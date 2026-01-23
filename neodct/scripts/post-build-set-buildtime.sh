#!/bin/sh
set -eu

TARGET_DIR="${1:-}"
if [ -z "$TARGET_DIR" ] || [ ! -d "$TARGET_DIR" ]; then
    echo "[post-build] Missing TARGET_DIR" >&2
    exit 1
fi

SETTINGS_FILE="$TARGET_DIR/NeoDCT/User/settings.prop"

if [ -n "${SOURCE_DATE_EPOCH:-}" ]; then
    BUILD_TIME="$(date -u -d "@$SOURCE_DATE_EPOCH" '+%Y-%m-%d %H:%M UTC' 2>/dev/null || \
        date -u -r "$SOURCE_DATE_EPOCH" '+%Y-%m-%d %H:%M UTC' 2>/dev/null || \
        date '+%Y-%m-%d %H:%M')"
else
    BUILD_TIME="$(date '+%Y-%m-%d %H:%M')"
fi

mkdir -p "$(dirname "$SETTINGS_FILE")"
touch "$SETTINGS_FILE"

escaped_build_time=$(printf '%s' "$BUILD_TIME" | sed 's/[&|]/\\&/g')
if grep -q '^system\.os\.buildtime=' "$SETTINGS_FILE"; then
    sed -i "s|^system\\.os\\.buildtime=.*|system.os.buildtime=${escaped_build_time}|" "$SETTINGS_FILE"
else
    printf '%s\n' "system.os.buildtime=${BUILD_TIME}" >> "$SETTINGS_FILE"
fi
