#include "fb.h"

#include <stdlib.h>
#include <string.h>

#include "neopix.h"

int nfb_present(const struct nfb_info *fb, const uint8_t *canvas_rgb,
                int cw, int ch, uint8_t *mem) {
    if (cw > fb->xres || ch > fb->yres) return -1;
    if (fb->bpp != 32 && fb->bpp != 16) return -2;

    int bytes_per_pixel = fb->bpp / 8;
    int row_bytes = cw * bytes_per_pixel;
    int dst_x = (fb->xres - cw) / 2;
    int dst_y = (fb->yres - ch) / 2;
    long npix = (long)cw * ch;

    uint8_t *band = malloc((size_t)npix * bytes_per_pixel);
    if (!band) return -3;
    if (fb->bpp == 32) npx_rgb_to_bgra(canvas_rgb, band, (int)npix);
    else npx_rgb_to_565le(canvas_rgb, band, (int)npix);

    if (dst_x == 0 && row_bytes == fb->line_length) {
        memcpy(mem + (long)dst_y * fb->line_length, band,
               (size_t)ch * row_bytes);
    } else {
        for (int y = 0; y < ch; y++) {
            memcpy(mem + (long)(dst_y + y) * fb->line_length
                       + (long)dst_x * bytes_per_pixel,
                   band + (long)y * row_bytes, (size_t)row_bytes);
        }
    }
    free(band);
    return 0;
}
