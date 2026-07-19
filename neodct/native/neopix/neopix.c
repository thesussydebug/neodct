#include "neopix.h"

#include <math.h>
#include <stdlib.h>

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

/* Pillow's LANCZOS: windowed sinc, support 3, weights normalised per output
   pixel, two passes (horizontal then vertical), rounding via +0.5 clamp. */
static double lanczos(double x) {
    if (x < 0.0) x = -x;
    if (x == 0.0) return 1.0;
    if (x >= 3.0) return 0.0;
    double px = M_PI * x;
    return (sin(px) / px) * (sin(px / 3.0) / (px / 3.0));
}

#define PREC_BITS 22
#define ROUND_OFF (1 << (PREC_BITS - 1))

static uint8_t clip8(int32_t v) {
    if (v < 0) return 0;
    if (v > 255) return 255;
    return (uint8_t)v;
}

__attribute__((unused))
static uint8_t clamp8(double v) {
    int i = (int)(v < 0.0 ? v - 0.5 : v + 0.5);
    if (i < 0) return 0;
    if (i > 255) return 255;
    return (uint8_t)i;
}

static int resample_axis(const uint8_t *src, int sw, int sh,
                         uint8_t *dst, int dw, int dh, int horizontal) {
    int out_size = horizontal ? dw : dh;
    int in_size = horizontal ? sw : sh;
    double scale = (double)out_size / (double)in_size;
    double filterscale = scale < 1.0 ? 1.0 / scale : 1.0;
    double support = 3.0 * filterscale;

    int kmax = (int)ceil(support) * 2 + 1;
    double *weights = malloc(sizeof(double) * kmax);
    if (!weights) return -1;

    for (int o = 0; o < out_size; o++) {
        double center = (o + 0.5) / scale;
        int lo = (int)(center - support + 0.5);
        int hi = (int)(center + support + 0.5);
        if (lo < 0) lo = 0;
        if (hi > in_size) hi = in_size;

        double total = 0.0;
        for (int i = lo; i < hi; i++) {
            double wgt = lanczos((i + 0.5 - center) / filterscale);
            weights[i - lo] = wgt;
            total += wgt;
        }
        if (total == 0.0) total = 1.0;

        /* Pillow convolves 8-bit images in fixed point after normalising. */
        for (int k = 0; k < hi - lo; k++) {
            double nw = weights[k] / total;
            weights[k] = nw < 0 ? (double)(int32_t)(-0.5 + nw * (1 << PREC_BITS))
                                : (double)(int32_t)(0.5 + nw * (1 << PREC_BITS));
        }

        int lines = horizontal ? sh : dw;
        for (int line = 0; line < lines; line++) {
            int32_t acc[4] = {ROUND_OFF, ROUND_OFF, ROUND_OFF, ROUND_OFF};
            for (int i = lo; i < hi; i++) {
                const uint8_t *px = horizontal
                    ? src + ((long)line * sw + i) * 4
                    : src + ((long)i * dw + line) * 4;
                int32_t wgt = (int32_t)weights[i - lo];
                acc[0] += px[0] * wgt;
                acc[1] += px[1] * wgt;
                acc[2] += px[2] * wgt;
                acc[3] += px[3] * wgt;
            }
            uint8_t *out = horizontal
                ? dst + ((long)line * dw + o) * 4
                : dst + ((long)o * dw + line) * 4;
            for (int c = 0; c < 4; c++) out[c] = clip8(acc[c] >> PREC_BITS);
        }
    }
    free(weights);
    return 0;
}

/* Pillow resamples RGBA with premultiplied alpha, so transparent pixels
   contribute no colour; results are un-premultiplied afterwards. */
int npx_resize_rgba(const uint8_t *src, int sw, int sh,
                    uint8_t *dst, int dw, int dh) {
    if (sw <= 0 || sh <= 0 || dw <= 0 || dh <= 0) return -1;

    long npix = (long)sw * sh;
    uint8_t *pre = malloc((size_t)npix * 4);
    uint8_t *tmp = malloc((size_t)dw * sh * 4);
    if (!pre || !tmp) { free(pre); free(tmp); return -1; }

    for (long i = 0; i < npix; i++) {
        int a = src[i * 4 + 3];
        if (a == 255) {
            for (int c = 0; c < 3; c++) pre[i * 4 + c] = src[i * 4 + c];
        } else {
            for (int c = 0; c < 3; c++) {
                unsigned t = (unsigned)src[i * 4 + c] * (unsigned)a + 128;
                pre[i * 4 + c] = (uint8_t)((t + (t >> 8)) >> 8);
            }
        }
        pre[i * 4 + 3] = (uint8_t)a;
    }

    if (resample_axis(pre, sw, sh, tmp, dw, sh, 1) != 0) { free(pre); free(tmp); return -1; }
    if (resample_axis(tmp, dw, sh, dst, dw, dh, 0) != 0) { free(pre); free(tmp); return -1; }
    free(pre);
    free(tmp);

    for (long i = 0; i < (long)dw * dh; i++) {
        int a = dst[i * 4 + 3];
        if (a == 255 || a == 0) continue;
        for (int c = 0; c < 3; c++) {
            int v = (255 * dst[i * 4 + c]) / a;
            dst[i * 4 + c] = (uint8_t)(v > 255 ? 255 : v);
        }
    }
    return 0;
}
