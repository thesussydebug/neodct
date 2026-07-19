#!/usr/bin/env python3
"""Golden framebuffer image produced by main.py's own present path:
240x175 canvas, 32bpp 240x240 fb, centered band write."""

import os
import random

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
os.makedirs(FIX, exist_ok=True)

XRES = YRES = 240
CW, CH = 240, 175
BPP_BYTES = 4
LINE = XRES * BPP_BYTES
FILL = 0xAA

random.seed(11)
canvas = bytes(random.randrange(256) for _ in range(CW * CH * 3))
open(os.path.join(FIX, "fb_canvas_rgb.bin"), "wb").write(canvas)

band = Image.frombytes("RGB", (CW, CH), canvas).convert("RGBA").tobytes("raw", "BGRA")

dst_y = (YRES - CH) // 2
mem = bytearray([FILL]) * (XRES * YRES * BPP_BYTES)
mem[dst_y * LINE:dst_y * LINE + len(band)] = band
open(os.path.join(FIX, "fb_expected.bin"), "wb").write(bytes(mem))

print(f"fb fixture: {CW}x{CH} canvas -> {XRES}x{YRES}@32bpp, band at y={dst_y}")

import shutil
NDO = os.path.join(HERE, "../../../overlay/NeoDCT")
shutil.copy(os.path.join(NDO, "System/ui/resources/ui_home.json"),
            os.path.join(FIX, "ui_home.json"))
print("copied real ui_home.json into fixtures")
