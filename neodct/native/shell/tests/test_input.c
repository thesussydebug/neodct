#include "../input.h"
#include "../../neopix/tests/runner.h"

#define EV_SYN 0
#define EV_KEY 1

/* Kernel layout: struct timeval (2 longs) then u16 type, u16 code, s32 value.
   16 bytes on armv7 (real hardware), 24 on aarch64 (QEMU). */
static size_t kernel_event_size(void) { return 2 * sizeof(long) + 8; }

static void put_event(uint8_t *p, uint16_t type, uint16_t code, int32_t value) {
    size_t off = 2 * sizeof(long);
    memset(p, 0, kernel_event_size());
    memcpy(p + off, &type, 2);
    memcpy(p + off + 2, &code, 2);
    memcpy(p + off + 4, &value, 4);
}

static void test_event_size_matches_kernel_layout(void) {
    CHECK("nin_event_size matches kernel input_event layout",
          nin_event_size() == kernel_event_size());
}

static void test_decodes_single_key_press(void) {
    uint8_t buf[64];
    put_event(buf, EV_KEY, 28, 1);
    struct nin_key keys[4];
    int n = nin_decode(buf, kernel_event_size(), keys, 4);
    CHECK("decodes one key press", n == 1 && keys[0].code == 28 && keys[0].value == 1);
}

static void test_decodes_press_then_release(void) {
    uint8_t buf[128];
    size_t es = kernel_event_size();
    put_event(buf, EV_KEY, 103, 1);
    put_event(buf + es, EV_KEY, 103, 0);
    struct nin_key keys[4];
    int n = nin_decode(buf, es * 2, keys, 4);
    CHECK("decodes press then release",
          n == 2 && keys[0].value == 1 && keys[1].value == 0 &&
          keys[0].code == 103 && keys[1].code == 103);
}

static void test_skips_non_key_events(void) {
    uint8_t buf[128];
    size_t es = kernel_event_size();
    put_event(buf, EV_SYN, 0, 0);
    put_event(buf + es, EV_KEY, 14, 1);
    struct nin_key keys[4];
    int n = nin_decode(buf, es * 2, keys, 4);
    CHECK("skips EV_SYN, keeps EV_KEY", n == 1 && keys[0].code == 14);
}

static void test_ignores_trailing_partial_event(void) {
    uint8_t buf[128];
    size_t es = kernel_event_size();
    put_event(buf, EV_KEY, 42, 1);
    memset(buf + es, 0xAB, es - 1);
    struct nin_key keys[4];
    int n = nin_decode(buf, es * 2 - 1, keys, 4);
    CHECK("ignores trailing partial event", n == 1 && keys[0].code == 42);
}

static void test_respects_output_capacity(void) {
    uint8_t buf[256];
    size_t es = kernel_event_size();
    for (int i = 0; i < 4; i++) put_event(buf + es * i, EV_KEY, 30 + i, 1);
    struct nin_key keys[2];
    int n = nin_decode(buf, es * 4, keys, 2);
    CHECK("never writes past out capacity", n == 2 && keys[1].code == 31);
}

int main(void) {
    test_event_size_matches_kernel_layout();
    test_decodes_single_key_press();
    test_decodes_press_then_release();
    test_skips_non_key_events();
    test_ignores_trailing_partial_event();
    test_respects_output_capacity();
    return SUMMARY();
}
