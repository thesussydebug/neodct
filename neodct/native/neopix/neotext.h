#ifndef NEOTEXT_H
#define NEOTEXT_H

#include <stdint.h>

int ntx_render(const uint8_t *atlas, const char *text,
               uint8_t *out_gray, int w, int h);

int ntx_bbox(const uint8_t *atlas, const char *text,
             int *x0, int *y0, int *x1, int *y1);

int ntx_draw(const uint8_t *atlas, const char *text,
             uint8_t *canvas_rgb, int w, int h, int x, int y,
             uint8_t cr, uint8_t cg, uint8_t cb);

#endif
