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

# Unlike the rest of the suite these tests do render, so they need PIL.
pytest.importorskip("PIL")

from PIL import Image

TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"
)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from uistub import (
    CapturingFramebuffer,
    KeyScript,
    PathRemap,
    ScriptExhausted,
    StubUI,
    run_app,
)


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


# --- StubUI: booting the real launcher headlessly ------------------------

def test_stub_ui_scans_the_shipped_app_manifests():
    with StubUI() as ui:
        names = [app["name"] for app in ui.apps]

    assert "Phone book" in names
    assert "Messages" in names
    assert "Games" in names


def test_stub_ui_sorts_apps_by_manifest_id():
    with StubUI() as ui:
        ids = [app["id"] for app in ui.apps]

    assert ids == sorted(ids)
    assert ids[0] == 1  # Phone book


def test_stub_ui_renders_a_240x175_home_frame():
    with StubUI() as ui:
        ui.update()

    assert len(ui.fb.frames) == 1
    assert ui.fb.frames[0].size == (240, 175)


def test_stub_ui_loads_the_shipped_pixel_font():
    with StubUI() as ui:
        # ImageFont.load_default() has no .size; truetype fonts do.
        assert getattr(ui.font_xl, "size", None) == 24


def test_stub_ui_applies_a_wallpaper_setting():
    with StubUI(wallpaper="Palestine.jpg") as ui:
        assert ui.wallpaper is not None
        assert ui.wallpaper.size == (240, 175)


def test_stub_ui_without_wallpaper_renders_a_black_home_background():
    with StubUI() as ui:
        assert ui.wallpaper is None


def test_engineering_apps_are_hidden_when_engineering_mode_is_off():
    with StubUI(engineering=False) as ui:
        names = [app["name"] for app in ui.apps]

    assert "LCD Test" not in names


def test_scripted_keys_drive_the_app_selector_to_a_choice():
    from System.ui.framework import AppSelector

    with StubUI() as ui:
        ui.keys.push(108, 28)  # DOWN, then ENTER
        choice = AppSelector("Main Menu", ui.apps, ui).show()

    assert choice == 1


def test_app_selector_back_key_returns_minus_one():
    from System.ui.framework import AppSelector

    with StubUI() as ui:
        ui.keys.push(14)  # BACK
        choice = AppSelector("Main Menu", ui.apps, ui).show()

    assert choice == -1


def test_stub_ui_never_attaches_to_a_real_input_device():
    # Without this the runtime's evdev fallback grabs /dev/input/event0,
    # so on a host with input-group access the stub would race the
    # developer's own keyboard.
    with StubUI() as ui:
        assert ui.keypad_fd is None
        assert not str(ui.keypad_path).startswith("/dev/")


def test_stub_ui_writes_stay_out_of_the_repo_overlay():
    repo_overlay = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "overlay", "NeoDCT",
    )
    with StubUI() as ui:
        assert not ui.root.startswith(repo_overlay)
        assert os.path.exists(os.path.join(ui.root, "System", "apps"))


# --- run_app: driving shipped apps ---------------------------------------

def test_run_app_captures_frames_from_a_shipped_app():
    with StubUI() as ui:
        frames = run_app(ui, "Calculator", keys=[6, 4])  # types "5", then "3"

    assert frames
    assert frames[0].size == (240, 175)


def test_run_app_returns_when_the_key_script_runs_out():
    # Clock blocks in a wait_for_key loop forever; the harness must unwind
    # instead of hanging the caller.
    with StubUI() as ui:
        frames = run_app(ui, "Clock", keys=[])

    assert frames


def test_run_app_only_returns_frames_drawn_by_that_app():
    with StubUI() as ui:
        ui.update()  # one home-screen frame first
        frames = run_app(ui, "Clock", keys=[])

    assert len(frames) == len(ui.fb.frames) - 1


def test_run_app_rejects_an_unknown_app_name():
    with StubUI() as ui:
        with pytest.raises(KeyError):
            run_app(ui, "No Such App")


# --- simulated device status ---------------------------------------------

def test_simulate_status_presents_a_registered_device_with_a_battery():
    # Without a fuel gauge the home screen draws "?" instead of a battery,
    # and with no modem the carrier line stays "No Service". Doc shots want
    # a normal-looking device.
    with StubUI() as ui:
        ui.stub.simulate_status(battery=4, signal=3, carrier="Tello")

        assert ui.battery.hardware is True
        assert ui.battery.level() == 4
        assert ui.modem.signal_level() == 3
        assert ui.modem.operator_display() == "Tello"


def test_simulate_status_defaults_leave_no_carrier_name():
    with StubUI() as ui:
        ui.stub.simulate_status(battery=2, signal=0)

        assert ui.modem.operator_display() is None


# --- installing a third-party app ----------------------------------------

HELLO_MAIN = '''\
from System.ui.framework import SoftKeyBar

def run(ui):
    ui.draw.rectangle((0, 0, ui.W, ui.content_bottom), fill="black")
    ui.draw.text((10, 40), "Hello NeoDCT", font=ui.font_n, fill="white")
    SoftKeyBar(ui).update("Back")
    while ui.wait_for_key() != 14:
        pass
'''


