import os
import time
from collections import deque

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


class WaylandBackend:
    """
    Display + input backend for NeoDCT on Wayland/GTK.
    Keeps the existing PIL renderer and emits Linux-style keycodes.
    """

    def __init__(self, width=240, height=240):
        self.width = int(width)
        self.height = int(height)
        self.scale = max(1, int(os.environ.get("NEODCT_WAYLAND_SCALE", "1")))
        self.fullscreen = os.environ.get("NEODCT_WAYLAND_FULLSCREEN", "1") != "0"

        self._keys = deque()
        self._frame_bytes = None
        self._closed = False

        self._keymap = self._build_keymap()

        self.window = Gtk.Window(title="NeoDCT")
        self.window.set_resizable(False)
        self.window.set_decorated(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_keep_above(True)
        self.window.set_can_focus(True)
        self.window.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.window.set_default_size(self.width * self.scale, self.height * self.scale)
        self.window.connect("delete-event", self._on_delete)
        self.window.connect("key-press-event", self._on_key_press)

        self.image = Gtk.Image()
        self.image.set_size_request(self.width * self.scale, self.height * self.scale)
        self.window.add(self.image)

        self.window.show_all()
        if self.fullscreen:
            self.window.fullscreen()

        self._show_black_frame()
        self._hide_cursor()
        self._pump_events()
        self._focus_window()

    def _show_black_frame(self):
        out_w = self.width * self.scale
        out_h = self.height * self.scale
        raw = b"\x00" * (out_w * out_h * 3)
        self._frame_bytes = GLib.Bytes.new(raw)
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            self._frame_bytes,
            GdkPixbuf.Colorspace.RGB,
            False,
            8,
            out_w,
            out_h,
            out_w * 3,
        )
        self.image.set_from_pixbuf(pixbuf)

    def _focus_window(self):
        try:
            self.window.present()
            self.window.grab_focus()
        except Exception:
            pass

    def _hide_cursor(self):
        try:
            gdk_window = self.window.get_window()
            if not gdk_window:
                return
            display = Gdk.Display.get_default()
            if not display:
                return
            blank = Gdk.Cursor.new_for_display(display, Gdk.CursorType.BLANK_CURSOR)
            gdk_window.set_cursor(blank)
        except Exception:
            pass

    def _build_keymap(self):
        keymap = {
            Gdk.KEY_Return: 28,
            Gdk.KEY_KP_Enter: 28,
            Gdk.KEY_BackSpace: 14,
            Gdk.KEY_Escape: 14,
            Gdk.KEY_Up: 103,
            Gdk.KEY_Down: 108,
            Gdk.KEY_Left: 105,
            Gdk.KEY_Right: 106,
            Gdk.KEY_minus: 12,
            Gdk.KEY_KP_Subtract: 12,
            Gdk.KEY_comma: 51,
            Gdk.KEY_period: 52,
            Gdk.KEY_KP_Decimal: 52,
            Gdk.KEY_asterisk: 42,
            Gdk.KEY_space: 57,
            # Legacy app shortcuts some stubs still watch
            Gdk.KEY_m: 50,
            Gdk.KEY_M: 50,
            Gdk.KEY_c: 46,
            Gdk.KEY_C: 46,
        }

        number_codes = {
            Gdk.KEY_1: 2,
            Gdk.KEY_2: 3,
            Gdk.KEY_3: 4,
            Gdk.KEY_4: 5,
            Gdk.KEY_5: 6,
            Gdk.KEY_6: 7,
            Gdk.KEY_7: 8,
            Gdk.KEY_8: 9,
            Gdk.KEY_9: 10,
            Gdk.KEY_0: 11,
            Gdk.KEY_KP_1: 2,
            Gdk.KEY_KP_2: 3,
            Gdk.KEY_KP_3: 4,
            Gdk.KEY_KP_4: 5,
            Gdk.KEY_KP_5: 6,
            Gdk.KEY_KP_6: 7,
            Gdk.KEY_KP_7: 8,
            Gdk.KEY_KP_8: 9,
            Gdk.KEY_KP_9: 10,
            Gdk.KEY_KP_0: 11,
        }
        keymap.update(number_codes)

        letter_codes = {
            "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23, "o": 24, "p": 25,
            "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38,
            "z": 44, "x": 45, "c": 46, "v": 47, "b": 48, "n": 49, "m": 50,
        }
        for ch, code in letter_codes.items():
            low = getattr(Gdk, f"KEY_{ch}", None)
            up = getattr(Gdk, f"KEY_{ch.upper()}", None)
            if low is not None:
                keymap[low] = code
            if up is not None:
                keymap[up] = code

        return keymap

    def _pump_events(self):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

    def _on_delete(self, *_args):
        self._closed = True
        return False

    def _on_key_press(self, _widget, event):
        code = self._keymap.get(event.keyval)
        if code is not None:
            self._keys.append(code)
        return False

    def _to_pixbuf(self, pil_image):
        frame = pil_image
        if frame.mode != "RGB":
            frame = frame.convert("RGB")
        if frame.size != (self.width, self.height):
            frame = frame.resize((self.width, self.height))

        if self.scale != 1:
            frame = frame.resize((self.width * self.scale, self.height * self.scale))
            out_w = self.width * self.scale
            out_h = self.height * self.scale
        else:
            out_w = self.width
            out_h = self.height

        raw = frame.tobytes("raw", "RGB")
        self._frame_bytes = GLib.Bytes.new(raw)
        return GdkPixbuf.Pixbuf.new_from_bytes(
            self._frame_bytes,
            GdkPixbuf.Colorspace.RGB,
            False,
            8,
            out_w,
            out_h,
            out_w * 3,
        )

    def update(self, pil_image):
        try:
            pixbuf = self._to_pixbuf(pil_image)
            self.image.set_from_pixbuf(pixbuf)
            self._focus_window()
        except Exception as exc:
            print(f"[Wayland] Frame update error: {exc}")
        self._pump_events()

    def read_keypress(self, timeout=0.1):
        if self._closed:
            return 14

        timeout = max(0.0, float(timeout))
        deadline = time.monotonic() + timeout

        while True:
            self._pump_events()
            if self._keys:
                return self._keys.popleft()

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            time.sleep(min(0.01, remaining))

    def flush_input(self):
        self._pump_events()
        self._keys.clear()
