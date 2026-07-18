#!/bin/sh
[ -c "/dev/$1" ] || exec sleep 86400
exec /sbin/getty -L "$1" 115200 vt100
