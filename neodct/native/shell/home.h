#ifndef NHOME_H
#define NHOME_H

#include <stdint.h>

#include "layout.h"

struct nhome_fonts {
    const uint8_t *small;
    const uint8_t *normal;
    const uint8_t *xl;
};

int nhome_render(const struct nlay_layout *layout,
                 const struct nhome_fonts *fonts,
                 uint8_t *canvas_rgb, int w, int h);

typedef int (*nhome_icon_loader)(void *ctx, const char *path,
                                 int *w, int *h, uint8_t **rgba);

int nhome_render_full(const struct nlay_layout *layout,
                      const struct nhome_fonts *fonts,
                      uint8_t *canvas_rgb, int w, int h,
                      const char *clock,
                      nhome_icon_loader loader, void *loader_ctx);

int nhome_render_clock(const struct nlay_layout *layout,
                       const struct nhome_fonts *fonts,
                       uint8_t *canvas_rgb, int w, int h,
                       const char *clock);

#endif
