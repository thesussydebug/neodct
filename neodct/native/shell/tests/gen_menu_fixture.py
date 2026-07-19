#!/usr/bin/env python3
"""Golden menu screen drawn by AppSelector.draw()'s own logic."""
import json, glob, os, shutil
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NDO = os.path.join(HERE, "../../../overlay/NeoDCT")
FONT = os.path.join(NDO, "System/ui/resources/fonts/font.ttf")

W, H, SOFT = 240, 175, 30
content_bottom = H - SOFT
header_y = max(30, int(H * 0.11))
ICON_MAX = 175

apps = []
for base in ("System/apps", "System/engineering/apps"):
    for mf in glob.glob(f"{NDO}/{base}/*/manifest.json"):
        m = json.load(open(mf))
        icon = os.path.join(os.path.dirname(mf), "icon.png")
        apps.append({"id": int(m.get("id", 999)), "name": m.get("name", "?"),
                     "icon": icon if os.path.exists(icon) else None})
apps.sort(key=lambda a: a["id"])

fonts = {"n": ImageFont.truetype(FONT, 20), "xl": ImageFont.truetype(FONT, 24)}

SEL = 0
app = apps[SEL]
canvas = Image.new("RGB", (W, H), "black")
d = ImageDraw.Draw(canvas)

def tsize(t, f):
    b = d.textbbox((0, 0), t, font=f)
    return b[2] - b[0], b[3] - b[1]

w, h = tsize(app["name"], fonts["xl"])
d.text(((W - w) // 2, header_y - 16), app["name"], font=fonts["xl"], fill="white")

icon_y = header_y + max(24, int((content_bottom - header_y) * 0.22))
icon_cap = min(ICON_MAX, max(24, content_bottom - icon_y - 8))
im = Image.open(app["icon"]).convert("RGBA")
if im.width > icon_cap or im.height > icon_cap:
    im.thumbnail((icon_cap, icon_cap), Image.Resampling.LANCZOS)
canvas.paste(im, ((W - im.width) // 2, icon_y), im)
shutil.copy(app["icon"], os.path.join(FIX, "menu_icon.png"))

w, h = tsize("Select", fonts["n"])
d.text(((W - w) // 2, content_bottom + max(0, (SOFT - h) // 2)), "Select",
       font=fonts["n"], fill="white")

bar_x = W - 8
track_top = header_y + 6
track_bottom = max(track_top, content_bottom - 10)
d.line((bar_x, track_top, bar_x, track_bottom), fill="white", width=2)
step = (track_bottom - track_top) / (len(apps) - 1) if len(apps) > 1 else 0
notch_y = track_top + SEL * step
d.rectangle((bar_x - 4, notch_y - 3, bar_x + 2, notch_y + 3), fill="white")

page = str(SEL + 1)
w, h = tsize(page, fonts["n"])
d.text((W - 5 - w, 10), page, font=fonts["n"], fill="white")

open(os.path.join(FIX, "menu_expected.bin"), "wb").write(canvas.tobytes())
open(os.path.join(FIX, "menu_meta.txt"), "w").write(
    f"{app['name']}\n{len(apps)}\n{SEL}\n{im.width} {im.height}\n")
print(f"menu golden: '{app['name']}' icon {im.width}x{im.height}, {len(apps)} apps")
