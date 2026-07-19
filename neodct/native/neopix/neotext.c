#include "neotext.h"

#include <math.h>
#include <string.h>

struct glyph {
    int32_t code, gw, gh, bx, by;
    double adv;
    const uint8_t *bitmap;
};

static int atlas_parse(const uint8_t *atlas, struct glyph *out, int max_glyphs) {
    uint32_t count, size;
    memcpy(&count, atlas, 4);
    memcpy(&size, atlas + 4, 4);
    (void)size;
    const uint8_t *p = atlas + 8;
    if ((int)count > max_glyphs) return -1;
    for (uint32_t i = 0; i < count; i++) {
        struct glyph *g = &out[i];
        memcpy(&g->code, p, 4);
        memcpy(&g->gw, p + 4, 4);
        memcpy(&g->gh, p + 8, 4);
        memcpy(&g->bx, p + 12, 4);
        memcpy(&g->by, p + 16, 4);
        memcpy(&g->adv, p + 20, 8);
        p += 28;
        g->bitmap = p;
        int sw = g->gw > 0 ? g->gw : 1;
        int sh = g->gh > 0 ? g->gh : 1;
        p += (long)sw * sh;
    }
    return (int)count;
}

int ntx_render(const uint8_t *atlas, const char *text,
               uint8_t *out_gray, int w, int h) {
    struct glyph glyphs[128];
    int count = atlas_parse(atlas, glyphs, 128);
    if (count <= 0) return -1;

    double cursor = 0.0;
    for (const char *c = text; *c; c++) {
        const struct glyph *g = NULL;
        for (int i = 0; i < count; i++)
            if (glyphs[i].code == (int32_t)(unsigned char)*c) { g = &glyphs[i]; break; }
        if (!g) return -2;

        int ox = (int)lround(cursor) + g->bx;
        for (int y = 0; y < g->gh; y++) {
            int dy = g->by + y;
            if (dy < 0 || dy >= h) continue;
            for (int x = 0; x < g->gw; x++) {
                int dx = ox + x;
                if (dx < 0 || dx >= w) continue;
                uint8_t cov = g->bitmap[(long)y * g->gw + x];
                uint8_t *dst = &out_gray[(long)dy * w + dx];
                int v = cov + ((255 - cov) * *dst + 127) / 255;
                *dst = (uint8_t)(v > 255 ? 255 : v);
            }
        }
        cursor += g->adv;
    }
    return 0;
}

int ntx_bbox(const uint8_t *atlas, const char *text,
             int *x0, int *y0, int *x1, int *y1) {
    struct glyph glyphs[128];
    int count = atlas_parse(atlas, glyphs, 128);
    if (count <= 0) return -1;

    int have = 0, ax0 = 0, ay0 = 0, ax1 = 0, ay1 = 0;
    double cursor = 0.0;
    for (const char *c = text; *c; c++) {
        const struct glyph *g = NULL;
        for (int i = 0; i < count; i++)
            if (glyphs[i].code == (int32_t)(unsigned char)*c) { g = &glyphs[i]; break; }
        if (!g) return -2;
        if (g->gw > 0 && g->gh > 0) {
            int gx0 = (int)lround(cursor) + g->bx;
            int gy0 = g->by;
            int gx1 = gx0 + g->gw;
            int gy1 = gy0 + g->gh;
            if (!have) { ax0 = gx0; ay0 = gy0; ax1 = gx1; ay1 = gy1; have = 1; }
            else {
                if (gx0 < ax0) ax0 = gx0;
                if (gy0 < ay0) ay0 = gy0;
                if (gx1 > ax1) ax1 = gx1;
                if (gy1 > ay1) ay1 = gy1;
            }
        }
        cursor += g->adv;
    }
    if (x0) *x0 = ax0;
    if (y0) *y0 = ay0;
    if (x1) *x1 = ax1;
    if (y1) *y1 = ay1;
    return 0;
}

int ntx_draw(const uint8_t *atlas, const char *text,
             uint8_t *canvas_rgb, int w, int h, int x, int y,
             uint8_t cr, uint8_t cg, uint8_t cb) {
    struct glyph glyphs[128];
    int count = atlas_parse(atlas, glyphs, 128);
    if (count <= 0) return -1;

    double cursor = 0.0;
    for (const char *c = text; *c; c++) {
        const struct glyph *g = NULL;
        for (int i = 0; i < count; i++)
            if (glyphs[i].code == (int32_t)(unsigned char)*c) { g = &glyphs[i]; break; }
        if (!g) return -2;
        int ox = x + (int)lround(cursor) + g->bx;
        for (int gy = 0; gy < g->gh; gy++) {
            int dy = y + g->by + gy;
            if (dy < 0 || dy >= h) continue;
            for (int gx = 0; gx < g->gw; gx++) {
                int dx = ox + gx;
                if (dx < 0 || dx >= w) continue;
                uint8_t a = g->bitmap[(long)gy * g->gw + gx];
                if (!a) continue;
                uint8_t *p = canvas_rgb + ((long)dy * w + dx) * 3;
                p[0] = (uint8_t)((p[0] * (255 - a) + cr * a + 127) / 255);
                p[1] = (uint8_t)((p[1] * (255 - a) + cg * a + 127) / 255);
                p[2] = (uint8_t)((p[2] * (255 - a) + cb * a + 127) / 255);
            }
        }
        cursor += g->adv;
    }
    return 0;
}
