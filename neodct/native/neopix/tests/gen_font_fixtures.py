#!/usr/bin/env python3
"""Bake the project TTF into a glyph atlas fixture and render reference
strings with Pillow's draw.text — the parity oracle for C text rendering."""

import os
import struct

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
FONT = os.path.join(
    HERE, "../../../overlay/NeoDCT/System/ui/resources/fonts/font.ttf")
SIZES = (14, 18, 20, 24)
CHARS = [chr(c) for c in range(32, 127)]
REF_STRINGS = ["12:34", "No Service", "Menu", "NeoDCT 0.3.0a!?"]


def render_string(s, size):
    font = ImageFont.truetype(FONT, size)
    tmp = Image.new("L", (8, 8))
    d = ImageDraw.Draw(tmp)
    x0, y0, x1, y1 = d.textbbox((0, 0), s, font=font)
    img = Image.new("L", (x1 + 2, y1 + 2), 0)
    ImageDraw.Draw(img).text((0, 0), s, font=font, fill=255)
    return img


def bake(size):
    font = ImageFont.truetype(FONT, size)
    tmp = Image.new("L", (8, 8))
    d = ImageDraw.Draw(tmp)

    atlas = bytearray()
    atlas += struct.pack("<II", len(CHARS), size)
    for ch in CHARS:
        x0, y0, x1, y1 = d.textbbox((0, 0), ch, font=font)
        gw = max(0, x1 - x0)
        gh = max(0, y1 - y0)
        adv = d.textlength(ch, font=font)
        g = Image.new("L", (max(1, gw), max(1, gh)), 0)
        if gw and gh:
            ImageDraw.Draw(g).text((-x0, -y0), ch, font=font, fill=255)
        atlas += struct.pack("<iiiii", ord(ch), gw, gh, x0, y0)
        atlas += struct.pack("<d", adv)
        atlas += g.tobytes()
    with open(os.path.join(FIX, f"font_atlas_{size}.bin"), "wb") as f:
        f.write(atlas)

    for i, txt in enumerate(REF_STRINGS):
        bb = d.textbbox((0, 0), txt, font=font)
        with open(os.path.join(FIX, f"text_bbox_{size}_{i}.bin"), "wb") as f:
            f.write(struct.pack("<iiii", *bb))

        cw, ch = 240, 175
        cv = Image.new("RGB", (cw, ch), (0, 0, 0))
        ImageDraw.Draw(cv).text((30, 40), txt, font=font, fill=(255, 128, 0))
        with open(os.path.join(FIX, f"text_draw_{size}_{i}.bin"), "wb") as f:
            f.write(cv.tobytes())

        img = render_string(txt, size)
        with open(os.path.join(FIX, f"text_ref_{size}_{i}.bin"), "wb") as f:
            f.write(struct.pack("<II", img.width, img.height))
            f.write(img.tobytes())
        with open(os.path.join(FIX, f"text_ref_{size}_{i}.txt"), "w") as f:
            f.write(txt)


def main():
    for size in SIZES:
        bake(size)
    print(f"baked {len(CHARS)} glyphs x {len(SIZES)} sizes + references")


if __name__ == "__main__":
    main()
