#!/usr/bin/env python3
"""zlib streams + expected plaintext: oracle for the C inflate."""
import os, random, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
random.seed(3)

cases = {
    "stored":  (bytes(random.randrange(256) for _ in range(300)), 0),
    "fixed":   (b"hello hello hello world\n" * 3, 9),
    "dynamic": (bytes(random.randrange(4) for _ in range(9000)), 9),
    "runs":    (b"A" * 5000 + b"B" * 300 + bytes(range(256)) * 8, 6),
    "empty":   (b"", 6),
}
for name, (raw, level) in cases.items():
    open(os.path.join(FIX, f"zl_{name}_in.bin"), "wb").write(zlib.compress(raw, level))
    open(os.path.join(FIX, f"zl_{name}_out.bin"), "wb").write(raw)
print(f"zlib fixtures: {', '.join(cases)}")
