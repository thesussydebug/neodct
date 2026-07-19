#include "../neopix.h"
#include "runner.h"
#include <stdlib.h>

static void rs_case(const char *tag) {
    char f[64], label[128];
    snprintf(f, sizeof f, "rs_%s_src.bin", tag);
    unsigned char *src = load_fix(f, NULL);
    snprintf(f, sizeof f, "rs_%s_dim.txt", tag);
    long dlen; unsigned char *dim = load_fix(f, &dlen);
    char dbuf[64];
    long dn = dlen < (long)sizeof dbuf - 1 ? dlen : (long)sizeof dbuf - 1;
    memcpy(dbuf, dim, dn); dbuf[dn] = 0;
    int sw, sh, dw, dh;
    if (sscanf(dbuf, "%d %d %d %d", &sw, &sh, &dw, &dh) != 4) {
        printf("  FAIL  %s: bad dim fixture\n", tag); t_fail++;
        free(src); free(dim); return;
    }
    snprintf(f, sizeof f, "rs_%s_out.bin", tag);
    unsigned char *want = load_fix(f, NULL);

    unsigned char *got = malloc((size_t)dw * dh * 4);
    int rc = npx_resize_rgba(src, sw, sh, got, dw, dh);
    snprintf(label, sizeof label, "resize %s %dx%d->%dx%d matches Pillow LANCZOS",
             tag, sw, sh, dw, dh);
    if (rc != 0) { printf("  FAIL  %s: rc=%d\n", label, rc); t_fail++; }
    else bytes_equal(label, got, want, dw * dh * 4);
    free(src); free(dim); free(want); free(got);
}

int main(void) {
    long n; unsigned char *list = load_fix("rs_list.txt", &n);
    char *s = malloc(n + 1); memcpy(s, list, n); s[n] = 0;
    for (char *t = strtok(s, "\n"); t; t = strtok(NULL, "\n")) rs_case(t);
    free(list); free(s);
    return SUMMARY();
}
