#!/usr/bin/env python3
"""Embed tests/fixtures/*.bin into a C table so the test runner is a single
self-contained binary (for running on the target)."""

import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
out = [
    "#include <stddef.h>",
    "struct npx_fix { const char *name; const unsigned char *data; long len; };",
]
entries = []
for path in sorted(glob.glob(os.path.join(HERE, "fixtures", "*.bin"))):
    name = os.path.basename(path)
    ident = "fx_" + name.replace(".", "_").replace("-", "_")
    data = open(path, "rb").read()
    body = ",".join(str(b) for b in data)
    out.append(f"static const unsigned char {ident}[] = {{{body}}};")
    entries.append(f'    {{"{name}", {ident}, {len(data)}}},')
out.append("const struct npx_fix npx_fixtures[] = {")
out.extend(entries)
out.append("};")
out.append(f"const int npx_fixture_count = {len(entries)};")

with open(os.path.join(HERE, "fixtures_embed.c"), "w") as f:
    f.write("\n".join(out) + "\n")
print(f"embedded {len(entries)} fixtures")
