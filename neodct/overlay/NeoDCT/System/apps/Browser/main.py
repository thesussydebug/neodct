# /NeoDCT/System/apps/Browser/main.py
#
# NetSurf framebuffer browser (netsurf-fb, NeoDCT chrome).
# Takes over /dev/fb0 and reads keys from evdev directly; on keypad
# hardware the presses are bridged to a uinput keyboard the same way
# LinuxShell does it. The launcher resumes drawing when we return.
import os
import subprocess


def _start_key_bridge(ui):
    """Keypad-only hardware: mirror i2c keypad presses into a uinput
    keyboard netsurf can read. Returns None on QEMU/dev where a real
    keyboard evdev device already exists."""
    try:
        from System.hw.t9_uinput import start_shell_bridge
        return start_shell_bridge(ui)
    except Exception:
        return None


HOME_PAGE = "file:///NeoDCT/System/apps/Browser/home.html"


def run(ui):
    browser = "/usr/bin/netsurf-fb"
    if not os.path.exists(browser):
        return

    bridge = _start_key_bridge(ui)

    env = os.environ.copy()
    env.setdefault("HOME", "/NeoDCT/User")

    try:
        subprocess.run(
            [browser, HOME_PAGE],
            env=env,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    finally:
        # Tear down the virtual keyboard before the UI resumes reading
        # the keypad, so nothing double-consumes presses.
        if bridge is not None:
            try:
                bridge.stop()
            except Exception:
                pass

        # Repaint the UI over whatever the browser left on the fb.
        try:
            ui.fb.update(ui.canvas)
        except Exception:
            pass
