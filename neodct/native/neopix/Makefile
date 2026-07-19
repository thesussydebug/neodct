CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Werror

TESTBIN := tests/run_tests

test: fixtures $(TESTBIN) tests/run_inflate
	./$(TESTBIN)
	./tests/run_inflate

tests/run_inflate: tests/test_inflate.c neozlib.c neozlib.h tests/runner.h
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. tests/test_inflate.c neozlib.c -o $@

$(TESTBIN): tests/test_pix.c neopix.c neotext.c neopix.h neotext.h tests/runner.h
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. tests/test_pix.c neopix.c neotext.c -o $@

fixtures:
	python3 tests/gen_fixtures.py
	python3 tests/gen_zlib_fixtures.py

hostlib:
	$(CC) $(CFLAGS) -shared -fPIC neopix.c -o libneopix_host.dylib

TARGET_CC := /obj/host/bin/aarch64-buildroot-linux-gnu-gcc
targetlib:
	docker run --rm --user 0:0 \
	  --mount "type=bind,src=$(abspath ../../..),dst=/src" \
	  --mount "type=volume,src=neodct-out-qemu,dst=/obj" \
	  registry.gitlab.com/buildroot.org/buildroot/base:20250218.2110 \
	  bash -c '$(TARGET_CC) -std=c99 -O2 -Wall -Wextra -Werror -shared -fPIC \
	    /src/neodct/native/neopix/neopix.c \
	    -o /src/neodct/overlay/NeoDCT/lib/libneopix.so'

clean:
	rm -f $(TESTBIN) libneopix_host.dylib
	rm -f tests/fixtures/*.bin

.PHONY: test fixtures hostlib targetlib clean
