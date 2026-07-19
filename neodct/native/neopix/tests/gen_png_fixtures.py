#!/usr/bin/env python3
"""Every project PNG + Pillow's RGBA output: exhaustive oracle for the C decoder."""
import glob, os, shutil
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NDO = os.path.join(HERE, "../../../overlay/NeoDCT")

files = sorted(set(
    glob.glob(f"{NDO}/System/ui/resources/img/**/*.png", recursive=True) +
    glob.glob(f"{NDO}/System/apps/*/icon.png") +
    glob.glob(f"{NDO}/System/engineering/apps/*/icon.png")))

tags = []
for path in files:
    rel = os.path.relpath(path, NDO)
    tag = rel.replace("/", "_").replace(".png", "").replace("System_", "")
    im = Image.open(path)
    shutil.copy(path, os.path.join(FIX, f"png_{tag}.png"))
    rgba = im.convert("RGBA")
    open(os.path.join(FIX, f"png_{tag}_rgba.bin"), "wb").write(rgba.tobytes())
    open(os.path.join(FIX, f"png_{tag}_dim.txt"), "w").write(f"{rgba.width} {rgba.height}")
    tags.append(tag)
open(os.path.join(FIX, "png_list.txt"), "w").write("\n".join(tags))
print(f"png fixtures: {len(tags)} files (every PNG in the project)")
