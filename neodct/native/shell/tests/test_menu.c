#include "../menu.h"
#include "../../neopix/tests/runner.h"
#include "neopng.h"
#include "neopix.h"
#include <stdlib.h>

static int loader(void *ctx, const char *path, int cap, int *w, int *h,
                  unsigned char **rgba) {
    (void)ctx; (void)path;
    long n;
    unsigned char *png = load_fix("menu_icon.png", &n);
    int sw, sh;
    unsigned char *full = NULL;
    if (npng_decode(png, n, &sw, &sh, &full) != 0) { free(png); return -1; }
    free(png);
    if (sw <= cap && sh <= cap) { *w = sw; *h = sh; *rgba = full; return 0; }
    int dw = cap, dh = cap;
    if (sw > sh) dh = (int)((double)sh * cap / sw);
    else if (sh > sw) dw = (int)((double)sw * cap / sh);
    unsigned char *small = malloc((size_t)dw * dh * 4);
    if (npx_resize_rgba(full, sw, sh, small, dw, dh) != 0) {
        free(full); free(small); return -1;
    }
    free(full);
    *w = dw; *h = dh; *rgba = small;
    return 0;
}

static void test_menu_matches_appselector(void) {
    long mn;
    unsigned char *meta = load_fix("menu_meta.txt", &mn);
    char buf[256];
    long n = mn < 255 ? mn : 255;
    memcpy(buf, meta, n); buf[n] = 0;
    char name[64];
    int total = 0, sel = 0, iw = 0, ih = 0;
    sscanf(buf, "%63[^\n]\n%d\n%d\n%d %d", name, &total, &sel, &iw, &ih);

    unsigned char *a20 = load_fix("font_atlas_20.bin", NULL);
    unsigned char *a24 = load_fix("font_atlas_24.bin", NULL);
    struct nmenu_fonts fonts = { a20, a24 };
    unsigned char *canvas = calloc(1, 240 * 175 * 3);

    int rc = nmenu_render(&fonts, canvas, 240, 175, name, "unused",
                          sel, total, loader, NULL);
    unsigned char *want = load_fix("menu_expected.bin", NULL);
    if (rc != 0) { printf("  FAIL  nmenu_render rc=%d\n", rc); t_fail++; }
    else bytes_equal("menu screen matches Python AppSelector.draw",
                     canvas, want, 240 * 175 * 3);
    free(meta); free(a20); free(a24); free(canvas); free(want);
}

int main(void) {
    test_menu_matches_appselector();
    return SUMMARY();
}
