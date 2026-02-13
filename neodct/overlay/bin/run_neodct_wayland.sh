#!/bin/sh

# 1. Silence Kernel Messages
dmesg -n 1

# 2. Disable tty echo
stty -echo -tostop

# 3. Hide cursor
printf "\033[?25l"
clear

echo "[NeoDCT] Booting (Wayland mode)..."

export NEODCT_BACKEND=wayland
export GDK_BACKEND=wayland
export GDK_GL=gles
export NEODCT_WAYLAND_SCALE="${NEODCT_WAYLAND_SCALE:-1}"
export NEODCT_WAYLAND_FULLSCREEN="${NEODCT_WAYLAND_FULLSCREEN:-1}"

# If launched by a compositor service, reuse it.
if [ -n "${WAYLAND_DISPLAY}" ]; then
    python3 /NeoDCT/launcher.py 2> /NeoDCT/crash.log
    EXIT_CODE=$?
else
    # Fallback for dev/QEMU images that include cage.
    if command -v cage >/dev/null 2>&1; then
        mkdir -p /run/user/0
        chmod 700 /run/user/0
        export XDG_RUNTIME_DIR=/run/user/0
        mkdir -p /dev/shm
        if ! grep -q " /dev/shm " /proc/mounts 2>/dev/null; then
            mount -t tmpfs tmpfs /dev/shm
        fi

        cage -- python3 /NeoDCT/launcher.py 2> /NeoDCT/crash.log
        EXIT_CODE=$?
    else
        echo "[NeoDCT] No WAYLAND_DISPLAY and no cage found, falling back to direct launch."
        python3 /NeoDCT/launcher.py 2> /NeoDCT/crash.log
        EXIT_CODE=$?
    fi
fi

# Crash handler shell (same behavior as framebuffer launcher)
stty echo tostop
printf "\033[?25h"

printf "\033[41m\033[1;97m"
clear
echo "=============================="
echo "   CRITICAL SYSTEM FAILURE    "
echo "=============================="
echo " CODE: $EXIT_CODE"
echo "=============================="
printf "\033[0m"

echo ""
echo "Dev Shell Active!"
echo "------------------------------"
export PS1="(CRASH)# "
/bin/sh
