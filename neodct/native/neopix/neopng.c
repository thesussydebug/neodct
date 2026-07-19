#include "neopng.h"

#include <stdlib.h>
#include <string.h>

#include "neozlib.h"

static uint32_t be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | p[3];
}

static int paeth(int a, int b, int c) {
    int p = a + b - c;
    int pa = p > a ? p - a : a - p;
    int pb = p > b ? p - b : b - p;
    int pc = p > c ? p - c : c - p;
    if (pa <= pb && pa <= pc) return a;
    if (pb <= pc) return b;
    return c;
}

static int unfilter_bytes(uint8_t *raw, long raw_len, long stride, int h, int bpp) {
    if (raw_len < (stride + 1) * h) return -1;
    uint8_t *prev = NULL;
    uint8_t *cur = raw;
    for (int y = 0; y < h; y++) {
        int ft = cur[0];
        uint8_t *line = cur + 1;
        for (long i = 0; i < stride; i++) {
            int a = i >= bpp ? line[i - bpp] : 0;
            int b = prev ? prev[i] : 0;
            int c = (prev && i >= bpp) ? prev[i - bpp] : 0;
            int x = line[i];
            switch (ft) {
                case 0: break;
                case 1: x += a; break;
                case 2: x += b; break;
                case 3: x += (a + b) / 2; break;
                case 4: x += paeth(a, b, c); break;
                default: return -1;
            }
            line[i] = (uint8_t)x;
        }
        prev = line;
        cur = line + stride;
    }
    return 0;
}

int npng_decode(const uint8_t *png, long len, int *w_out, int *h_out,
                uint8_t **rgba_out) {
    static const uint8_t SIG[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    if (len < 8 || memcmp(png, SIG, 8) != 0) return -1;

    int w = 0, h = 0, depth = 0, ctype = 0, interlace = 0;
    uint8_t palette[256][3];
    uint8_t trns[256];
    int have_plte = 0, ntrns = 0;
    memset(trns, 255, sizeof trns);

    uint8_t *idat = NULL;
    long idat_len = 0;

    long pos = 8;
    int seen_ihdr = 0, seen_iend = 0;
    while (pos + 8 <= len) {
        uint32_t clen = be32(png + pos);
        const uint8_t *ctag = png + pos + 4;
        const uint8_t *cdata = png + pos + 8;
        if (pos + 12 + (long)clen > len) { free(idat); return -2; }

        if (memcmp(ctag, "IHDR", 4) == 0 && clen >= 13) {
            w = (int)be32(cdata);
            h = (int)be32(cdata + 4);
            depth = cdata[8];
            ctype = cdata[9];
            interlace = cdata[12];
            seen_ihdr = 1;
        } else if (memcmp(ctag, "PLTE", 4) == 0) {
            int n = (int)clen / 3;
            if (n > 256) n = 256;
            for (int i = 0; i < n; i++) {
                palette[i][0] = cdata[i * 3];
                palette[i][1] = cdata[i * 3 + 1];
                palette[i][2] = cdata[i * 3 + 2];
            }
            have_plte = 1;
        } else if (memcmp(ctag, "tRNS", 4) == 0) {
            ntrns = (int)clen > 256 ? 256 : (int)clen;
            for (int i = 0; i < ntrns; i++) trns[i] = cdata[i];
        } else if (memcmp(ctag, "IDAT", 4) == 0) {
            uint8_t *grown = realloc(idat, idat_len + clen);
            if (!grown) { free(idat); return -3; }
            idat = grown;
            memcpy(idat + idat_len, cdata, clen);
            idat_len += clen;
        } else if (memcmp(ctag, "IEND", 4) == 0) {
            seen_iend = 1;
            break;
        }
        pos += 12 + clen;
    }

    if (!seen_ihdr || !seen_iend || !idat || w <= 0 || h <= 0) { free(idat); return -4; }
    if (interlace != 0) { free(idat); return -5; }
    if (ctype == 3) {
        if (depth != 1 && depth != 2 && depth != 4 && depth != 8) { free(idat); return -5; }
    } else if (depth != 8) { free(idat); return -5; }

    int channels;
    switch (ctype) {
        case 0: channels = 1; break;
        case 2: channels = 3; break;
        case 3: channels = 1; break;
        case 4: channels = 2; break;
        case 6: channels = 4; break;
        default: free(idat); return -6;
    }
    if (ctype == 3 && !have_plte) { free(idat); return -7; }

    long stride = ((long)w * channels * depth + 7) / 8;
    int filt_bpp = (channels * depth) / 8;
    if (filt_bpp < 1) filt_bpp = 1;
    long raw_cap = (stride + 1) * h;
    uint8_t *raw = malloc(raw_cap);
    if (!raw) { free(idat); return -3; }

    long got = nzl_inflate(idat, idat_len, raw, raw_cap);
    free(idat);
    if (got != raw_cap) { free(raw); return -8; }
    if (unfilter_bytes(raw, raw_cap, stride, h, filt_bpp) != 0) {
        free(raw);
        return -9;
    }

    uint8_t *rgba = malloc((size_t)w * h * 4);
    if (!rgba) { free(raw); return -3; }
    for (int y = 0; y < h; y++) {
        const uint8_t *line = raw + (stride + 1) * y + 1;
        uint8_t *dst = rgba + (long)y * w * 4;
        for (int x = 0; x < w; x++) {
            const uint8_t *px = line + (long)x * channels;
            uint8_t r, g, b, a = 255;
            int pidx = 0;
            if (ctype == 3) {
                if (depth == 8) pidx = px[0];
                else {
                    long bit = (long)x * depth;
                    int shift = 8 - depth - (int)(bit % 8);
                    pidx = (line[bit / 8] >> shift) & ((1 << depth) - 1);
                }
            }
            switch (ctype) {
                case 0: r = g = b = px[0]; break;
                case 2: r = px[0]; g = px[1]; b = px[2]; break;
                case 3:
                    r = palette[pidx][0]; g = palette[pidx][1]; b = palette[pidx][2];
                    a = pidx < ntrns ? trns[pidx] : 255;
                    break;
                case 4: r = g = b = px[0]; a = px[1]; break;
                default: r = px[0]; g = px[1]; b = px[2]; a = px[3]; break;
            }
            dst[x * 4 + 0] = r;
            dst[x * 4 + 1] = g;
            dst[x * 4 + 2] = b;
            dst[x * 4 + 3] = a;
        }
    }
    free(raw);

    *w_out = w;
    *h_out = h;
    *rgba_out = rgba;
    return 0;
}
