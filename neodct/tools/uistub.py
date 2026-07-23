"""Headless stub of the NeoDCT runtime.

Lets host tooling drive the *real* UI code (System/core/main.py,
System/ui/framework.py, the shipped apps) with no framebuffer, no keypad,
no modem and no /NeoDCT rootfs. Frames are captured as PIL images instead
of being written to /dev/fb0.

Three pieces make that possible:

  CapturingFramebuffer  stands in for core.main.Framebuffer
  PathRemap             makes hardcoded "/NeoDCT/..." paths resolve into a
                        staged copy of the overlay
  KeyScript             replays a canned list of evdev key codes instead of
                        blocking on /dev/input/event0

Nothing here ships to the device; the overlay is the only thing copied
into the rootfs.
"""

import builtins
import os

from PIL import Image

# Device geometry (see System/core/main.py).
PANEL_W = 240
PANEL_H = 240
UI_W = 240
UI_H = 175

NEODCT_PREFIX = "/NeoDCT"


class CapturingFramebuffer:
    """Drop-in for core.main.Framebuffer that records frames.

    The real driver mmaps /dev/fb0 and blits the 240x175 UI band into the
    middle of the 240x240 panel. This keeps the band frames as handed over
    by the UI, and reproduces the letterboxed panel on demand.
    """

    def __init__(self, panel_size=(PANEL_W, PANEL_H)):
        self.panel_size = panel_size
        self.frames = []
        self.xres, self.yres = panel_size
        self.bpp = 32

    def update(self, pil_image):
        # Copy: the UI redraws onto one long-lived canvas, so a reference
        # would leave every captured frame showing the final screen.
        self.frames.append(pil_image.convert("RGB").copy())

    def device_frame(self, index=-1):
        """The band as the physical panel shows it, black bars included."""
        band = self.frames[index]
        panel = Image.new("RGB", self.panel_size, "black")
        panel.paste(
            band,
            ((self.panel_size[0] - band.width) // 2,
             (self.panel_size[1] - band.height) // 2),
        )
        return panel

    def clear(self):
        self.frames.clear()


class PathRemap:
    """Redirect absolute "/NeoDCT/..." paths into a staged overlay copy.

    The runtime hardcodes device paths (fonts, icons, layout JSON, sqlite
    databases). Rather than needing root to create /NeoDCT on the host,
    this patches the path-taking calls the runtime uses so they land in a
    staging directory instead.
    """

    # (module, attribute, index of the path argument)
    _TARGETS = (
        ("builtins", "open", 0),
        ("os.path", "exists", 0),
        ("os.path", "isfile", 0),
        ("os.path", "isdir", 0),
        ("os.path", "getsize", 0),
        ("os", "listdir", 0),
        ("os", "makedirs", 0),
        ("os", "mkdir", 0),
        ("os", "remove", 0),
        ("os", "stat", 0),
        ("os", "access", 0),
        ("sqlite3", "connect", 0),
        ("PIL.Image", "open", 0),
        ("PIL.ImageFont", "truetype", 0),
    )

    def __init__(self, staged_root):
        self.staged_root = str(staged_root).rstrip("/")
        self._saved = []

    def map_path(self, path):
        if isinstance(path, os.PathLike):
            path = os.fspath(path)
        if not isinstance(path, str):
            return path
        if path == NEODCT_PREFIX:
            return self.staged_root
        if path.startswith(NEODCT_PREFIX + "/"):
            return self.staged_root + path[len(NEODCT_PREFIX):]
        return path

    def _resolve(self, dotted):
        import importlib

        if dotted == "builtins":
            return builtins
        return importlib.import_module(dotted)

    def __enter__(self):
        for dotted, attr, arg_index in self._TARGETS:
            module = self._resolve(dotted)
            original = getattr(module, attr, None)
            if original is None:
                continue
            self._saved.append((module, attr, original))
            setattr(module, attr, self._wrap(original, arg_index))
        return self

    def _wrap(self, original, arg_index):
        remap = self.map_path

        def wrapper(*args, **kwargs):
            if len(args) > arg_index:
                args = list(args)
                args[arg_index] = remap(args[arg_index])
            return original(*args, **kwargs)

        wrapper.__name__ = getattr(original, "__name__", "wrapped")
        wrapper.__wrapped__ = original
        return wrapper

    def __exit__(self, exc_type, exc, tb):
        for module, attr, original in reversed(self._saved):
            setattr(module, attr, original)
        self._saved.clear()
        return False


class ScriptExhausted(BaseException):
    """Raised to unwind a blocking widget loop once the script runs out.

    Derives from BaseException (like core.main.IncomingCall) so that app
    code catching Exception cannot swallow it and spin forever.
    """


class KeyScript:
    """Replays evdev key codes in place of the keypad.

    on_exhausted="none"  -> pop() returns None (the runtime keeps polling)
    on_exhausted="raise" -> pop() raises ScriptExhausted to break a
                            blocking .show() loop once the script is done
    """

    def __init__(self, keys=(), on_exhausted="none"):
        self._keys = list(keys)
        self.on_exhausted = on_exhausted
        self.consumed = []

    def push(self, *keys):
        self._keys.extend(keys)

    def pop(self, timeout=0.1):
        if self._keys:
            key = self._keys.pop(0)
            self.consumed.append(key)
            return key
        if self.on_exhausted == "raise":
            raise ScriptExhausted()
        return None

    def __len__(self):
        return len(self._keys)
