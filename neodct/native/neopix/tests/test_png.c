#include "../neopng.h"
#include "runner.h"
#include <stdlib.h>

static void png_case(const char *tag) {
    char f[80], label[128];
    snprintf(f, sizeof f, "png_%s.png", tag);
    long plen; unsigned char *png = load_fix(f, &plen);
    snprintf(f, sizeof f, "png_%s_rgba.bin", tag);
    long rlen; unsigned char *want = load_fix(f, &rlen);
    snprintf(f, sizeof f, "png_%s_dim.txt", tag);
    long dlen; unsigned char *dim = load_fix(f, &dlen);
    char dbuf[64];
    long dn = dlen < (long)sizeof dbuf - 1 ? dlen : (long)sizeof dbuf - 1;
    memcpy(dbuf, dim, dn); dbuf[dn] = 0;
    int ew = 0, eh = 0;
    sscanf(dbuf, "%d %d", &ew, &eh);

    int w = 0, h = 0;
    unsigned char *rgba = NULL;
    int rc = npng_decode(png, plen, &w, &h, &rgba);
    snprintf(label, sizeof label, "decode %s (%dx%d) matches Pillow RGBA", tag, ew, eh);
    if (rc != 0 || !rgba) { printf("  FAIL  %s: rc=%d\n", label, rc); t_fail++; }
    else if (w != ew || h != eh) {
        printf("  FAIL  %s: got %dx%d\n", label, w, h); t_fail++;
    } else bytes_equal(label, rgba, want, (int)rlen);
    free(png); free(want); free(dim); free(rgba);
}

static void test_rejects_non_png(void) {
    unsigned char junk[64];
    memset(junk, 0x42, sizeof junk);
    int w, h; unsigned char *out = NULL;
    CHECK("non-PNG data rejected", npng_decode(junk, sizeof junk, &w, &h, &out) != 0);
}

static void test_rejects_truncated_png(void) {
    long plen; unsigned char *png = load_fix("png_img_envelope.png", &plen);
    int w, h; unsigned char *out = NULL;
    CHECK("truncated PNG rejected", npng_decode(png, 40, &w, &h, &out) != 0);
    free(png);
}

int main(void) {
    long n; unsigned char *list = load_fix("png_list.txt", &n);
    char *s = malloc(n + 1); memcpy(s, list, n); s[n] = 0;
    char *tok = strtok(s, "\n");
    while (tok) { png_case(tok); tok = strtok(NULL, "\n"); }
    free(list); free(s);
    test_rejects_non_png();
    test_rejects_truncated_png();
    return SUMMARY();
}
