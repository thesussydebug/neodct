#ifndef NMENU_H
#define NMENU_H

#include <stdint.h>

struct nmenu_fonts {
    const uint8_t *normal;
    const uint8_t *xl;
};

typedef int (*nmenu_icon_loader)(void *ctx, const char *path, int cap,
                                 int *w, int *h, uint8_t **rgba);

int nmenu_render(const struct nmenu_fonts *fonts,
                 uint8_t *canvas_rgb, int w, int h,
                 const char *name, const char *icon_path,
                 int selected, int total,
                 nmenu_icon_loader loader, void *loader_ctx);

#endif
