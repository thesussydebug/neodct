#include "input.h"

#include <string.h>

#define NIN_EV_KEY 1

/* Mirrors the kernel's struct input_event: timeval is two longs, so this is
   16 bytes on armv7 and 24 on aarch64 without per-arch #ifdefs. */
struct nin_input_event {
    long tv_sec;
    long tv_usec;
    uint16_t type;
    uint16_t code;
    int32_t value;
};

size_t nin_event_size(void) {
    return sizeof(struct nin_input_event);
}

int nin_decode(const uint8_t *buf, size_t len, struct nin_key *out, int max) {
    size_t es = sizeof(struct nin_input_event);
    int n = 0;
    for (size_t off = 0; off + es <= len && n < max; off += es) {
        struct nin_input_event ev;
        memcpy(&ev, buf + off, es);
        if (ev.type != NIN_EV_KEY) continue;
        out[n].code = ev.code;
        out[n].value = ev.value;
        n++;
    }
    return n;
}
