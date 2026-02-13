#!/bin/sh

echo "Starting WebBrowser"

if [ -n "${WAYLAND_DISPLAY}" ]; then
    echo "Wayland session detected: ${WAYLAND_DISPLAY}"
    env GDK_GL=gles python3 /tests/neodct-browser/main.py > /dev/ttyAMA0 2>&1
else
    sh /tests/neodct-browser/start.sh > /dev/ttyAMA0 2>&1
fi
