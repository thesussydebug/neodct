"""Tests for T9 integration in System.ui.framework text widgets.

T9 multi-tap is active only when ui.matrix_input (the i2c keypad) exists;
with a dev keyboard (QEMU) the existing QWERTY DEV_KEYMAP path is used,
now restricted by the widget's input_filter.

No drawing happens in handle_key, so a minimal FakeUI suffices (host
python has no PIL).
"""

from System.ui.framework import TextInput, TextInputLong

# NeoDCT evdev codes
K2, K3, K0 = 3, 4, 11
STAR, HASH = 42, 43
ENTER, BACKSPACE = 28, 14
KEY_A_QWERTY = 30  # 'a' on the dev keyboard
KEY_5_QWERTY = 6   # '5' on the dev keyboard


class FakeUI:
    def __init__(self, keypad=True):
        self.matrix_input = object() if keypad else None
        self.font_n = object()  # TextInputLong touches fonts in __init__


# --- TextInput, i2c keypad (T9) path ---

def test_t9_press_appends_letter():
    ti = TextInput(FakeUI(), "Add Entry", "Name:")
    assert ti.handle_key(K2) == "typed"
    assert ti.text == "a"


def test_t9_same_key_cycles_in_place():
    ti = TextInput(FakeUI(), "Add Entry", "Name:")
    ti.handle_key(K2)
    ti.handle_key(K2)
    assert ti.text == "b"      # replaced, not appended


def test_t9_different_keys_append():
    ti = TextInput(FakeUI(), "Add Entry", "Name:")
    ti.handle_key(K2)
    ti.handle_key(K3)
    assert ti.text == "ad"


def test_t9_hash_changes_mode_and_reports_it():
    ti = TextInput(FakeUI(), "Add Entry", "Name:")
    assert ti.t9.mode == "abc"
    assert ti.handle_key(HASH) == "mode"
    assert ti.t9.mode == "ABC"
    ti.handle_key(K2)
    assert ti.text == "A"


def test_t9_backspace_deletes_and_resets_cycle():
    ti = TextInput(FakeUI(), "Add Entry", "Name:")
    ti.handle_key(K2)
    ti.handle_key(K2)          # "b"
    assert ti.handle_key(BACKSPACE) == "backspace"
    assert ti.text == ""
    ti.handle_key(K2)
    assert ti.text == "a"      # fresh cycle, not "c"


def test_backspace_on_empty_cancels():
    ti = TextInput(FakeUI(), "Add Entry", "Name:")
    assert ti.handle_key(BACKSPACE) == "cancel"


def test_enter_confirms():
    ti = TextInput(FakeUI(), "Add Entry", "Name:", initial_text="hi")
    assert ti.handle_key(ENTER) == "confirm"
    assert ti.text == "hi"


def test_numbers_filter_types_digits_directly():
    ti = TextInput(FakeUI(), "Add Entry", "Number:", input_filter="numbers")
    ti.handle_key(K2)
    ti.handle_key(K2)
    assert ti.text == "22"     # literal, no multi-tap
    assert ti.t9.mode == "123"


def test_numbers_filter_star_hash_literal():
    ti = TextInput(FakeUI(), "Add Entry", "Number:", input_filter="numbers")
    ti.handle_key(STAR)
    ti.handle_key(HASH)
    assert ti.text == "*#"


def test_letters_filter_never_types_digits():
    ti = TextInput(FakeUI(), "Add Entry", "Name:", input_filter="letters")
    for _ in range(8):         # cycle far past a,b,c
        ti.handle_key(K2)
    assert ti.text in ("a", "b", "c")


# --- TextInput, dev keyboard (QWERTY) path ---

def test_dev_keyboard_still_types():
    ti = TextInput(FakeUI(keypad=False), "Add Entry", "Name:")
    assert ti.handle_key(KEY_A_QWERTY) == "typed"
    assert ti.text == "A"      # legacy first-letter auto-caps


def test_dev_keyboard_numbers_filter_rejects_letters():
    ti = TextInput(FakeUI(keypad=False), "Add Entry", "Number:",
                   input_filter="numbers")
    assert ti.handle_key(KEY_A_QWERTY) is None
    assert ti.text == ""
    ti.handle_key(KEY_5_QWERTY)
    assert ti.text == "5"


def test_dev_keyboard_letters_filter_rejects_digits():
    ti = TextInput(FakeUI(keypad=False), "Add Entry", "Name:",
                   input_filter="letters")
    assert ti.handle_key(KEY_5_QWERTY) is None
    assert ti.text == ""


# --- TextInputLong ---

def test_long_t9_types_and_cycles():
    til = TextInputLong(FakeUI(), "Write")
    assert til.handle_key(K2) == "typed"
    til.handle_key(K2)
    assert til.get_text() == "b"
    assert til.cursor == 1


def test_long_t9_multi_letter_word():
    til = TextInputLong(FakeUI(), "Write")
    til.handle_key(K2)         # a
    til.handle_key(K3)         # d
    til.handle_key(K3)         # -> e
    til.handle_key(K0)         # space
    assert til.get_text() == "ae "
    assert til.cursor == 3


def test_long_t9_mode_switch():
    til = TextInputLong(FakeUI(), "Write")
    assert til.handle_key(HASH) == "mode"
    assert til.t9.mode == "ABC"


def test_long_t9_backspace_resets_cycle():
    til = TextInputLong(FakeUI(), "Write")
    til.handle_key(K2)
    til.handle_key(BACKSPACE)
    til.handle_key(K2)
    assert til.get_text() == "a"


def test_long_empty_backspace_callback_still_works():
    fired = []
    til = TextInputLong(FakeUI(), "Write",
                        on_empty_backspace=lambda: fired.append(1))
    assert til.handle_key(BACKSPACE) == "empty_backspace"
    assert fired == [1]


def test_long_dev_keyboard_unchanged():
    til = TextInputLong(FakeUI(keypad=False), "Write")
    til.handle_key(KEY_A_QWERTY)
    assert til.get_text() == "A"
