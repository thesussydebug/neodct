#!/usr/bin/env python3
"""Golden home screen, drawn by main.py's own render_element logic
(text + icon_set bar fallback). Oracle for the C compositor."""

import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NDO = os.path.join(HERE, "../../../overlay/NeoDCT")
FONT = os.path.join(NDO, "System/ui/resources/fonts/font.ttf")

W, H = 240, 175

layout = json.load(open(os.path.join(NDO, "System/ui/resources/ui_home.json")))
for el in layout.get("elements", []):
    el.pop("custom_images", None)
open(os.path.join(FIX, "home_layout.json"), "w").write(json.dumps(layout))

fonts = {
    "s": ImageFont.truetype(FONT, 14),
    "n": ImageFont.truetype(FONT, 20),
    "xl": ImageFont.truetype(FONT, 24),
}

CLOCK = "07:30"

canvas = Image.new("RGB", (W, H), "black")
draw = ImageDraw.Draw(canvas)


def text_size(text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]


for el in layout["elements"]:
    x = int((el["x"] / 240.0) * W)
    y = int((el["y"] / 240.0) * H)

    if el["type"] == "text":
        size = el.get("font_size", 12)
        font = fonts["xl"] if size >= 20 else fonts["n"] if size >= 16 else fonts["s"]
        tw, th = text_size(el["text"], font)
        anchor = el.get("anchor", "")
        if "center_h" in anchor:
            x -= tw // 2
        elif "right" in anchor:
            x -= tw
        draw.text((x, y), el["text"], font=font, fill=el.get("color", "white"))

    elif el["type"] == "icon_set":
        count = el.get("count", 5)
        val = int(el.get("sim_val", 3))
        step = max(3, int(W * 0.021))
        for i in range(count):
            bh = (i + 1) * 3
            color = "white" if i <= val else "#333333"
            bx = x + (i * step)
            draw.rectangle((bx, y + 15 - bh, bx + 3, y + 15), fill=color)

with open(os.path.join(FIX, "home_expected.bin"), "wb") as f:
    f.write(canvas.tobytes())

canvas2 = Image.new("RGB", (W, H), "black")
draw = ImageDraw.Draw(canvas2)
for el in layout["elements"]:
    x = int((el["x"] / 240.0) * W)
    y = int((el["y"] / 240.0) * H)
    if el["type"] == "text":
        txt = CLOCK if el["text"] == "12:00" else el["text"]
        size = el.get("font_size", 12)
        font = fonts["xl"] if size >= 20 else fonts["n"] if size >= 16 else fonts["s"]
        tw, th = text_size(txt, font)
        anchor = el.get("anchor", "")
        if "center_h" in anchor:
            x -= tw // 2
        elif "right" in anchor:
            x -= tw
        draw.text((x, y), txt, font=font, fill=el.get("color", "white"))
    elif el["type"] == "icon_set":
        count = el.get("count", 5)
        val = int(el.get("sim_val", 3))
        step = max(3, int(W * 0.021))
        for i in range(count):
            bh = (i + 1) * 3
            color = "white" if i <= val else "#333333"
            bx = x + (i * step)
            draw.rectangle((bx, y + 15 - bh, bx + 3, y + 15), fill=color)
with open(os.path.join(FIX, "home_clock_expected.bin"), "wb") as f:
    f.write(canvas2.tobytes())

print(f"home golden: {W}x{H}, {len(layout['elements'])} elements (bar-icon fallback)")
