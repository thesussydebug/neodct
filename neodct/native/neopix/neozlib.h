#ifndef NEOZLIB_H
#define NEOZLIB_H

#include <stdint.h>

long nzl_inflate(const uint8_t *in, long in_len, uint8_t *out, long out_cap);

#endif
