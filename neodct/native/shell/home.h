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

int nhome_render_clock(const struct nlay_layout *layout,
                       const struct nhome_fonts *fonts,
                       uint8_t *canvas_rgb, int w, int h,
                       const char *clock);

#endif
