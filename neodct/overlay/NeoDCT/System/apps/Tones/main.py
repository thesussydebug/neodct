import os
import time
import subprocess
import select

from System.ui.framework import SoftKeyBar, MessageDialog, PagedList, VerticalList
from System.core.SettingsStorage import set_setting

ROOT_ID = 9
SYSTEM_TONES_DIR = "/NeoDCT/System/tones"
USER_TONES_DIR = "/NeoDCT/User/tones"
SUPPORTED_EXTS = (".mp3")

MPV_CMD = [
    "nice", "-n", "-10",
    "mpv",
    "--no-video",
    "--audio-buffer=4",
    "--quiet"
]


class TonePreviewPlayer:
    def __init__(self):
        self.process = None

    def play(self, path):
        if not path:
            return
        self.stop()
        try:
            self.process = subprocess.Popen(
                MPV_CMD + [path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            print(f"[Tones] Failed to play {path}: {exc}")
            self.process = None

    def stop(self):
        if not self.process:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=0.2)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        self.process = None


def _flush_input(ui):
    fd = getattr(ui, "keypad_fd", None)
    if fd is None:
        return
    while True:
        r, _, _ = select.select([fd], [], [], 0.01)
        if not r:
            break
        try:
            os.read(fd, 24)
        except Exception:
            break


def _scan_tones():
    tones = []
    for base in (SYSTEM_TONES_DIR, USER_TONES_DIR):
        if not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            for filename in sorted(files):
                if filename.lower().endswith(SUPPORTED_EXTS):
                    full_path = os.path.join(root, filename)
                    display = os.path.splitext(os.path.basename(filename))[0]
                    tones.append({"name": display, "path": full_path})
    tones.sort(key=lambda item: item["name"].lower())
    return tones


def _show_ringing_options(ui):
    options = ["Ring", "Vibrate"]
    vlist = VerticalList(ui, "Ringing Options", options, app_id=ROOT_ID)
    softkey = SoftKeyBar(ui)
    softkey.update("Select", present=False)

    selection = vlist.show()
    if selection == -1:
        return
    MessageDialog(ui, "Option saved (no effect yet).").show()


def _show_ringing_tones(ui):
    try:
        os.makedirs(USER_TONES_DIR, exist_ok=True)
    except Exception:
        pass

    tones = _scan_tones()
    if not tones:
        MessageDialog(ui, "No ringtones found.").show()
        return

    names = [tone["name"] for tone in tones]
    vlist = VerticalList(ui, "Tones", names, app_id=ROOT_ID)
    softkey = SoftKeyBar(ui)
    player = TonePreviewPlayer()

    pending_index = None
    pending_time = 0.0

    def schedule_preview():
        nonlocal pending_index, pending_time
        pending_index = vlist.selected_index
        pending_time = time.time()
        player.stop()

    def redraw():
        softkey.update("Select", present=False)
        vlist.draw()

    _flush_input(ui)
    redraw()

    while True:
        if pending_index is not None and (time.time() - pending_time) >= 0.5:
            player.play(tones[pending_index]["path"])
            pending_index = None

        key = ui.read_keypress(0.05)
        if key is None:
            continue

        if key == 108:  # DOWN
            if vlist.selected_index < len(names) - 1:
                vlist.selected_index += 1
                if vlist.selected_index >= vlist.window_start + vlist.max_lines:
                    vlist.window_start += 1
                schedule_preview()
                redraw()

        elif key == 103:  # UP
            if vlist.selected_index > 0:
                vlist.selected_index -= 1
                if vlist.selected_index < vlist.window_start:
                    vlist.window_start -= 1
                schedule_preview()
                redraw()

        elif 2 <= key <= 10:  # Number shortcuts
            shortcut_idx = key - 2
            if shortcut_idx < len(names):
                vlist.selected_index = shortcut_idx
                if vlist.selected_index < vlist.window_start:
                    vlist.window_start = vlist.selected_index
                elif vlist.selected_index >= vlist.window_start + vlist.max_lines:
                    vlist.window_start = max(0, vlist.selected_index - vlist.max_lines + 1)
                schedule_preview()
                redraw()

        elif key in (28, 96):  # ENTER / center
            player.stop()
            set_setting("system.audio.ringtone", tones[vlist.selected_index]["path"])
            MessageDialog(ui, f"Ringtone set to {names[vlist.selected_index]}.").show()
            return

        elif key == 14:  # BACKSPACE
            player.stop()
            return

def run(ui):
    while True:
        menu = PagedList(
            ui,
            "Tones",
            ["Ringing Options", "Ringing Tones"],
            root_id=ROOT_ID,
        )
        selection = menu.show()
        if selection == -1:
            return
        if selection == 0:
            _show_ringing_options(ui)
        elif selection == 1:
            _show_ringing_tones(ui)
