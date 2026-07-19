#include "neozlib.h"

#include <string.h>

#define MAX_BITS 15

struct bits {
    const uint8_t *src;
    long len, pos;
    uint32_t acc;
    int have;
};

static int need(struct bits *b, int n) {
    while (b->have < n) {
        if (b->pos >= b->len) return -1;
        b->acc |= (uint32_t)b->src[b->pos++] << b->have;
        b->have += 8;
    }
    return 0;
}

static int getbits(struct bits *b, int n, uint32_t *out) {
    if (n == 0) { *out = 0; return 0; }
    if (need(b, n) < 0) return -1;
    *out = b->acc & ((1u << n) - 1);
    b->acc >>= n;
    b->have -= n;
    return 0;
}

struct huff {
    uint16_t counts[MAX_BITS + 1];
    uint16_t symbols[288];
};

static void huff_build(struct huff *h, const uint8_t *lengths, int n) {
    memset(h->counts, 0, sizeof h->counts);
    for (int i = 0; i < n; i++) h->counts[lengths[i]]++;
    h->counts[0] = 0;
    uint16_t offs[MAX_BITS + 2];
    offs[1] = 0;
    for (int i = 1; i <= MAX_BITS; i++) offs[i + 1] = offs[i] + h->counts[i];
    for (int i = 0; i < n; i++)
        if (lengths[i]) h->symbols[offs[lengths[i]]++] = (uint16_t)i;
}

static int huff_decode(struct bits *b, const struct huff *h) {
    int code = 0, first = 0, index = 0;
    for (int len = 1; len <= MAX_BITS; len++) {
        uint32_t bit;
        if (getbits(b, 1, &bit) < 0) return -1;
        code |= (int)bit;
        int count = h->counts[len];
        if (code - first < count) return h->symbols[index + (code - first)];
        index += count;
        first = (first + count) << 1;
        code <<= 1;
    }
    return -1;
}

static const uint16_t LBASE[] = {3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,
                                 51,59,67,83,99,115,131,163,195,227,258};
static const uint8_t LEXTRA[] = {0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,
                                 4,4,4,4,5,5,5,5,0};
static const uint16_t DBASE[] = {1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,
                                 385,513,769,1025,1537,2049,3073,4097,6145,8193,
                                 12289,16385,24577};
static const uint8_t DEXTRA[] = {0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,
                                 9,9,10,10,11,11,12,12,13,13};

static long emit_block(struct bits *b, const struct huff *lit,
                       const struct huff *dist, uint8_t *out,
                       long cap, long written) {
    for (;;) {
        int sym = huff_decode(b, lit);
        if (sym < 0) return -1;
        if (sym < 256) {
            if (written >= cap) return -1;
            out[written++] = (uint8_t)sym;
        } else if (sym == 256) {
            return written;
        } else {
            sym -= 257;
            if (sym >= 29) return -1;
            uint32_t extra;
            if (getbits(b, LEXTRA[sym], &extra) < 0) return -1;
            int length = LBASE[sym] + (int)extra;

            int dsym = huff_decode(b, dist);
            if (dsym < 0 || dsym >= 30) return -1;
            if (getbits(b, DEXTRA[dsym], &extra) < 0) return -1;
            long distance = DBASE[dsym] + (long)extra;
            if (distance > written) return -1;
            if (written + length > cap) return -1;
            for (int i = 0; i < length; i++) {
                out[written] = out[written - distance];
                written++;
            }
        }
    }
}

static void fixed_tables(struct huff *lit, struct huff *dist) {
    uint8_t lengths[288];
    for (int i = 0; i < 144; i++) lengths[i] = 8;
    for (int i = 144; i < 256; i++) lengths[i] = 9;
    for (int i = 256; i < 280; i++) lengths[i] = 7;
    for (int i = 280; i < 288; i++) lengths[i] = 8;
    huff_build(lit, lengths, 288);
    for (int i = 0; i < 30; i++) lengths[i] = 5;
    huff_build(dist, lengths, 30);
}

static int dynamic_tables(struct bits *b, struct huff *lit, struct huff *dist) {
    static const uint8_t ORDER[19] = {16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};
    uint32_t hlit, hdist, hclen;
    if (getbits(b, 5, &hlit) < 0) return -1;
    if (getbits(b, 5, &hdist) < 0) return -1;
    if (getbits(b, 4, &hclen) < 0) return -1;
    int nlit = (int)hlit + 257, ndist = (int)hdist + 1, ncode = (int)hclen + 4;

    uint8_t clen[19];
    memset(clen, 0, sizeof clen);
    for (int i = 0; i < ncode; i++) {
        uint32_t v;
        if (getbits(b, 3, &v) < 0) return -1;
        clen[ORDER[i]] = (uint8_t)v;
    }
    struct huff cl;
    huff_build(&cl, clen, 19);

    uint8_t lengths[320];
    memset(lengths, 0, sizeof lengths);
    int n = 0;
    while (n < nlit + ndist) {
        int sym = huff_decode(b, &cl);
        if (sym < 0) return -1;
        uint32_t extra;
        if (sym < 16) {
            lengths[n++] = (uint8_t)sym;
        } else if (sym == 16) {
            if (n == 0) return -1;
            if (getbits(b, 2, &extra) < 0) return -1;
            uint8_t prev = lengths[n - 1];
            for (uint32_t i = 0; i < extra + 3 && n < nlit + ndist; i++) lengths[n++] = prev;
        } else if (sym == 17) {
            if (getbits(b, 3, &extra) < 0) return -1;
            for (uint32_t i = 0; i < extra + 3 && n < nlit + ndist; i++) lengths[n++] = 0;
        } else {
            if (getbits(b, 7, &extra) < 0) return -1;
            for (uint32_t i = 0; i < extra + 11 && n < nlit + ndist; i++) lengths[n++] = 0;
        }
    }
    huff_build(lit, lengths, nlit);
    huff_build(dist, lengths + nlit, ndist);
    return 0;
}

long nzl_inflate(const uint8_t *in, long in_len, uint8_t *out, long out_cap) {
    if (in_len < 2) return -1;
    if ((in[0] & 0x0F) != 8) return -1;
    if (((in[0] << 8) | in[1]) % 31 != 0) return -1;

    struct bits b = { in, in_len, 2, 0, 0 };
    long written = 0;

    for (;;) {
        uint32_t final, type;
        if (getbits(&b, 1, &final) < 0) return -1;
        if (getbits(&b, 2, &type) < 0) return -1;

        if (type == 0) {
            b.acc = 0;
            b.have = 0;
            if (b.pos + 4 > b.len) return -1;
            int len = in[b.pos] | (in[b.pos + 1] << 8);
            b.pos += 4;
            if (b.pos + len > b.len || written + len > out_cap) return -1;
            memcpy(out + written, in + b.pos, (size_t)len);
            b.pos += len;
            written += len;
        } else if (type == 1 || type == 2) {
            struct huff lit, dist;
            if (type == 1) fixed_tables(&lit, &dist);
            else if (dynamic_tables(&b, &lit, &dist) < 0) return -1;
            written = emit_block(&b, &lit, &dist, out, out_cap, written);
            if (written < 0) return -1;
        } else {
            return -1;
        }

        if (final) break;
    }
    return written;
}
