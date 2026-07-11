"""Calculator -- Nokia 5110-style two-operand calculator.

Flow (matches the design mockups):
  1. Entry screen: blinking cursor, type the first number.
     Softkeys: Options (Enter) / Exit (Backspace on empty input).
  2. Options: full-screen vertical menu (Add/Subtract/Multiply/Divide,
     plus Equals once an operation is pending). Block cursor marks the
     selected row. Softkeys: OK (Enter) / Back (Backspace).
  3. After Equals the equation disappears and only the right-justified
     answer remains. Softkeys: Options / Clear. Picking another
     operation chains from the result; typing a digit starts fresh.
"""

import time

KEY_ENTER = 28
KEY_BACK = 14
KEY_UP = 103
KEY_DOWN = 108

DIGITS = {2: "1", 3: "2", 4: "3", 5: "4", 6: "5",
          7: "6", 8: "7", 9: "8", 10: "9", 11: "0"}
KEYS_POINT = (42, 52)   # '*' on the keypad, '.' on a dev keyboard
KEYS_SIGN = (43, 12)    # '#' on the keypad, '-' on a dev keyboard

OPS = [("Add", "+"), ("Subtract", "-"), ("Multiply", "x"), ("Divide", "/")]

MAX_DIGITS = 12


def _calc(a, op, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "x":
        return a * b
    if op == "/":
        if b == 0:
            return None
        return a / b
    return None


def _fmt(value):
    """Format a result the way a pocket calculator would."""
    if value is None or value != value or value in (float("inf"), float("-inf")):
        return "Error"
    if abs(value) >= 10 ** MAX_DIGITS:
        return "Error"
    if float(value).is_integer():
        return str(int(value))
    text = f"{value:.8f}".rstrip("0").rstrip(".")
    return text[:MAX_DIGITS + 1]


class Calculator:
    def __init__(self, ui):
        self.ui = ui
        self.w = getattr(ui, "W", 240)
        self.h = getattr(ui, "H", 175)
        self.softkey_h = getattr(ui, "SOFTKEY_H", 30)
        self.content_bottom = getattr(ui, "content_bottom", self.h - self.softkey_h)

        self.first = ""        # committed left operand (display string)
        self.op = None         # pending op symbol, e.g. "+"
        self.buf = ""          # number currently being typed
        self.result_mode = False

    # ---- drawing --------------------------------------------------------

    def _frame(self, left_label, right_label):
        """Black screen, outer border, softkey separator + two labels."""
        d = self.ui.draw
        d.rectangle((0, 0, self.w, self.h), fill="black")
        d.rectangle((1, 1, self.w - 2, self.h - 2), outline="white")
        d.line((1, self.content_bottom, self.w - 2, self.content_bottom), fill="white")

        font = self.ui.font_n
        y = self.content_bottom + max(2, (self.softkey_h - 22) // 2)
        if left_label:
            d.text((12, y), left_label, font=font, fill="white")
        if right_label:
            tw = self.ui.get_text_size(right_label, font)[0]
            d.text((self.w - 12 - tw, y), right_label, font=font, fill="white")

    def _draw_entry(self, cursor_on):
        self._frame("Options", "Exit" if not self.op else "Clear")
        d = self.ui.draw
        font = self.ui.font_xl
        x, y, line_h = 14, 46, 32

        if self.op:
            # equation building: first operand + op on line 1, entry below
            d.text((x, y - line_h), f"{self.first}{self.op}", font=font, fill="white")
        d.text((x, y), self.buf + ("_" if cursor_on else ""), font=font, fill="white")
        self.ui.fb.update(self.ui.canvas)

    def _draw_result(self, text):
        self._frame("Options", "Clear")
        font = self.ui.font_xl
        tw = self.ui.get_text_size(text, font)[0]
        self.ui.draw.text((self.w - 14 - tw, 62), text, font=font, fill="white")
        self.ui.fb.update(self.ui.canvas)

    def _draw_menu(self, items, sel, window):
        self._frame("OK", "Back")
        d = self.ui.draw
        font = self.ui.font_n
        x, y0, line_h = 14, 10, 30
        visible = 4

        for row, idx in enumerate(range(window, min(window + visible, len(items)))):
            y = y0 + row * line_h
            d.text((x, y), items[idx], font=font, fill="white")
            if idx == sel:
                d.rectangle((self.w - 26, y + 2, self.w - 14, y + 18), fill="white")
        self.ui.fb.update(self.ui.canvas)

    # ---- screens --------------------------------------------------------

    def _options_menu(self):
        """Full-screen op menu. Returns an op symbol, '=' or None (back)."""
        items = [name for name, _ in OPS]
        symbols = [sym for _, sym in OPS]
        if self.op and self.buf:
            items.insert(0, "Equals")
            symbols.insert(0, "=")

        sel, window = 0, 0
        visible = 4
        self._draw_menu(items, sel, window)
        while True:
            key = self.ui.wait_for_key()
            if key == KEY_DOWN and sel < len(items) - 1:
                sel += 1
                if sel >= window + visible:
                    window += 1
                self._draw_menu(items, sel, window)
            elif key == KEY_UP and sel > 0:
                sel -= 1
                if sel < window:
                    window -= 1
                self._draw_menu(items, sel, window)
            elif key == KEY_ENTER:
                return symbols[sel]
            elif key == KEY_BACK:
                return None

    def _apply_equals(self):
        """Compute first <op> buf and switch to result mode."""
        try:
            result = _calc(float(self.first), self.op, float(self.buf))
        except ValueError:
            result = None
        text = _fmt(result)
        self.first = "" if text == "Error" else text
        self.op = None
        self.buf = ""
        self.result_mode = True
        return text

    def run(self):
        cursor_on = True
        last_blink = time.monotonic()
        result_text = None
        self._draw_entry(cursor_on)

        while True:
            # ---- result screen: static, no cursor ----
            if self.result_mode:
                key = self.ui.wait_for_key()
                if key == KEY_BACK:                       # Clear
                    self.first, self.op, self.buf = "", None, ""
                    self.result_mode = False
                    self._draw_entry(cursor_on)
                elif key == KEY_ENTER:                    # Options: chain
                    if self.first:                        # not after Error
                        choice = self._options_menu()
                        if choice and choice != "=":
                            self.op = choice
                            self.buf = ""
                            self.result_mode = False
                            self._draw_entry(cursor_on)
                            continue
                    self._draw_result(result_text or _fmt(None))
                elif key in DIGITS:                       # start fresh calc
                    self.first, self.op = "", None
                    self.buf = DIGITS[key]
                    self.result_mode = False
                    self._draw_entry(cursor_on)
                continue

            # ---- entry screens (first or second operand) ----
            key = self.ui.read_keypress(0.1)
            now = time.monotonic()
            if now - last_blink >= 0.5:
                cursor_on = not cursor_on
                last_blink = now
                self._draw_entry(cursor_on)
            if key is None:
                continue

            if key in DIGITS and len(self.buf) < MAX_DIGITS:
                self.buf += DIGITS[key]
            elif key in KEYS_POINT and "." not in self.buf:
                self.buf = (self.buf or "0") + "."
            elif key in KEYS_SIGN:
                self.buf = self.buf[1:] if self.buf.startswith("-") else "-" + self.buf
            elif key == KEY_BACK:
                if self.buf:
                    self.buf = self.buf[:-1]
                elif self.op:
                    # clear the pending operation, back to editing first
                    self.buf, self.first, self.op = self.first, "", None
                else:
                    return                                # Exit
            elif key == KEY_ENTER:
                choice = self._options_menu()
                if choice == "=":
                    result_text = self._apply_equals()
                    self._draw_result(result_text)
                    continue
                if choice:
                    if self.op and self.buf:
                        # chained op: fold the pending pair first
                        result_text = self._apply_equals()
                        if not self.first:                # Error
                            self._draw_result(result_text)
                            continue
                        self.result_mode = False
                    elif self.buf:
                        self.first = self.buf
                    self.op = choice if self.first else None
                    self.buf = ""
            self._draw_entry(cursor_on)


def run(ui):
    Calculator(ui).run()
