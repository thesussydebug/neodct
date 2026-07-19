#include "../home.h"
#include "neopng.h"
#include "neopix.h"
#include "../layout.h"
#include "../../neopix/tests/runner.h"

#include <stdlib.h>

static char *slurp(const char *name) {
    long n;
    unsigned char *raw = load_fix(name, &n);
    char *s = malloc(n + 1);
    memcpy(s, raw, n);
    s[n] = 0;
    free(raw);
    return s;
}

static void test_home_matches_python_render(void) {
    char *json = slurp("home_layout.json");
    struct nlay_layout l;
    if (nlay_parse(json, &l) != 0) { printf("  FAIL  layout parse\n"); t_fail++; free(json); return; }

    unsigned char *atlas14 = load_fix("font_atlas_14.bin", NULL);
    unsigned char *atlas20 = load_fix("font_atlas_20.bin", NULL);
    unsigned char *atlas24 = load_fix("font_atlas_24.bin", NULL);
    struct nhome_fonts fonts = { atlas14, atlas20, atlas24 };

    unsigned char *canvas = calloc(1, 240 * 175 * 3);
    int rc = nhome_render(&l, &fonts, canvas, 240, 175);

    unsigned char *want = load_fix("home_expected.bin", NULL);
    if (rc != 0) { printf("  FAIL  nhome_render rc=%d\n", rc); t_fail++; }
    else bytes_equal("home screen matches Python render_element",
                     canvas, want, 240 * 175 * 3);

    free(json); free(atlas14); free(atlas20); free(atlas24);
    free(canvas); free(want);
}

static void test_render_clears_canvas_first(void) {
    struct nlay_layout l;
    nlay_parse("{\"elements\": []}", &l);
    unsigned char *atlas14 = load_fix("font_atlas_14.bin", NULL);
    struct nhome_fonts fonts = { atlas14, atlas14, atlas14 };
    unsigned char *canvas = malloc(240 * 175 * 3);
    memset(canvas, 0x7F, 240 * 175 * 3);
    nhome_render(&l, &fonts, canvas, 240, 175);
    int black = 1;
    for (long i = 0; i < 240L * 175 * 3; i++) if (canvas[i] != 0) black = 0;
    CHECK("empty layout clears canvas to black", black);
    free(atlas14); free(canvas);
}

static void test_clock_placeholder_is_substituted(void) {
    char *json = slurp("home_layout.json");
    struct nlay_layout l;
    nlay_parse(json, &l);
    unsigned char *a14 = load_fix("font_atlas_14.bin", NULL);
    unsigned char *a20 = load_fix("font_atlas_20.bin", NULL);
    unsigned char *a24 = load_fix("font_atlas_24.bin", NULL);
    struct nhome_fonts fonts = { a14, a20, a24 };
    unsigned char *canvas = calloc(1, 240 * 175 * 3);
    nhome_render_clock(&l, &fonts, canvas, 240, 175, "07:30");
    unsigned char *want = load_fix("home_clock_expected.bin", NULL);
    bytes_equal("clock placeholder 12:00 replaced with live time",
                canvas, want, 240 * 175 * 3);
    free(json); free(a14); free(a20); free(a24); free(canvas); free(want);
}

/* Loader mirroring _get_status_icon: decode PNG, scale by H/240, return RGBA. */
static int fixture_loader(void *ctx, const char *path, int *w, int *h,
                          unsigned char **rgba) {
    (void)ctx;
    const char *base = strrchr(path, '/');
    base = base ? base + 1 : path;
    char name[128];
    snprintf(name, sizeof name, "icon_%s", base);
    long n;
    unsigned char *png = load_fix(name, &n);
    int sw, sh;
    unsigned char *full = NULL;
    if (npng_decode(png, n, &sw, &sh, &full) != 0) { free(png); return -1; }
    free(png);

    double scale = 175.0 / 240.0;
    int dw = (int)(sw * scale); if (dw < 1) dw = 1;
    int dh = (int)(sh * scale); if (dh < 1) dh = 1;
    if (dw == sw && dh == sh) { *w = sw; *h = sh; *rgba = full; return 0; }
    unsigned char *small = malloc((size_t)dw * dh * 4);
    if (npx_resize_rgba(full, sw, sh, small, dw, dh) != 0) {
        free(full); free(small); return -1;
    }
    free(full);
    *w = dw; *h = dh; *rgba = small;
    return 0;
}

static void test_home_with_png_icons_matches_python(void) {
    char *json = slurp("home_icons_layout.json");
    struct nlay_layout l;
    if (nlay_parse(json, &l) != 0) { printf("  FAIL  layout parse\n"); t_fail++; free(json); return; }
    unsigned char *a14 = load_fix("font_atlas_14.bin", NULL);
    unsigned char *a20 = load_fix("font_atlas_20.bin", NULL);
    unsigned char *a24 = load_fix("font_atlas_24.bin", NULL);
    struct nhome_fonts fonts = { a14, a20, a24 };
    unsigned char *canvas = calloc(1, 240 * 175 * 3);

    nhome_render_full(&l, &fonts, canvas, 240, 175, NULL, fixture_loader, NULL);

    unsigned char *want = load_fix("home_icons_expected.bin", NULL);
    bytes_equal("home screen with PNG status icons matches Python",
                canvas, want, 240 * 175 * 3);
    free(json); free(a14); free(a20); free(a24); free(canvas); free(want);
}

int main(void) {
    test_home_matches_python_render();
    test_render_clears_canvas_first();
    test_clock_placeholder_is_substituted();
    test_home_with_png_icons_matches_python();
    return SUMMARY();
}
