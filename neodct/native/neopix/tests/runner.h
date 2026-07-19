#ifndef NEOPIX_TEST_RUNNER_H
#define NEOPIX_TEST_RUNNER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int t_pass = 0, t_fail = 0;

#define CHECK(name, cond) do { \
    if (cond) { t_pass++; printf("  PASS  %s\n", name); } \
    else { t_fail++; printf("  FAIL  %s (%s:%d)\n", name, __FILE__, __LINE__); } \
} while (0)

__attribute__((unused))
static int bytes_equal(const char *name, const unsigned char *got,
                       const unsigned char *want, int n) {
    for (int i = 0; i < n; i++) {
        if (got[i] != want[i]) {
            printf("  FAIL  %s: byte %d got 0x%02X want 0x%02X\n",
                   name, i, got[i], want[i]);
            t_fail++;
            return 0;
        }
    }
    t_pass++;
    printf("  PASS  %s\n", name);
    return 1;
}

#ifdef EMBED_FIXTURES
struct npx_fix { const char *name; const unsigned char *data; long len; };
extern const struct npx_fix npx_fixtures[];
extern const int npx_fixture_count;

__attribute__((unused))
static unsigned char *load_fix(const char *name, long *len_out) {
    for (int i = 0; i < npx_fixture_count; i++) {
        if (strcmp(npx_fixtures[i].name, name) == 0) {
            unsigned char *buf = malloc(npx_fixtures[i].len);
            memcpy(buf, npx_fixtures[i].data, (size_t)npx_fixtures[i].len);
            if (len_out) *len_out = npx_fixtures[i].len;
            return buf;
        }
    }
    printf("  FAIL  missing embedded fixture %s\n", name);
    exit(2);
}
#else
__attribute__((unused))
static unsigned char *load_fix(const char *name, long *len_out) {
    char path[512];
    snprintf(path, sizeof path, "%s/fixtures/%s", TEST_DIR, name);
    FILE *f = fopen(path, "rb");
    if (!f) { printf("  FAIL  missing fixture %s\n", name); exit(2); }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    unsigned char *buf = malloc(n);
    if (fread(buf, 1, n, f) != (size_t)n) { exit(2); }
    fclose(f);
    if (len_out) *len_out = n;
    return buf;
}
#endif

#define SUMMARY() (printf("\n%d passed, %d failed\n", t_pass, t_fail), \
                   t_fail ? 1 : 0)

#endif
