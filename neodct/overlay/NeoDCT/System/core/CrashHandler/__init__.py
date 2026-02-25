"""Crash handling UX helpers for NeoDCT.

Behavior:
- Engineering mode ON: show a full-screen crash image with a "Continue" softkey.
- Engineering mode OFF: show a simple notice dialog.
"""

from __future__ import annotations

import os
import select

from PIL import Image

from System.ui.framework import MessageDialog, SoftKeyBar

CRASH_IMAGE_PATH = "/NeoDCT/System/ui/resources/CRASH.jpg"
DEFAULT_NOTICE = "An application has crashed."
CONTINUE_KEYS = {14, 28, 46, 50, 96}


def _is_engineering_mode(ui, default=False):
    value = getattr(ui, "engineering_mode", None)
    if value is None:
        return default
    return bool(value)


def _flush_input(ui):
    fd = getattr(ui, "keypad_fd", None)
    if fd is None:
        return
    while True:
        r, _, _ = select.select([fd], [], [], 0.0)
        if not r:
            break
        try:
            os.read(fd, 24)
        except Exception:
            break


def _draw_engineering_crash_screen(ui):
    screen_w = int(getattr(ui, "W", 240))
    screen_h = int(getattr(ui, "H", 175))
    softkey_h = int(getattr(ui, "SOFTKEY_H", 30))
    content_bottom = int(getattr(ui, "content_bottom", screen_h - softkey_h))

    ui.draw.rectangle((0, 0, screen_w, screen_h), fill="black")

    crash_img = None
    try:
        crash_img = Image.open(CRASH_IMAGE_PATH).convert("RGB")
    except Exception:
        crash_img = None

    if crash_img is not None:
        # Draw full frame; softkey bar intentionally overlays the bottom strip.
        crash_img = crash_img.resize((screen_w, screen_h), Image.Resampling.LANCZOS)
        ui.canvas.paste(crash_img, (0, 0))
    else:
        # Fallback if image file is missing or unreadable.
        text = "CRASH"
        font = getattr(ui, "font_xl", None) or getattr(ui, "font_n", None) or getattr(ui, "font_s", None)
        if font is not None:
            w, h = ui.get_text_size(text, font)
            x = (screen_w - w) // 2
            y = max(0, (content_bottom - h) // 2)
            ui.draw.text((x, y), text, font=font, fill="white")

    SoftKeyBar(ui).update("Continue", present=False)
    ui.fb.update(ui.canvas)


def _wait_for_continue(ui):
    while True:
        key = ui.wait_for_key()
        if key in CONTINUE_KEYS:
            return key


def show_app_crash(ui, message=DEFAULT_NOTICE):
    """Display the crash UX for app failures.

    This function must never raise into the caller.
    """
    try:
        if _is_engineering_mode(ui, default=False):
            _flush_input(ui)
            _draw_engineering_crash_screen(ui)
            _wait_for_continue(ui)
            return

        MessageDialog(ui, message).show()
    except Exception:
        # Never let crash UI handling create a secondary crash.
        return
