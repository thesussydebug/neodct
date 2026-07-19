#ifndef NEOPNG_H
#define NEOPNG_H

#include <stdint.h>

int npng_decode(const uint8_t *png, long len, int *w, int *h, uint8_t **rgba);

#endif
