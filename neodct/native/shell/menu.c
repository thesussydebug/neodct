#include "menu.h"

#include <stdio.h>
#include <stdlib.h>

#include "neopix.h"
#include "neotext.h"

#define SOFTKEY_H 30
#define ICON_MAX 175

static void centered(const uint8_t *atlas, uint8_t *canvas, int w, int h,
                     const char *text, int y) {
    int x0, y0, x1, y1;
    if (ntx_bbox(atlas, text, &x0, &y0, &x1, &y1) != 0) return;
    ntx_draw(atlas, text, canvas, w, h, (w - (x1 - x0)) / 2, y, 255, 255, 255);
}

int nmenu_render(const struct nmenu_fonts *fonts,
                 uint8_t *canvas_rgb, int w, int h,
                 const char *name, const char *icon_path,
                 int selected, int total,
                 nmenu_icon_loader loader, void *loader_ctx) {
    if (!fonts || !canvas_rgb) return -1;
    npx_fill_rect(canvas_rgb, w, h, 0, 0, w, h, 0, 0, 0);

    int content_bottom = h - SOFTKEY_H;
    int header_y = h * 11 / 100;
    if (header_y < 30) header_y = 30;

    centered(fonts->xl, canvas_rgb, w, h, name, header_y - 16);

    int icon_y = (content_bottom - header_y) * 22 / 100;
    if (icon_y < 24) icon_y = 24;
    icon_y += header_y;
    int cap = content_bottom - icon_y - 8;
    if (cap < 24) cap = 24;
    if (cap > ICON_MAX) cap = ICON_MAX;

    if (loader) {
        int iw, ih;
        uint8_t *rgba = NULL;
        if (loader(loader_ctx, icon_path, cap, &iw, &ih, &rgba) == 0 && rgba) {
            npx_blit_rgba(canvas_rgb, w, h, rgba, iw, ih, (w - iw) / 2, icon_y);
            free(rgba);
        }
    }

    int x0, y0, x1, y1;
    if (ntx_bbox(fonts->normal, "Select", &x0, &y0, &x1, &y1) == 0) {
        int th = y1 - y0;
        int fy = content_bottom + (SOFTKEY_H - th) / 2;
        if (fy < content_bottom) fy = content_bottom;
        centered(fonts->normal, canvas_rgb, w, h, "Select", fy);
    }

    int bar_x = w - 8;
    int track_top = header_y + 6;
    int track_bottom = content_bottom - 10;
    if (track_bottom < track_top) track_bottom = track_top;
    npx_fill_rect(canvas_rgb, w, h, bar_x, track_top, bar_x + 2, track_bottom + 1,
                  255, 255, 255);

    double notch_y = track_top;
    if (total > 1)
        notch_y = track_top + (double)selected * (track_bottom - track_top) / (total - 1);
    int ny = (int)notch_y;
    npx_fill_rect(canvas_rgb, w, h, bar_x - 4, ny - 3, bar_x + 3, ny + 4,
                  255, 255, 255);

    char page[16];
    snprintf(page, sizeof page, "%d", selected + 1);
    if (ntx_bbox(fonts->normal, page, &x0, &y0, &x1, &y1) == 0)
        ntx_draw(fonts->normal, page, canvas_rgb, w, h,
                 w - 5 - (x1 - x0), 10, 255, 255, 255);
    return 0;
}
