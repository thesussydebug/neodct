#include "neopix.h"
#include "neotext.h"
#include "runner.h"

static void test_fill_rect_writes_expected_bytes(void) {
    uint8_t buf[4 * 3 * 3];
    memset(buf, 9, sizeof buf);
    npx_fill_rect(buf, 4, 3, 1, 1, 3, 3, 255, 10, 20);

    uint8_t want[4 * 3 * 3];
    memset(want, 9, sizeof want);
    for (int y = 1; y < 3; y++)
        for (int x = 1; x < 3; x++) {
            want[(y * 4 + x) * 3 + 0] = 255;
            want[(y * 4 + x) * 3 + 1] = 10;
            want[(y * 4 + x) * 3 + 2] = 20;
        }
    bytes_equal("fill_rect interior 2x2", buf, want, sizeof buf);
}

static void test_fill_rect_clips_to_buffer(void) {
    uint8_t buf[3 * 2 * 3];
    memset(buf, 7, sizeof buf);
    npx_fill_rect(buf, 3, 2, -5, -5, 99, 99, 1, 2, 3);
    int all = 1;
    for (int i = 0; i < 3 * 2; i++)
        if (buf[i * 3] != 1 || buf[i * 3 + 1] != 2 || buf[i * 3 + 2] != 3)
            all = 0;
    CHECK("fill_rect clips oversized rect to full buffer", all);

    uint8_t buf2[3 * 2 * 3];
    memset(buf2, 7, sizeof buf2);
    npx_fill_rect(buf2, 3, 2, 2, 2, 1, 1, 5, 5, 5);
    int untouched = 1;
    for (unsigned i = 0; i < sizeof buf2; i++)
        if (buf2[i] != 7) untouched = 0;
    CHECK("fill_rect empty/inverted rect writes nothing", untouched);
}

static void test_rgb_to_bgra_matches_pillow(void) {
    long n;
    unsigned char *rgb = load_fix("conv_rgb.bin", &n);
    unsigned char *want = load_fix("conv_bgra_expected.bin", NULL);
    int npix = (int)(n / 3);
    unsigned char *got = malloc((size_t)npix * 4);
    npx_rgb_to_bgra(rgb, got, npix);
    bytes_equal("rgb_to_bgra matches Pillow BGRA", got, want, npix * 4);
    free(rgb); free(want); free(got);
}

static void test_rgb_to_565le_matches_shipping_pack(void) {
    long n;
    unsigned char *rgb = load_fix("conv_rgb.bin", &n);
    unsigned char *want = load_fix("conv_565_expected.bin", NULL);
    int npix = (int)(n / 3);
    unsigned char *got = malloc((size_t)npix * 2);
    npx_rgb_to_565le(rgb, got, npix);
    bytes_equal("rgb_to_565le matches _pack_rgb565", got, want, npix * 2);
    free(rgb); free(want); free(got);
}

static void blit_case(const char *fixture, int x, int y, const char *label) {
    long dn;
    unsigned char *dst = load_fix("blit_dst.bin", &dn);
    unsigned char *src = load_fix("blit_src.bin", NULL);
    unsigned char *want = load_fix(fixture, NULL);
    npx_blit_rgba(dst, 24, 10, src, 9, 5, x, y);
    bytes_equal(label, dst, want, (int)dn);
    free(dst); free(src); free(want);
}

static void test_blit_rgba_matches_pillow_paste(void) {
    blit_case("blit_in_expected.bin", 3, 2, "blit interior matches Pillow paste");
    blit_case("blit_neg_expected.bin", -4, -2, "blit negative offset clips like Pillow");
    blit_case("blit_over_expected.bin", 20, 7, "blit overhang clips like Pillow");
}

static void test_blit_full_canvas_random(void) {
    long dn;
    unsigned char *dst = load_fix("big_dst.bin", &dn);
    unsigned char *src = load_fix("big_src.bin", NULL);
    unsigned char *want = load_fix("big_expected.bin", NULL);
    npx_blit_rgba(dst, 240, 175, src, 64, 64, 88, 55);
    bytes_equal("64x64 random-alpha blit on 240x175 canvas", dst, want, (int)dn);
    free(dst); free(src); free(want);
}

