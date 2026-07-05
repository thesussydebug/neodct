#!/bin/sh
set -eu

TARGET_DIR="${1:-}"
FLAVOR="${2:-}"
if [ -z "$TARGET_DIR" ] || [ ! -d "$TARGET_DIR" ]; then
    echo "[post-build] Missing TARGET_DIR" >&2
    exit 1
fi

rm -rf "$TARGET_DIR/tests"

# Luckfox-specific console config: replace generic inittab
# only when called with the explicit luckfox flavor argument.
LUCKFOX_INITTAB="$TARGET_DIR/etc/inittab.luckfox"
if [ "$FLAVOR" = "luckfox" ]; then
    if [ -f "$LUCKFOX_INITTAB" ]; then
        cp "$LUCKFOX_INITTAB" "$TARGET_DIR/etc/inittab"
    fi
fi
# Either way, don't ship the flavor-specific file itself
rm -f "$LUCKFOX_INITTAB"
