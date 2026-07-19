#include "neopix.h"

static int clampi(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void npx_rgb_to_bgra(const uint8_t *rgb, uint8_t *bgra, int npix) {
    for (int i = 0; i < npix; i++) {
        bgra[0] = rgb[2];
        bgra[1] = rgb[1];
        bgra[2] = rgb[0];
        bgra[3] = 255;
        rgb += 3;
        bgra += 4;
    }
}

void npx_rgb_to_565le(const uint8_t *rgb, uint8_t *out, int npix) {
    for (int i = 0; i < npix; i++) {
        uint16_t v = (uint16_t)(((rgb[0] & 0xF8) << 8) |
                                ((rgb[1] & 0xFC) << 3) |
                                (rgb[2] >> 3));
        out[0] = (uint8_t)(v & 0xFF);
        out[1] = (uint8_t)(v >> 8);
        rgb += 3;
        out += 2;
    }
}

static inline uint8_t blend255(int d, int s, int a) {
    return (uint8_t)((d * (255 - a) + s * a + 127) / 255);
}

void npx_blit_rgba(uint8_t *dst_rgb, int dw, int dh,
                   const uint8_t *src_rgba, int sw, int sh,
                   int x, int y) {
    int sx0 = x < 0 ? -x : 0;
    int sy0 = y < 0 ? -y : 0;
    int x0 = x < 0 ? 0 : x;
    int y0 = y < 0 ? 0 : y;
    int cw = sw - sx0;
    int ch = sh - sy0;
    if (x0 + cw > dw) cw = dw - x0;
    if (y0 + ch > dh) ch = dh - y0;
    if (cw <= 0 || ch <= 0) return;

    for (int row = 0; row < ch; row++) {
        const uint8_t *s = src_rgba + (((long)(sy0 + row) * sw) + sx0) * 4;
        uint8_t *d = dst_rgb + (((long)(y0 + row) * dw) + x0) * 3;
        for (int col = 0; col < cw; col++) {
            int a = s[3];
            if (a == 255) {
                d[0] = s[0]; d[1] = s[1]; d[2] = s[2];
            } else if (a != 0) {
                d[0] = blend255(d[0], s[0], a);
                d[1] = blend255(d[1], s[1], a);
                d[2] = blend255(d[2], s[2], a);
            }
            s += 4;
            d += 3;
        }
    }
}

void npx_fill_rect(uint8_t *rgb, int w, int h,
                   int x0, int y0, int x1, int y1,
                   uint8_t r, uint8_t g, uint8_t b) {
    x0 = clampi(x0, 0, w);
    x1 = clampi(x1, 0, w);
    y0 = clampi(y0, 0, h);
    y1 = clampi(y1, 0, h);
    for (int y = y0; y < y1; y++) {
        uint8_t *p = rgb + ((long)y * w + x0) * 3;
        for (int x = x0; x < x1; x++) {
            *p++ = r;
            *p++ = g;
            *p++ = b;
        }
    }
}