static void text_case_sz(int size, int idx, const char *label) {
    char name[64];
    snprintf(name, sizeof name, "text_ref_%d_%d.txt", size, idx);
    long tn; unsigned char *txt = load_fix(name, &tn);
    char *string = malloc(tn + 1); memcpy(string, txt, tn); string[tn] = 0;
    snprintf(name, sizeof name, "text_ref_%d_%d.bin", size, idx);
    long rn; unsigned char *ref = load_fix(name, &rn);
    unsigned int w, hgt;
    memcpy(&w, ref, 4); memcpy(&hgt, ref + 4, 4);
    snprintf(name, sizeof name, "font_atlas_%d.bin", size);
    unsigned char *atlas = load_fix(name, NULL);
    unsigned char *out = calloc(1, (size_t)w * hgt);
    int rc = ntx_render(atlas, string, out, (int)w, (int)hgt);
    if (rc != 0) { printf("  FAIL  %s: ntx_render rc=%d\n", label, rc); t_fail++; }
    else bytes_equal(label, out, ref + 8, (int)(w * hgt));
    free(txt); free(string); free(ref); free(atlas); free(out);
}

static void test_text_matches_pillow_draw_text(void) {
    const int sizes[] = {14, 18, 20, 24};
    for (int s = 0; s < 4; s++) {
        char label[80];
        for (int i = 0; i < 4; i++) {
            snprintf(label, sizeof label, "text ref %d @ %dpx matches Pillow", i, sizes[s]);
            text_case_sz(sizes[s], i, label);
        }
    }
}

static void bbox_case(int size, int idx) {
    char name[64], label[96];
    snprintf(name, sizeof name, "text_ref_%d_%d.txt", size, idx);
    long tn; unsigned char *txt = load_fix(name, &tn);
    char *str = malloc(tn + 1); memcpy(str, txt, tn); str[tn] = 0;
    snprintf(name, sizeof name, "text_bbox_%d_%d.bin", size, idx);
    unsigned char *bb = load_fix(name, NULL);
    int want[4]; memcpy(want, bb, 16);
    snprintf(name, sizeof name, "font_atlas_%d.bin", size);
    unsigned char *atlas = load_fix(name, NULL);
    int x0, y0, x1, y1;
    int rc = ntx_bbox(atlas, str, &x0, &y0, &x1, &y1);
    snprintf(label, sizeof label, "bbox '%s' @%dpx matches Pillow textbbox", str, size);
    CHECK(label, rc == 0 && x0 == want[0] && y0 == want[1] &&
                 x1 == want[2] && y1 == want[3]);
    free(txt); free(str); free(bb); free(atlas);
}

static void draw_case(int size, int idx) {
    char name[64], label[96];
    snprintf(name, sizeof name, "text_ref_%d_%d.txt", size, idx);
    long tn; unsigned char *txt = load_fix(name, &tn);
    char *str = malloc(tn + 1); memcpy(str, txt, tn); str[tn] = 0;
    snprintf(name, sizeof name, "text_draw_%d_%d.bin", size, idx);
    unsigned char *want = load_fix(name, NULL);
    snprintf(name, sizeof name, "font_atlas_%d.bin", size);
    unsigned char *atlas = load_fix(name, NULL);
    unsigned char *cv = calloc(1, 240 * 175 * 3);
    int rc = ntx_draw(atlas, str, cv, 240, 175, 30, 40, 255, 128, 0);
    snprintf(label, sizeof label, "draw '%s' @%dpx matches Pillow draw.text", str, size);
    if (rc != 0) { printf("  FAIL  %s rc=%d\n", label, rc); t_fail++; }
    else bytes_equal(label, cv, want, 240 * 175 * 3);
    free(txt); free(str); free(want); free(atlas); free(cv);
}

static void test_bbox_and_draw_match_pillow(void) {
    const int sizes[] = {14, 20, 24};
    for (int s = 0; s < 3; s++) {
        bbox_case(sizes[s], 1);
        draw_case(sizes[s], 1);
    }
    bbox_case(14, 3);
    draw_case(14, 3);
}

int main(void) {
    test_fill_rect_writes_expected_bytes();
    test_fill_rect_clips_to_buffer();
    test_rgb_to_bgra_matches_pillow();
    test_rgb_to_565le_matches_shipping_pack();
    test_blit_rgba_matches_pillow_paste();
    test_blit_full_canvas_random();
    test_text_matches_pillow_draw_text();
    test_bbox_and_draw_match_pillow();
    return SUMMARY();
}
