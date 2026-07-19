#!/usr/bin/env python3
"""Golden home screen WITH real PNG status icons, drawn exactly as
main.py render_element + _get_status_icon do."""
import json, os, shutil
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NDO = os.path.join(HERE, "../../../overlay/NeoDCT")
FONT = os.path.join(NDO, "System/ui/resources/fonts/font.ttf")
W, H = 240, 175
SCALE = H / 240.0

layout = json.load(open(os.path.join(NDO, "System/ui/resources/ui_home.json")))
open(os.path.join(FIX, "home_icons_layout.json"), "w").write(json.dumps(layout))

fonts = {"s": ImageFont.truetype(FONT, 14),
         "n": ImageFont.truetype(FONT, 20),
         "xl": ImageFont.truetype(FONT, 24)}
canvas = Image.new("RGB", (W, H), "black")
draw = ImageDraw.Draw(canvas)

def status_icon(path):
    im = Image.open(os.path.join(NDO, path.replace("/NeoDCT/", ""))).convert("RGBA")
    w = max(1, int(im.width * SCALE))
    h = max(1, int(im.height * SCALE))
    if (w, h) != im.size:
        im = im.resize((w, h), Image.Resampling.LANCZOS)
    return im

copied = set()
for el in layout["elements"]:
    x = int((el["x"] / 240.0) * W)
    y = int((el["y"] / 240.0) * H)
    if el["type"] == "text":
        size = el.get("font_size", 12)
        f = fonts["xl"] if size >= 20 else fonts["n"] if size >= 16 else fonts["s"]
        b = draw.textbbox((0, 0), el["text"], font=f)
        tw = b[2] - b[0]
        a = el.get("anchor", "")
        if "center_h" in a: x -= tw // 2
        elif "right" in a: x -= tw
        draw.text((x, y), el["text"], font=f, fill=el.get("color", "white"))
    elif el["type"] == "icon_set":
        val = int(el.get("sim_val", 3))
        p = el.get("custom_images", {}).get(str(val))
        if p:
            img = status_icon(p)
            canvas.paste(img, (x, y), img)
            base = os.path.basename(p)
            if base not in copied:
                shutil.copy(os.path.join(NDO, p.replace("/NeoDCT/", "")),
                            os.path.join(FIX, "icon_" + base))
                copied.add(base)

open(os.path.join(FIX, "home_icons_expected.bin"), "wb").write(canvas.tobytes())
print(f"home+icons golden written ({len(copied)} sprites: {sorted(copied)})")
