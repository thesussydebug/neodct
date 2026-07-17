#!/bin/sh
if [ ! -c "/dev/$1" ]; then
    while true; do sleep 86400; done
fi
exec /sbin/getty -L "$1" 115200 vt100