def _write_example_app(directory):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "manifest.json"), "w") as f:
        f.write('{"name": "Hello World", "id": "42", '
                '"icon": "icon.png", "exec": "main.py"}')
    with open(os.path.join(directory, "main.py"), "w") as f:
        f.write(HELLO_MAIN)
    return directory


def test_install_app_makes_a_custom_app_appear_in_the_launcher(tmp_path):
    source = _write_example_app(str(tmp_path / "HelloWorld"))

    with StubUI() as ui:
        ui.stub.install_app(source)

        assert "Hello World" in [app["name"] for app in ui.apps]


def test_an_installed_app_runs_and_draws_through_the_real_contract(tmp_path):
    source = _write_example_app(str(tmp_path / "HelloWorld"))

    with StubUI() as ui:
        ui.stub.install_app(source)
        frames = run_app(ui, "Hello World", keys=[14])

    assert frames
    assert frames[-1].size == (240, 175)


def test_install_app_does_not_touch_the_repo_overlay(tmp_path):
    source = _write_example_app(str(tmp_path / "HelloWorld"))
    repo_apps = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "overlay", "NeoDCT", "System", "apps",
    )

    with StubUI() as ui:
        ui.stub.install_app(source)

    assert not os.path.exists(os.path.join(repo_apps, "HelloWorld"))


# --- unwinding apps that poll instead of blocking ------------------------

POLLING_MAIN = '''\
def run(ui):
    while True:
        ui.draw.rectangle((0, 0, ui.W, ui.content_bottom), fill="black")
        ui.draw.text((10, 40), "tick", font=ui.font_n, fill="white")
        ui.fb.update(ui.canvas)
        ui.read_keypress(0.01)   # never blocks, never returns
'''


def test_key_script_raises_once_the_idle_budget_is_spent():
    keys = KeyScript([], idle_budget=3)

    assert keys.pop(0.01) is None
    assert keys.pop(0.01) is None
    assert keys.pop(0.01) is None
    with pytest.raises(ScriptExhausted):
        keys.pop(0.01)


def test_idle_budget_resets_when_a_real_key_arrives():
    keys = KeyScript([], idle_budget=2)
    keys.pop(0.01)
    keys.push(28)

    assert keys.pop(0.01) == 28
    assert keys.pop(0.01) is None  # budget started over
    assert keys.pop(0.01) is None


def test_run_app_unwinds_a_game_loop_that_polls_forever(tmp_path):
    source = str(tmp_path / "Poller")
    os.makedirs(source, exist_ok=True)
    with open(os.path.join(source, "manifest.json"), "w") as f:
        f.write('{"name": "Poller", "id": "43", "exec": "main.py"}')
    with open(os.path.join(source, "main.py"), "w") as f:
        f.write(POLLING_MAIN)

    with StubUI(idle_budget=5) as ui:
        ui.stub.install_app(source)
        frames = run_app(ui, "Poller", keys=[])

    assert frames  # it drew, then the harness unwound it


# --- stopping real-time apps that never read the keypad ------------------

DRAWING_MAIN = '''\
def run(ui):
    while True:
        ui.draw.rectangle((0, 0, ui.W, ui.content_bottom), fill="black")
        ui.draw.text((10, 40), "frame", font=ui.font_n, fill="white")
        ui.fb.update(ui.canvas)   # no input call at all
'''


def test_frame_budget_stops_an_endless_draw_loop():
    fb = CapturingFramebuffer()
    frame = Image.new("RGB", (240, 175), "black")
    fb.set_budget(3)

    fb.update(frame)
    fb.update(frame)
    fb.update(frame)
    with pytest.raises(ScriptExhausted):
        fb.update(frame)


def test_clearing_the_frame_budget_allows_drawing_again():
    fb = CapturingFramebuffer()
    frame = Image.new("RGB", (240, 175), "black")
    fb.set_budget(1)
    fb.update(frame)
    fb.clear_budget()

    fb.update(frame)  # must not raise

    assert len(fb.frames) == 2


def test_run_app_stops_a_game_loop_that_never_reads_the_keypad(tmp_path):
    source = str(tmp_path / "Drawer")
    os.makedirs(source, exist_ok=True)
    with open(os.path.join(source, "manifest.json"), "w") as f:
        f.write('{"name": "Drawer", "id": "44", "exec": "main.py"}')
    with open(os.path.join(source, "main.py"), "w") as f:
        f.write(DRAWING_MAIN)

    with StubUI() as ui:
        ui.stub.install_app(source)
        frames = run_app(ui, "Drawer", keys=[], frame_budget=6)

    assert len(frames) == 6


def test_frame_budget_does_not_leak_into_later_screens(tmp_path):
    source = str(tmp_path / "Drawer")
    os.makedirs(source, exist_ok=True)
    with open(os.path.join(source, "manifest.json"), "w") as f:
        f.write('{"name": "Drawer", "id": "44", "exec": "main.py"}')
    with open(os.path.join(source, "main.py"), "w") as f:
        f.write(DRAWING_MAIN)

    with StubUI() as ui:
        ui.stub.install_app(source)
        run_app(ui, "Drawer", keys=[], frame_budget=3)

        ui.update()  # home screen must still be drawable afterwards

    assert ui.fb.frames[-1].size == (240, 175)
