#!/usr/bin/env python3
"""Pillow LANCZOS resizes of real sprites: oracle for the C resampler."""
import os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NDO = os.path.join(HERE, "../../../overlay/NeoDCT")

cases = [
    ("bat4", "System/ui/resources/img/battery/bat-4.png", 175 / 240.0),
    ("env",  "System/ui/resources/img/envelope.png",      175 / 240.0),
    ("icon", "System/apps/Calculator/icon.png",           0.5),
]
names = []
for tag, rel, scale in cases:
    im = Image.open(os.path.join(NDO, rel)).convert("RGBA")
    w = max(1, int(im.width * scale))
    h = max(1, int(im.height * scale))
    out = im.resize((w, h), Image.Resampling.LANCZOS)
    open(os.path.join(FIX, f"rs_{tag}_src.bin"), "wb").write(im.tobytes())
    open(os.path.join(FIX, f"rs_{tag}_dim.txt"), "w").write(
        f"{im.width} {im.height} {w} {h}")
    open(os.path.join(FIX, f"rs_{tag}_out.bin"), "wb").write(out.tobytes())
    names.append(f"{tag} {im.width}x{im.height}->{w}x{h}")
open(os.path.join(FIX, "rs_list.txt"), "w").write("\n".join(t for t, _, _ in cases))
print("resize fixtures:", "; ".join(names))
