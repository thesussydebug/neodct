CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Werror

TESTBINS := tests/run_input_tests tests/run_ui_tests tests/run_fb_tests tests/run_layout_tests tests/run_home_tests

test: fixtures $(TESTBINS)
	@for t in $(TESTBINS); do echo "-- $$t"; ./$$t || exit 1; done

tests/run_input_tests: tests/test_input.c input.c input.h
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. tests/test_input.c input.c -o $@

tests/run_ui_tests: tests/test_ui.c ui.c ui.h
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. tests/test_ui.c ui.c -o $@

tests/run_fb_tests: tests/test_fb.c fb.c fb.h ../neopix/neopix.c
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. -I../neopix tests/test_fb.c fb.c ../neopix/neopix.c -o $@

tests/run_layout_tests: tests/test_layout.c layout.c layout.h
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. tests/test_layout.c layout.c -o $@

tests/run_home_tests: tests/test_home.c home.c home.h layout.c ../neopix/neopix.c ../neopix/neotext.c
	$(CC) $(CFLAGS) -DTEST_DIR='"tests"' -I. -I../neopix tests/test_home.c home.c layout.c ../neopix/neopix.c ../neopix/neotext.c -o $@

fixtures:
	python3 tests/gen_fb_fixture.py
	python3 tests/gen_home_fixture.py
	cp ../neopix/tests/fixtures/font_atlas_*.bin tests/fixtures/ 2>/dev/null || true

clean:
	rm -f $(TESTBINS)

.PHONY: test fixtures clean

OVERLAY := ../../overlay/NeoDCT
SHELL_SRC := main.c fb.c home.c input.c layout.c ui.c ../neopix/neopix.c ../neopix/neotext.c

atlases:
	python3 tests/gen_font_atlases.py

targetshell: atlases
	docker run --rm --user 0:0 \
	  --mount "type=bind,src=$(abspath ../../..),dst=/src" \
	  --mount "type=volume,src=neodct-out-qemu,dst=/obj" \
	  registry.gitlab.com/buildroot.org/buildroot/base:20250218.2110 \
	  bash -c 'cd /src/neodct/native/shell && \
	    /obj/host/bin/aarch64-buildroot-linux-gnu-gcc -std=gnu99 -O2 -Wall -Wextra \
	      -I. -I../neopix $(SHELL_SRC) -lm -o /src/neodct/overlay/usr/bin/neodct-shell'

.PHONY: atlases targetshell
