# The Browser app takes over input while netsurf runs; the launcher's
# keypad fd (and the i2c scanner's pending queue) keep accumulating
# presses meanwhile. Without draining them on exit, the UI replays the
# backlog and opens random menus.
import os
import select

from System.apps.Browser.main import _drain_input


class _FakeMatrix:
    def __init__(self, queued):
        self.queued = list(queued)

    def read_key(self, timeout):
        if self.queued:
            return self.queued.pop(0)
        return None


class _FakeUI:
    def __init__(self, keypad_fd=None, matrix_input=None):
        self.keypad_fd = keypad_fd
        self.matrix_input = matrix_input


def test_drain_flushes_keypad_fd():
    r, w = os.pipe()
    os.set_blocking(r, False)
    try:
        # three stale 24-byte input_event-sized records
        os.write(w, b"\x00" * 72)
        _drain_input(_FakeUI(keypad_fd=r))
        assert select.select([r], [], [], 0)[0] == []
    finally:
        os.close(r)
        os.close(w)


def test_drain_consumes_matrix_pending():
    matrix = _FakeMatrix([28, 108, 14])
    _drain_input(_FakeUI(matrix_input=matrix))
    assert matrix.queued == []


def test_drain_tolerates_missing_attrs():
    _drain_input(_FakeUI())          # no fd, no matrix
    _drain_input(object())           # ui without the attributes at all


def test_drain_tolerates_closed_fd():
    r, w = os.pipe()
    os.close(r)
    os.close(w)
    _drain_input(_FakeUI(keypad_fd=r))
