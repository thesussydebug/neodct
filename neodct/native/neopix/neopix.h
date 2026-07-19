#ifndef NEOPIX_H
#define NEOPIX_H

#include <stdint.h>

void npx_fill_rect(uint8_t *rgb, int w, int h,
                   int x0, int y0, int x1, int y1,
                   uint8_t r, uint8_t g, uint8_t b);

void npx_rgb_to_bgra(const uint8_t *rgb, uint8_t *bgra, int npix);

void npx_rgb_to_565le(const uint8_t *rgb, uint8_t *out, int npix);

int npx_resize_rgba(const uint8_t *src, int sw, int sh,
                    uint8_t *dst, int dw, int dh);

void npx_blit_rgba(uint8_t *dst_rgb, int dw, int dh,
                   const uint8_t *src_rgba, int sw, int sh,
                   int x, int y);

#endif
