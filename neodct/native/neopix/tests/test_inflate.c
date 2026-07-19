#include "../neozlib.h"
#include "runner.h"
#include <stdlib.h>

static void case_(const char *name) {
    char f[64], label[96];
    snprintf(f, sizeof f, "zl_%s_in.bin", name);
    long inlen; unsigned char *in = load_fix(f, &inlen);
    snprintf(f, sizeof f, "zl_%s_out.bin", name);
    long outlen; unsigned char *want = load_fix(f, &outlen);

    unsigned char *got = malloc(outlen ? outlen : 1);
    long n = nzl_inflate(in, inlen, got, outlen);
    snprintf(label, sizeof label, "inflate '%s' (%ld bytes)", name, outlen);
    if (n != outlen) { printf("  FAIL  %s: got %ld bytes want %ld\n", label, n, outlen); t_fail++; }
    else if (outlen == 0) { printf("  PASS  %s\n", label); t_pass++; }
    else bytes_equal(label, got, want, (int)outlen);
    free(in); free(want); free(got);
}

static void test_rejects_truncated_stream(void) {
    long inlen; unsigned char *in = load_fix("zl_dynamic_in.bin", &inlen);
    unsigned char out[64];
    CHECK("truncated stream is rejected", nzl_inflate(in, 12, out, sizeof out) < 0);
    free(in);
}

static void test_rejects_undersized_output(void) {
    long inlen; unsigned char *in = load_fix("zl_runs_in.bin", &inlen);
    unsigned char out[16];
    CHECK("undersized output buffer is rejected",
          nzl_inflate(in, inlen, out, sizeof out) < 0);
    free(in);
}

int main(void) {
    case_("stored"); case_("fixed"); case_("dynamic"); case_("runs"); case_("empty");
    test_rejects_truncated_stream();
    test_rejects_undersized_output();
    return SUMMARY();
}
