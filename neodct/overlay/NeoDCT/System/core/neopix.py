"""ctypes bridge to libneopix; falls back cleanly when the lib is absent."""

import ctypes
import os

_LIB_PATH = os.environ.get("NEODCT_NEOPIX_LIB", "/NeoDCT/lib/libneopix.so")

stats = {"bgra_calls": 0, "p565_calls": 0}

_lib = None
try:
    _lib = ctypes.CDLL(_LIB_PATH)
    _lib.npx_rgb_to_bgra.argtypes = (ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int)
    _lib.npx_rgb_to_bgra.restype = None
    _lib.npx_rgb_to_565le.argtypes = (ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int)
    _lib.npx_rgb_to_565le.restype = None
except OSError:
    _lib = None


def available():
    return _lib is not None


def rgb_to_bgra(rgb_bytes, out_bytearray):
    stats["bgra_calls"] += 1
    buf = (ctypes.c_char * len(out_bytearray)).from_buffer(out_bytearray)
    _lib.npx_rgb_to_bgra(rgb_bytes, buf, len(rgb_bytes) // 3)


def rgb_to_565le(rgb_bytes, out_bytearray):
    stats["p565_calls"] += 1
    buf = (ctypes.c_char * len(out_bytearray)).from_buffer(out_bytearray)
    _lib.npx_rgb_to_565le(rgb_bytes, buf, len(rgb_bytes) // 3)
