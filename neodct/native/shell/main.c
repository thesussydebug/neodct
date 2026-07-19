#include <dirent.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/select.h>
#include <time.h>
#include <unistd.h>

#include "fb.h"
#include "home.h"
#include "input.h"
#include "layout.h"
#include "menu.h"
#include "neopix.h"
#include "neopng.h"
#include "neotext.h"
#include "ui.h"

#define UI_W 240
#define UI_H 175
#define SOFTKEY_H 30
#define RES "/NeoDCT/System/ui/resources"
#define MAX_APPS 48

struct app_entry {
    int id;
    char name[40];
    char icon[256];
};

static uint8_t *slurp(const char *path, long *len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc(n + 1);
    if (fread(buf, 1, n, f) != (size_t)n) { fclose(f); free(buf); return NULL; }
    fclose(f);
    buf[n] = 0;
    if (len) *len = n;
    return buf;
}

static int json_str(const char *src, const char *key, char *out, size_t cap) {
    char pat[32];
    snprintf(pat, sizeof pat, "\"%s\"", key);
    const char *p = strstr(src, pat);
    if (!p) return -1;
    p = strchr(p + strlen(pat), ':');
    if (!p) return -1;
    p++;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
    if (*p != '"') return -1;
    p++;
    size_t n = 0;
    while (*p && *p != '"' && n + 1 < cap) out[n++] = *p++;
    out[n] = 0;
    return 0;
}

static int cmp_app(const void *a, const void *b) {
    return ((const struct app_entry *)a)->id - ((const struct app_entry *)b)->id;
}

static int scan_dir(const char *base, struct app_entry *apps, int n, int max) {
    DIR *d = opendir(base);
    if (!d) return n;
    struct dirent *e;
    while ((e = readdir(d)) && n < max) {
        if (e->d_name[0] == '.') continue;
        char path[512];
        snprintf(path, sizeof path, "%s/%s/manifest.json", base, e->d_name);
        uint8_t *raw = slurp(path, NULL);
        if (!raw) continue;
        char idbuf[16];
        if (json_str((char *)raw, "name", apps[n].name, sizeof apps[n].name) == 0 &&
            json_str((char *)raw, "id", idbuf, sizeof idbuf) == 0) {
            apps[n].id = atoi(idbuf);
            snprintf(apps[n].icon, sizeof apps[n].icon, "%s/%s/icon.png",
                     base, e->d_name);
            n++;
        }
        free(raw);
    }
    closedir(d);
    return n;
}

#define ICON_CACHE_MAX 40

struct icon_cache_entry {
    char path[224];
    int w, h;
    uint8_t *rgba;
};

struct icon_cache {
    struct icon_cache_entry e[ICON_CACHE_MAX];
    int n;
    double scale;
};

/* Mirrors _get_status_icon: decode once, scale by H/240, cache at display size. */
static int icon_load_sized(struct icon_cache *c, const char *path,
                           int cap, int *w, int *h, uint8_t **rgba) {
    char key[224];
    snprintf(key, sizeof key, "%d|%s", cap, path);
    for (int i = 0; i < c->n; i++) {
        if (strcmp(c->e[i].path, key) == 0) {
            *w = c->e[i].w;
            *h = c->e[i].h;
            size_t sz = (size_t)*w * *h * 4;
            *rgba = malloc(sz);
            if (!*rgba) return -1;
            memcpy(*rgba, c->e[i].rgba, sz);
            return 0;
        }
    }

    long n;
    uint8_t *png = slurp(path, &n);
    if (!png) return -1;
    int sw, sh;
    uint8_t *full = NULL;
    if (npng_decode(png, n, &sw, &sh, &full) != 0) { free(png); return -1; }
    free(png);

    int dw, dh;
    if (cap > 0) {
        dw = sw; dh = sh;
        if (sw > cap || sh > cap) {
            if (sw >= sh) { dw = cap; dh = (int)((double)sh * cap / sw); }
            else { dh = cap; dw = (int)((double)sw * cap / sh); }
            if (dw < 1) dw = 1;
            if (dh < 1) dh = 1;
        }
    } else {
        dw = (int)(sw * c->scale); if (dw < 1) dw = 1;
        dh = (int)(sh * c->scale); if (dh < 1) dh = 1;
    }
    uint8_t *out = full;
    if (dw != sw || dh != sh) {
        out = malloc((size_t)dw * dh * 4);
        if (!out || npx_resize_rgba(full, sw, sh, out, dw, dh) != 0) {
            free(full); free(out); return -1;
        }
        free(full);
    }

    if (c->n < ICON_CACHE_MAX) {
        struct icon_cache_entry *e = &c->e[c->n++];
        snprintf(e->path, sizeof e->path, "%s", key);
        e->w = dw; e->h = dh;
        e->rgba = malloc((size_t)dw * dh * 4);
        if (e->rgba) memcpy(e->rgba, out, (size_t)dw * dh * 4);
        else c->n--;
    }
    *w = dw; *h = dh; *rgba = out;
    return 0;
}

static int icon_load(void *ctx, const char *path, int *w, int *h, uint8_t **rgba) {
    return icon_load_sized(ctx, path, 0, w, h, rgba);
}

static int menu_icon_load(void *ctx, const char *path, int cap,
                          int *w, int *h, uint8_t **rgba) {
    return icon_load_sized(ctx, path, cap, w, h, rgba);
}

