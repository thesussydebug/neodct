"""Tests for the LinuxShell app's T9 bridge wiring.

The app module is loaded by file path, the same way the NeoDCT launcher
does it (engineering apps are not packages).
"""

import importlib.util
import os
import sys
import time

import conftest

APP_MAIN = os.path.join(conftest.OVERLAY_NEODCT, "System", "engineering",
                        "apps", "LinuxShell", "main.py")


def load_app():
    spec = importlib.util.spec_from_file_location("linuxshell_app", APP_MAIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeMatrixInput:
    def read_key(self, timeout):
        time.sleep(min(timeout, 0.01))
        return None


class FakeUI:
    def __init__(self, matrix):
        self.matrix_input = matrix


def test_no_keypad_starts_no_bridge():
    app = load_app()
    assert app._start_t9_bridge(FakeUI(None)) is None


def test_uinput_failure_is_not_fatal(monkeypatch):
    # With a keypad but no usable /dev/uinput, the app must return None
    # instead of raising -- the shell works without T9. (Forced via
    # monkeypatch: some hosts actually allow uinput, and the test must
    # never create a real virtual keyboard.)
    app = load_app()

    import System.hw.t9_uinput as tu

    def boom():
        raise PermissionError("no /dev/uinput")

    monkeypatch.setattr(tu, "UInputKeyboard", boom)
    assert app._start_t9_bridge(FakeUI(FakeMatrixInput())) is None


def test_bridge_started_and_stoppable_with_working_uinput(monkeypatch):
    app = load_app()

    class FakeKeyboard:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    import System.hw.t9_uinput as tu
    kb = FakeKeyboard()
    monkeypatch.setattr(tu, "UInputKeyboard", lambda: kb)

    bridge = app._start_t9_bridge(FakeUI(FakeMatrixInput()))
    assert bridge is not None
    assert bridge._thread.is_alive()
    bridge.stop()
    assert kb.closed
