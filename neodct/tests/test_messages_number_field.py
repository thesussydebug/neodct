"""The Messages 'Send To' number field must be numbers-only: on the i2c
keypad digits type literally (no multi-tap letters) and star/hash work."""

import importlib.util
import os

import conftest

MESSAGES_MAIN = os.path.join(conftest.OVERLAY_NEODCT, "System", "apps",
                             "Messages", "main.py")

K2 = 3
STAR, HASH = 42, 43


def load_messages():
    spec = importlib.util.spec_from_file_location("messages_app", MESSAGES_MAIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeUI:
    def __init__(self):
        self.matrix_input = object()
        self.font_n = object()


def test_contact_number_input_is_numbers_only():
    app = load_messages()
    field = app.ContactNumberInput(FakeUI(), "Send To", "Number:")
    assert field.input_filter == "numbers"


def test_contact_number_input_types_digits_star_hash_on_keypad():
    app = load_messages()
    field = app.ContactNumberInput(FakeUI(), "Send To", "Number:")
    field.handle_key(K2)
    field.handle_key(K2)   # no multi-tap: two literal '2's
    field.handle_key(STAR)
    field.handle_key(HASH)
    assert field.text == "22*#"
