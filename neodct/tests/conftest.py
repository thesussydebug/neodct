# Host-side unit tests for NeoDCT (never shipped to the target).
# Make /NeoDCT-style absolute imports (System.hw..., System.ui...) work
# by putting the overlay root on sys.path, same as the device runtime.
import os
import sys

OVERLAY_NEODCT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "overlay", "NeoDCT",
)
if OVERLAY_NEODCT not in sys.path:
    sys.path.insert(0, OVERLAY_NEODCT)
