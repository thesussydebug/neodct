#include "home.h"

#include <stdlib.h>
#include <string.h>

#include "neopix.h"
#include "neotext.h"

static void parse_color(const char *name, uint8_t *r, uint8_t *g, uint8_t *b) {
    if (name[0] == '#') {
        long v = strtol(name + 1, NULL, 16);
        *r = (uint8_t)((v >> 16) & 0xFF);
        *g = (uint8_t)((v >> 8) & 0xFF);
        *b = (uint8_t)(v & 0xFF);
        return;
    }
    if (strcmp(name, "black") == 0) { *r = *g = *b = 0; return; }
    if (strcmp(name, "gray") == 0) { *r = *g = *b = 128; return; }
    *r = *g = *b = 255;
}

static const uint8_t *pick_font(const struct nhome_fonts *f, int size) {
    if (size >= 20) return f->xl;
    if (size >= 16) return f->normal;
    return f->small;
}

int nhome_render_clock(const struct nlay_layout *layout,
                       const struct nhome_fonts *fonts,
                       uint8_t *canvas_rgb, int w, int h,
                       const char *clock) {
    if (!layout || !fonts || !canvas_rgb) return -1;
    npx_fill_rect(canvas_rgb, w, h, 0, 0, w, h, 0, 0, 0);

    for (int i = 0; i < layout->count; i++) {
        const struct nlay_element *e = &layout->elements[i];
        int x = (int)((e->x / 240.0) * w);
        int y = (int)((e->y / 240.0) * h);

        if (e->type == NLAY_TEXT) {
            const char *txt = e->text;
            if (clock && strcmp(txt, "12:00") == 0) txt = clock;
            const uint8_t *atlas = pick_font(fonts, e->font_size);
            int x0, y0, x1, y1;
            if (ntx_bbox(atlas, txt, &x0, &y0, &x1, &y1) != 0) continue;
            int tw = x1 - x0;
            if (strstr(e->anchor, "center_h")) x -= tw / 2;
            else if (strstr(e->anchor, "right")) x -= tw;
            uint8_t r, g, b;
            parse_color(e->color, &r, &g, &b);
            ntx_draw(atlas, txt, canvas_rgb, w, h, x, y, r, g, b);
        }
        else if (e->type == NLAY_ICON_SET) {
            int count = e->count > 0 ? e->count : 5;
            int step = (int)(w * 0.021);
            if (step < 3) step = 3;
            for (int k = 0; k < count; k++) {
                int bh = (k + 1) * 3;
                uint8_t v = k <= e->sim_val ? 255 : 0x33;
                int bx = x + k * step;
                npx_fill_rect(canvas_rgb, w, h, bx, y + 15 - bh, bx + 4, y + 16,
                              v, v, v);
            }
        }
    }
    return 0;
}

int nhome_render(const struct nlay_layout *layout,
                 const struct nhome_fonts *fonts,
                 uint8_t *canvas_rgb, int w, int h) {
    return nhome_render_clock(layout, fonts, canvas_rgb, w, h, NULL);
}
