#!/usr/bin/env python3
"""Bake the shipped TTF into runtime glyph atlases for the C shell."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../../neopix/tests"))
import gen_font_fixtures as G
OUT = os.path.join(HERE, "../../../overlay/NeoDCT/System/ui/resources/fonts")
os.makedirs(OUT, exist_ok=True)
import shutil
G.main()
for size in G.SIZES:
    src = os.path.join(G.FIX, f"font_atlas_{size}.bin")
    shutil.copy(src, os.path.join(OUT, f"atlas_{size}.bin"))
print(f"installed atlases {G.SIZES} into overlay")
