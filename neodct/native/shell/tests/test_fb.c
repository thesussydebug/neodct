#include "../fb.h"
#include "../../neopix/tests/runner.h"

#include <stdlib.h>

static void test_present_matches_python_band_write(void) {
    struct nfb_info fb = {240, 240, 32, 240 * 4};
    long cn;
    unsigned char *canvas = load_fix("fb_canvas_rgb.bin", &cn);
    unsigned char *want = load_fix("fb_expected.bin", NULL);
    long memlen = (long)fb.xres * fb.yres * 4;
    unsigned char *mem = malloc(memlen);
    memset(mem, 0xAA, memlen);

    int rc = nfb_present(&fb, canvas, 240, 175, mem);
    if (rc != 0) { printf("  FAIL  present rc=%d\n", rc); t_fail++; }
    else bytes_equal("present matches main.py centered band write",
                     mem, want, (int)memlen);
    free(canvas); free(want); free(mem);
}

static void test_present_leaves_letterbox_untouched(void) {
    struct nfb_info fb = {240, 240, 32, 240 * 4};
    long cn;
    unsigned char *canvas = load_fix("fb_canvas_rgb.bin", &cn);
    long memlen = (long)fb.xres * fb.yres * 4;
    unsigned char *mem = malloc(memlen);
    memset(mem, 0xAA, memlen);
    nfb_present(&fb, canvas, 240, 175, mem);

    int clean = 1;
    for (long i = 0; i < 32L * fb.line_length; i++) if (mem[i] != 0xAA) clean = 0;
    for (long i = (32L + 175) * fb.line_length; i < memlen; i++)
        if (mem[i] != 0xAA) clean = 0;
    CHECK("letterbox rows above/below are not written", clean);
    free(canvas); free(mem);
}

static void test_rejects_canvas_larger_than_fb(void) {
    struct nfb_info fb = {240, 240, 32, 240 * 4};
    unsigned char mem[16];
    unsigned char canvas[16];
    CHECK("oversized canvas is rejected",
          nfb_present(&fb, canvas, 320, 240, mem) != 0);
}

static void test_rejects_unsupported_depth(void) {
    struct nfb_info fb = {240, 240, 24, 240 * 3};
    unsigned char mem[16];
    unsigned char canvas[16];
    CHECK("unsupported bpp is rejected",
          nfb_present(&fb, canvas, 240, 175, mem) != 0);
}

int main(void) {
    test_present_matches_python_band_write();
    test_present_leaves_letterbox_untouched();
    test_rejects_canvas_larger_than_fb();
    test_rejects_unsupported_depth();
    return SUMMARY();
}
