"""Tests for System.hw.t9_uinput -- the LinuxShell keypad->console bridge.

UInputKeyboard is tested through an injected pipe fd (no /dev/uinput or
root on the host): we read back the packed input_event structs it writes.
The bridge is tested against a recording fake keyboard.
"""

import os
import struct
import time

from System.hw import t9_uinput as tu

# NeoDCT evdev codes coming off the keypad
K2, K3 = 3, 4
STAR, HASH = 42, 43
ENTER, BACKSPACE, UP = 28, 14, 103

EV_SYN, EV_KEY = 0x00, 0x01
KEY_A, KEY_2, KEY_3, KEY_8, KEY_SLASH = 30, 3, 4, 9, 53
KEY_Z, KEY_SPACE, KEY_LEFTSHIFT = 44, 57, 42

_EVT = struct.Struct("llHHi")


# --- char -> keycode mapping ---

def test_char_to_keypress_lowercase():
    assert tu.char_to_keypress("a") == (KEY_A, False)


def test_char_to_keypress_uppercase_needs_shift():
    assert tu.char_to_keypress("Z") == (KEY_Z, True)


def test_char_to_keypress_digit():
    assert tu.char_to_keypress("2") == (KEY_2, False)


def test_char_to_keypress_symbols():
    assert tu.char_to_keypress("/") == (KEY_SLASH, False)
    assert tu.char_to_keypress("#") == (KEY_3, True)   # shift+3 on US layout
    assert tu.char_to_keypress("*") == (KEY_8, True)   # shift+8
    assert tu.char_to_keypress(" ") == (KEY_SPACE, False)


def test_char_to_keypress_unknown_is_none():
    assert tu.char_to_keypress("\x07") is None


# --- UInputKeyboard event emission ---

def make_kb():
    r, w = os.pipe()
    return tu.UInputKeyboard(fd=w), r


def read_events(r):
    """Drain (type, code, value) tuples from the pipe."""
    os.set_blocking(r, False)
    out = []
    try:
        while True:
            data = os.read(r, _EVT.size)
            if len(data) < _EVT.size:
                break
            _, _, etype, code, value = _EVT.unpack(data)
            out.append((etype, code, value))
    except BlockingIOError:
        pass
    return out


def key_events_only(events):
    return [e for e in events if e[0] == EV_KEY]


def test_type_char_press_release_with_syn():
    kb, r = make_kb()
    assert kb.type_char("a") is True
    events = read_events(r)
    assert (EV_KEY, KEY_A, 1) in events
    assert (EV_KEY, KEY_A, 0) in events
    assert events.index((EV_KEY, KEY_A, 1)) < events.index((EV_KEY, KEY_A, 0))
    # every key event is followed by a SYN report
    for i, ev in enumerate(events):
        if ev[0] == EV_KEY:
            assert events[i + 1] == (EV_SYN, 0, 0)


def test_type_char_shifted_wraps_in_shift():
    kb, r = make_kb()
    kb.type_char("A")
    keys = key_events_only(read_events(r))
    assert keys == [
        (EV_KEY, KEY_LEFTSHIFT, 1),
        (EV_KEY, KEY_A, 1),
        (EV_KEY, KEY_A, 0),
        (EV_KEY, KEY_LEFTSHIFT, 0),
    ]


def test_type_char_unknown_emits_nothing():
    kb, r = make_kb()
    assert kb.type_char("\x07") is False
    assert read_events(r) == []


def test_backspace_and_send_key():
    kb, r = make_kb()
    kb.backspace()
    kb.send_key(ENTER)
    keys = key_events_only(read_events(r))
    assert keys == [
        (EV_KEY, BACKSPACE, 1), (EV_KEY, BACKSPACE, 0),
        (EV_KEY, ENTER, 1), (EV_KEY, ENTER, 0),
    ]


# --- T9ShellBridge ---

class FakeKeyboard:
    def __init__(self):
        self.calls = []
        self.closed = False

    def type_char(self, ch):
        self.calls.append(("char", ch))
        return True

    def backspace(self):
        self.calls.append(("backspace",))

    def send_key(self, code, shift=False):
        self.calls.append(("key", code))

    def close(self):
        self.closed = True


def make_bridge():
    kb = FakeKeyboard()
    bridge = tu.T9ShellBridge(read_key=lambda timeout: None, keyboard=kb)
    return bridge, kb


def test_bridge_types_multitap_letter():
    bridge, kb = make_bridge()
    bridge.handle_code(K2)
    assert kb.calls == [("char", "a")]


def test_bridge_cycling_backspaces_then_retypes():
    bridge, kb = make_bridge()
    bridge.handle_code(K2)
    bridge.handle_code(K2)
    assert kb.calls == [("char", "a"), ("backspace",), ("char", "b")]


def test_bridge_enter_passthrough_commits_cycle():
    bridge, kb = make_bridge()
    bridge.handle_code(K2)
    bridge.handle_code(ENTER)
    bridge.handle_code(K2)
    assert kb.calls == [("char", "a"), ("key", ENTER), ("char", "a")]


def test_bridge_backspace_passthrough_resets_engine():
    bridge, kb = make_bridge()
    bridge.handle_code(K2)
    bridge.handle_code(BACKSPACE)
    bridge.handle_code(K2)
    assert kb.calls == [("char", "a"), ("key", BACKSPACE), ("char", "a")]


def test_bridge_arrows_passthrough():
    bridge, kb = make_bridge()
    bridge.handle_code(UP)
    assert kb.calls == [("key", UP)]


def test_bridge_hash_switches_mode_silently():
    bridge, kb = make_bridge()
    bridge.handle_code(HASH)
    assert kb.calls == []
    bridge.handle_code(K2)
    assert kb.calls == [("char", "A")]


def test_bridge_start_stop_lifecycle():
    script = [K2, K3, None]
    kb = FakeKeyboard()

    def read_key(timeout):
        if script:
            code = script.pop(0)
            return code
        time.sleep(0.01)
        return None

    bridge = tu.T9ShellBridge(read_key=read_key, keyboard=kb)
    bridge.start()
    deadline = time.time() + 2.0
    while len(kb.calls) < 2 and time.time() < deadline:
        time.sleep(0.01)
    bridge.stop()
    assert kb.calls[:2] == [("char", "a"), ("char", "d")]
    assert kb.closed  # stop() releases the virtual keyboard
    assert bridge._thread is None


# --- start_shell_bridge ---

class FakeMatrixInput:
    def read_key(self, timeout):
        time.sleep(min(timeout, 0.01))
        return None


class FakeUI:
    def __init__(self, matrix):
        self.matrix_input = matrix


def test_start_shell_bridge_without_keypad_returns_none():
    made = []
    result = tu.start_shell_bridge(FakeUI(None),
                                   keyboard_factory=lambda: made.append(1))
    assert result is None
    assert made == []  # no uinput device created in QEMU/dev


def test_start_shell_bridge_with_keypad_starts_bridge():
    kb = FakeKeyboard()
    bridge = tu.start_shell_bridge(FakeUI(FakeMatrixInput()),
                                   keyboard_factory=lambda: kb)
    try:
        assert bridge is not None
        assert bridge._thread is not None and bridge._thread.is_alive()
    finally:
        bridge.stop()


def test_start_shell_bridge_keyboard_failure_returns_none():
    def boom():
        raise OSError("no /dev/uinput")

    assert tu.start_shell_bridge(FakeUI(FakeMatrixInput()),
                                 keyboard_factory=boom) is None
