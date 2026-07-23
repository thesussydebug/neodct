# Tests for the headless UI stub (neodct/tools/uistub).
#
# The stub lets host tooling render real NeoDCT screens without a
# framebuffer, keypad, modem or /NeoDCT rootfs. It is what the
# documentation screenshots are generated from, so it must faithfully
# reproduce the device geometry: a 240x175 UI band centred on a
# 240x240 panel.
import os
import sys

import pytest

# PIL is not installed in the plain host python used by the rest of the
# suite; these tests only run where it is (the docs venv).
pytest.importorskip("PIL")

from PIL import Image

TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"
)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from uistub import CapturingFramebuffer, KeyScript, PathRemap, ScriptExhausted


# --- CapturingFramebuffer ------------------------------------------------

def test_framebuffer_captures_frame_independent_of_later_canvas_edits():
    fb = CapturingFramebuffer()
    canvas = Image.new("RGB", (240, 175), "black")

    fb.update(canvas)
    canvas.paste((255, 255, 255), (0, 0, 240, 175))

    assert len(fb.frames) == 1
    assert fb.frames[0].getpixel((0, 0)) == (0, 0, 0)


def test_device_frame_centres_ui_band_on_240x240_panel():
    fb = CapturingFramebuffer()
    fb.update(Image.new("RGB", (240, 175), "white"))

    panel = fb.device_frame(0)

    assert panel.size == (240, 240)
    assert panel.getpixel((120, 0)) == (0, 0, 0)      # letterbox above
    assert panel.getpixel((120, 120)) == (255, 255, 255)  # band centre
    assert panel.getpixel((120, 239)) == (0, 0, 0)    # letterbox below


def test_device_frame_band_starts_at_row_32():
    fb = CapturingFramebuffer()
    fb.update(Image.new("RGB", (240, 175), "white"))

    panel = fb.device_frame(0)

    assert panel.getpixel((120, 31)) == (0, 0, 0)
    assert panel.getpixel((120, 32)) == (255, 255, 255)


# --- PathRemap -----------------------------------------------------------

def test_remap_reads_neodct_absolute_path_from_staged_root(tmp_path):
    staged = tmp_path / "NeoDCT"
    (staged / "System").mkdir(parents=True)
    (staged / "System" / "hello.txt").write_text("hi")

    with PathRemap(staged):
        with open("/NeoDCT/System/hello.txt") as f:
            assert f.read() == "hi"


def test_remap_reports_existence_through_staged_root(tmp_path):
    staged = tmp_path / "NeoDCT"
    (staged / "User").mkdir(parents=True)

    with PathRemap(staged):
        assert os.path.exists("/NeoDCT/User")
        assert not os.path.exists("/NeoDCT/User/nope.db")


def test_remap_leaves_unrelated_paths_alone(tmp_path):
    other = tmp_path / "plain.txt"
    other.write_text("untouched")

    with PathRemap(tmp_path / "NeoDCT"):
        with open(other) as f:
            assert f.read() == "untouched"


def test_remap_restores_builtins_after_exit(tmp_path):
    import builtins

    original = builtins.open
    with PathRemap(tmp_path / "NeoDCT"):
        assert builtins.open is not original
    assert builtins.open is original


# --- KeyScript -----------------------------------------------------------

def test_key_script_returns_queued_codes_in_order():
    keys = KeyScript([28, 108, 14])

    assert keys.pop(0.1) == 28
    assert keys.pop(0.1) == 108
    assert keys.pop(0.1) == 14


def test_key_script_returns_none_when_drained_by_default():
    keys = KeyScript([28])
    keys.pop(0.1)

    assert keys.pop(0.1) is None


def test_key_script_raises_to_break_out_of_blocking_widget_loops():
    keys = KeyScript([28], on_exhausted="raise")
    keys.pop(0.1)

    with pytest.raises(ScriptExhausted):
        keys.pop(0.1)
