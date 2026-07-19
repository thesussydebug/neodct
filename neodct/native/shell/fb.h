#ifndef NFB_H
#define NFB_H

#include <stdint.h>

struct nfb_info {
    int xres;
    int yres;
    int bpp;
    int line_length;
};

int nfb_present(const struct nfb_info *fb, const uint8_t *canvas_rgb,
                int cw, int ch, uint8_t *mem);

#endif
