"""NotifyService -- Nokia-style home-screen notifications.

First consumer: incoming SMS. This is deliberately NOT a modal dialog
framework (battery warnings keep their own dedicated path): posting a
notification beeps immediately, and the *visual* part lives on the HOME
screen exactly like the 3310 --

    * "N message(s) received" banner mid-left (carrier line hidden),
    * softkey turns into "Read" (enter opens the message),
    * C/backspace dismisses the banner (messages stay unread in the
      inbox and the envelope keeps flashing until they're actually read),
    * a flashing envelope in the status strip while unread mail exists.

Inside apps nothing visual happens -- the banner is waiting when you get
back to HOME. main.py owns rendering and key handling; this service is
just the state + the beep.

The tone is played fire-and-forget through BusyBox aplay so nothing here
ever blocks the UI loop; if the ALSA device is busy (MusicPlayer/Koki)
the beep is skipped silently -- the banner still shows.
"""

import os
import subprocess

TONES_DIR = "/NeoDCT/System/tones"
SMS_TONE = os.path.join(TONES_DIR, "sms.wav")


class NotifyService:
    def __init__(self):
        print("[NOTIFY] Initializing NotifyService...")
        self._kind = None        # active banner kind ("sms") or None
        self._count = 0          # how many arrivals the banner covers
        self._latest_data = None  # e.g. newest inbox row id

    # --- posting -----------------------------------------------------------

    def post_sms(self, message_row_id, tone=True):
        """Register one received SMS: beep now, banner until dismissed."""
        self._kind = "sms"
        self._count += 1
        self._latest_data = message_row_id
        if tone:
            self.play_tone(SMS_TONE)

    # --- home-screen state ---------------------------------------------------

    def active(self):
        return self._kind is not None

    def kind(self):
        return self._kind

    def count(self):
        return self._count

    def latest_data(self):
        return self._latest_data

    def banner_lines(self):
        """Two text lines for the home screen, 3310-style."""
        if self._kind != "sms":
            return ()
        noun = "message" if self._count == 1 else "messages"
        return ("%d %s" % (self._count, noun), "received")

    def dismiss(self):
        """C pressed (or the messages were opened): clear the banner."""
        self._kind = None
        self._count = 0
        self._latest_data = None

    # --- audio ---------------------------------------------------------------

    def play_tone(self, path):
        """Fire-and-forget beep; never blocks, never raises."""
        try:
            if not os.path.exists(path):
                print(f"[NOTIFY] Tone missing: {path}")
                return False
            subprocess.Popen(
                ["aplay", "-q", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as exc:
            print(f"[NOTIFY] Tone playback unavailable: {exc}")
            return False
