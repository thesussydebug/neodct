import glob
import json
import os
import select
import time

from System.ui.framework import MessageDialog, SoftKeyBar

ROOT_ID = 10
OUTPUT_PATH = "/NeoDCT/User/keymap.json"
KEY_MENU = 50
GPIO_REQUIRED_MSG = "This app requires GPIO. GPIO devices not found. This application can not run in QEMU."

KEY_TARGETS = [
    ("navikey", "NaviKey"),
    ("clear", "C"),
    ("up", "Up"),
    ("down", "Down"),
    ("num_1", "1"),
    ("num_2", "2"),
    ("num_3", "3"),
    ("num_4", "4"),
    ("num_5", "5"),
    ("num_6", "6"),
    ("num_7", "7"),
    ("num_8", "8"),
    ("num_9", "9"),
    ("num_0", "0"),
    ("star", "*"),
    ("hash", "#"),
]


def _gpio_available():
    return len(glob.glob("/dev/gpiochip*")) > 0


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


def _wrap_text(ui, text, max_width, font):
    words = (text or "").split()
    if not words:
        return [""]

    lines = []
    current = ""

    def fits(candidate):
        width, _ = ui.get_text_size(candidate, font)
        return width <= max_width

    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if fits(candidate):
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


class KeypadMapper:
    def __init__(self, ui):
        self.ui = ui
        self.softkey = SoftKeyBar(ui)
        self.screen_w = getattr(ui, "W", 240)
        self.screen_h = getattr(ui, "H", 175)
        self.softkey_h = getattr(ui, "SOFTKEY_H", 30)
        self.content_bottom = getattr(ui, "content_bottom", self.screen_h - self.softkey_h)

    def _draw_capture_prompt(self, label, index, total):
        self.ui.draw.rectangle((0, 0, self.screen_w, self.screen_h), fill="black")

        title = "Keypad Mapper"
        tw, _ = self.ui.get_text_size(title, self.ui.font_n)
        self.ui.draw.text(((self.screen_w - tw) // 2, 8), title, font=self.ui.font_n, fill="white")
        self.ui.draw.line((12, 32, self.screen_w - 12, 32), fill="white")

        progress = f"{ROOT_ID}-{index}/{total}"
        pw, _ = self.ui.get_text_size(progress, self.ui.font_s)
        self.ui.draw.text((self.screen_w - pw - 8, 38), progress, font=self.ui.font_s, fill="gray")

        body = [
            f"Press: {label}",
            "",
            "Capture one key now.",
            "Menu key cancels.",
        ]

        y = 56
        line_h = self.ui.get_text_size("Ag", self.ui.font_s)[1] + 4
        for raw in body:
            lines = [""] if raw == "" else _wrap_text(self.ui, raw, self.screen_w - 16, self.ui.font_s)
            for line in lines:
                if y > self.content_bottom - line_h:
                    break
                self.ui.draw.text((8, y), line, font=self.ui.font_s, fill="white")
                y += line_h

        self.softkey.update("Capture", present=False)
        self.ui.fb.update(self.ui.canvas)

    def _capture_keymap(self):
        keymap_by_name = {}
        used_codes = set()

        total = len(KEY_TARGETS)
        for index, (name, label) in enumerate(KEY_TARGETS, start=1):
            while True:
                self._draw_capture_prompt(label, index, total)
                _flush_input(self.ui)
                key = self.ui.wait_for_key()

                if key == KEY_MENU:
                    MessageDialog(self.ui, "Calibration canceled. Keymap not saved.").show()
                    return None

                if key in used_codes:
                    MessageDialog(
                        self.ui,
                        f"Key code {key} is already mapped. Press a different key for {label}.",
                    ).show()
                    continue

                keymap_by_name[name] = {
                    "label": label,
                    "code": int(key),
                }
                used_codes.add(key)
                break

        return keymap_by_name

    def _save_keymap(self, keymap_by_name):
        payload = {
            "format": "neodct.keymap.v1",
            "generated_at_unix": int(time.time()),
            "output": OUTPUT_PATH,
            "keys": keymap_by_name,
            "by_code": {str(v["code"]): k for k, v in keymap_by_name.items()},
        }

        out_dir = os.path.dirname(OUTPUT_PATH)
        os.makedirs(out_dir, exist_ok=True)

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")

    def run(self):
        MessageDialog(
            self.ui,
            "This tool captures keypad presses and writes a JSON keymap to /NeoDCT/User/config/keymap.json.",
            title="Keypad Mapper",
        ).show()

        captured = self._capture_keymap()
        if not captured:
            return

        try:
            self._save_keymap(captured)
        except Exception as exc:
            MessageDialog(self.ui, f"Failed to write keymap: {exc}").show()
            return

        MessageDialog(self.ui, f"Keymap saved to\n{OUTPUT_PATH}").show()


def run(ui):
    if not _gpio_available():
        MessageDialog(ui, GPIO_REQUIRED_MSG).show()
        return

    app = KeypadMapper(ui)
    app.run()