static void draw_softkey(const uint8_t *atlas, uint8_t *canvas,
                         const char *label) {
    npx_fill_rect(canvas, UI_W, UI_H, 0, UI_H - SOFTKEY_H, UI_W, UI_H, 0, 0, 0);
    int x0, y0, x1, y1;
    if (ntx_bbox(atlas, label, &x0, &y0, &x1, &y1) != 0) return;
    int tw = x1 - x0, th = y1 - y0;
    ntx_draw(atlas, label, canvas, UI_W, UI_H,
             (UI_W - tw) / 2, UI_H - SOFTKEY_H + (SOFTKEY_H - th) / 2 - y0,
             255, 255, 255);
}

int main(void) {
    int fbfd = open("/dev/fb0", O_RDWR);
    if (fbfd < 0) { perror("[SHELL] /dev/fb0"); return 1; }
    struct fb_var_screeninfo vinfo;
    struct fb_fix_screeninfo finfo;
    if (ioctl(fbfd, FBIOGET_VSCREENINFO, &vinfo) < 0 ||
        ioctl(fbfd, FBIOGET_FSCREENINFO, &finfo) < 0) {
        perror("[SHELL] fb ioctl");
        return 1;
    }
    struct nfb_info fb = { (int)vinfo.xres, (int)vinfo.yres,
                           (int)vinfo.bits_per_pixel, (int)finfo.line_length };
    size_t fbsize = (size_t)fb.line_length * fb.yres;
    uint8_t *fbmem = mmap(NULL, fbsize, PROT_READ | PROT_WRITE, MAP_SHARED, fbfd, 0);
    if (fbmem == MAP_FAILED) { perror("[SHELL] mmap"); return 1; }
    memset(fbmem, 0, fbsize);
    printf("[SHELL] fb %dx%d @%dbpp stride=%d\n",
           fb.xres, fb.yres, fb.bpp, fb.line_length);

    const char *kbd = getenv("NEODCT_KEYPAD_DEVICE");
    if (!kbd) kbd = "/dev/input/event0";
    int kfd = open(kbd, O_RDONLY | O_NONBLOCK);
    if (kfd < 0) fprintf(stderr, "[SHELL] no input device %s\n", kbd);
    else printf("[SHELL] input %s\n", kbd);

    long n;
    uint8_t *ljson = slurp(RES "/ui_home.json", &n);
    struct nlay_layout layout;
    memset(&layout, 0, sizeof layout);
    if (!ljson || nlay_parse((char *)ljson, &layout) != 0)
        fprintf(stderr, "[SHELL] layout parse failed; blank home\n");
    else
        printf("[SHELL] layout: %d elements\n", layout.count);

    uint8_t *a14 = slurp(RES "/fonts/atlas_14.bin", NULL);
    uint8_t *a20 = slurp(RES "/fonts/atlas_20.bin", NULL);
    uint8_t *a24 = slurp(RES "/fonts/atlas_24.bin", NULL);
    if (!a14 || !a20 || !a24) { fprintf(stderr, "[SHELL] font atlas missing\n"); return 1; }
    struct nhome_fonts fonts = { a14, a20, a24 };

    struct app_entry apps[MAX_APPS];
    int app_count = scan_dir("/NeoDCT/System/apps", apps, 0, MAX_APPS);
    app_count = scan_dir("/NeoDCT/System/engineering/apps", apps, app_count, MAX_APPS);
    qsort(apps, app_count, sizeof apps[0], cmp_app);
    printf("[SHELL] %d apps\n", app_count);

    struct icon_cache icons;
    memset(&icons, 0, sizeof icons);
    icons.scale = (double)UI_H / 240.0;

    struct nui_state ui;
    nui_init(&ui, app_count);
    uint8_t *canvas = malloc((size_t)UI_W * UI_H * 3);

    printf("[SHELL] Entering Main Loop...\n");
    fflush(stdout);

    int last_screen = -1, last_sel = -1;
    char last_clock[8] = "";
    for (;;) {
        if (kfd >= 0) {
            fd_set rd;
            FD_ZERO(&rd);
            FD_SET(kfd, &rd);
            struct timeval tv = { 0, 100000 };
            if (select(kfd + 1, &rd, NULL, NULL, &tv) > 0) {
                uint8_t buf[512];
                ssize_t got = read(kfd, buf, sizeof buf);
                if (got > 0) {
                    struct nin_key keys[32];
                    int k = nin_decode(buf, (size_t)got, keys, 32);
                    for (int i = 0; i < k; i++)
                        if (keys[i].value == 1) nui_key(&ui, keys[i].code);
                }
            }
        } else {
            usleep(100000);
        }

        int launch = nui_take_launch(&ui);
        if (launch >= 0 && launch < app_count)
            printf("[SHELL] Launching App ID: %d (%s)\n",
                   apps[launch].id, apps[launch].name);

        char clock[8];
        time_t now = time(NULL);
        struct tm tmv;
        localtime_r(&now, &tmv);
        snprintf(clock, sizeof clock, "%02d:%02d", tmv.tm_hour, tmv.tm_min);

        if (ui.screen == last_screen && ui.selected == last_sel &&
            strcmp(clock, last_clock) == 0)
            continue;
        last_screen = ui.screen;
        last_sel = ui.selected;
        snprintf(last_clock, sizeof last_clock, "%s", clock);

        if (ui.screen == NUI_HOME) {
            nhome_render_full(&layout, &fonts, canvas, UI_W, UI_H, clock,
                              icon_load, &icons);
            draw_softkey(a20, canvas, "Menu");
        } else {
            struct nmenu_fonts mf = { a20, a24 };
            const char *name = app_count > 0 ? apps[ui.selected].name : "No Apps";
            const char *ipath = app_count > 0 ? apps[ui.selected].icon : "";
            nmenu_render(&mf, canvas, UI_W, UI_H, name, ipath,
                         ui.selected, app_count, menu_icon_load, &icons);
        }
        nfb_present(&fb, canvas, UI_W, UI_H, fbmem);
    }
    return 0;
}
