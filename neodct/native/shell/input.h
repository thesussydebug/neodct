#ifndef NIN_INPUT_H
#define NIN_INPUT_H

#include <stddef.h>
#include <stdint.h>

struct nin_key {
    int code;
    int value;
};

size_t nin_event_size(void);

int nin_decode(const uint8_t *buf, size_t len, struct nin_key *out, int max);

#endif
