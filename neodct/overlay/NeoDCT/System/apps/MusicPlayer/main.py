"""
NeoDCT Music Player v3 (The "NeoPod" - Split Layout)
Updates:
- Removed conflicting audio flags for better stability
- New Layout: Art Left, Info Right
"""

import os
import time
import subprocess
import signal
import io
from PIL import Image, ImageFile
from System.ui.framework import VerticalList, SoftKeyBar

# 1. Be tolerant of bad MP3 art
ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    print("[Music] 'mutagen' library not found. Metadata/Art disabled.")

MUSIC_DIR = "/NeoDCT/User/music"

# --- SIMPLIFIED COMMAND ---
# Removed explicit audio formatting flags that were causing crashes.
# Kept 'nice' and 'buffer' for performance.
MPV_CMD = [
    "nice", "-n", "-10",
    "mpv",
    "--no-video",
    "--audio-buffer=4",
    "--quiet"
]

class MusicPlayer:
    def __init__(self, ui):
        self.ui = ui
        self.softkey = SoftKeyBar(ui)
        self.playlist = [] 
        self.current_process = None
        self.is_paused = False
        
        if not os.path.exists(MUSIC_DIR):
            try: os.makedirs(MUSIC_DIR)
            except: pass

    def scan_music(self):
        self.playlist = []
        if os.path.exists(MUSIC_DIR):
            for root, dirs, files in os.walk(MUSIC_DIR):
                for f in sorted(files):
                    if f.lower().endswith((".mp3", ".wav", ".aac")):
                        full_path = os.path.join(root, f)
                        self.playlist.append(full_path)

    def get_metadata(self, filepath):
        meta = {
            "title": os.path.basename(filepath),
            "artist": "Unknown Artist",
            "album": "",
            "art": None,
            "length": 0
        }

        if not HAS_MUTAGEN:
            return meta

        try:
            audio = MP3(filepath, ID3=ID3)
            
            if audio.tags:
                if "TIT2" in audio.tags: meta["title"] = str(audio.tags["TIT2"])
                if "TPE1" in audio.tags: meta["artist"] = str(audio.tags["TPE1"])
                if "TALB" in audio.tags: meta["album"] = str(audio.tags["TALB"])
                
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        img_data = tag.data
                        try:
                            meta["art"] = Image.open(io.BytesIO(img_data))
                        except Exception:
                            meta["art"] = None
                        break
            
            meta["length"] = audio.info.length
        except Exception as e:
            print(f"[Music] Metadata error: {e}")

        return meta

    def format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def play_file(self, full_path):
        self.stop() 

        try:
            cmd = MPV_CMD + [full_path]
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_paused = False
            return True
        except Exception as e:
            print(f"[Music] Error launching mpv: {e}")
            return False

    def stop(self):
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=0.2)
            except:
                try: self.current_process.kill() 
                except: pass
            self.current_process = None
            self.is_paused = False

    def toggle_pause(self):
        if not self.current_process: return

        # mpv can exit between our poll and this signal (track just ended);
        # signalling a dead pid raises ProcessLookupError and crashes the app.
        try:
            if self.is_paused:
                os.kill(self.current_process.pid, signal.SIGCONT)
                self.is_paused = False
            else:
                os.kill(self.current_process.pid, signal.SIGSTOP)
                self.is_paused = True
        except (ProcessLookupError, OSError):
            self.is_paused = False

    def run_now_playing(self, filepath):
        screen_w = getattr(self.ui, "W", 240)
        screen_h = getattr(self.ui, "H", 175)
        softkey_h = getattr(self.ui, "SOFTKEY_H", 30)
        content_bottom = getattr(self.ui, "content_bottom", screen_h - softkey_h)
        header_h = max(24, int(screen_h * 0.08))

        # 1. Load Data
        self.ui.draw.rectangle((0, 0, screen_w, screen_h), fill="black")
        lw, lh = self.ui.get_text_size("Loading...", self.ui.font_n)
        self.ui.draw.text(((screen_w - lw) // 2, max(10, (content_bottom - lh) // 2)), "Loading...", font=self.ui.font_n, fill="white")
        self.ui.fb.update(self.ui.canvas)
        
        meta = self.get_metadata(filepath)
        
        # 2. Resize Art (Smaller now, for side layout)
        display_art = None
        art_size = min(100, max(64, int(screen_w * 0.42)))
        
        if meta["art"]:
            try:
                meta["art"].draft("RGB", (art_size * 2, art_size * 2))
                meta["art"].load()
                display_art = meta["art"].resize((art_size, art_size), Image.Resampling.NEAREST)
            except Exception:
                display_art = None
        
        start_time = time.time()
        paused_at = 0
        total_paused_duration = 0
        
        # --- NEW LAYOUT CONSTANTS ---
        art_x = 8
        art_y = header_h + 12
        text_x = art_x + art_size + 8
        text_width = max(30, screen_w - text_x - 8)
        bar_width = max(48, screen_w - 20)
        bar_x = (screen_w - bar_width) // 2
        bar_y = content_bottom - 18

        # Keep art fully above progress/timestamps.
        available_media_h = max(48, bar_y - art_y - 18)
        art_size = min(art_size, available_media_h)

        if display_art and display_art.size != (art_size, art_size):
            display_art = display_art.resize((art_size, art_size), Image.Resampling.NEAREST)

        needs_redraw = True

        while True:
            # Check Status
            if self.current_process.poll() is not None:
                self.stop()
                return

            # Calc Time
            now = time.time()
            if self.is_paused:
                if paused_at == 0: paused_at = now
                current_elapsed = paused_at - start_time - total_paused_duration
            else:
                if paused_at != 0:
                    total_paused_duration += (now - paused_at)
                    paused_at = 0
                current_elapsed = now - start_time - total_paused_duration

            # DRAW
            if needs_redraw:
                # Clear Content Area
                self.ui.draw.rectangle((0, 0, screen_w, content_bottom), fill="black")

                # -- Header --
                self.ui.draw.rectangle((0, 0, screen_w, header_h), fill="white")
                w, h = self.ui.get_text_size("Now Playing", self.ui.font_s)
                self.ui.draw.text(((screen_w - w) // 2, max(2, (header_h - h) // 2)), "Now Playing", font=self.ui.font_s, fill="black")

                # -- Album Art (Left) --
                if display_art:
                    self.ui.canvas.paste(display_art, (art_x, art_y))
                    self.ui.draw.rectangle((art_x - 1, art_y - 1, art_x + art_size, art_y + art_size), outline="white")
                else:
                    self.ui.draw.rectangle((art_x, art_y, art_x + art_size, art_y + art_size), outline="white")
                    # Note Icon
                    cx, cy = art_x + (art_size // 2), art_y + (art_size // 2)
                    self.ui.draw.ellipse((cx - 8, cy + 8, cx + 1, cy + 17), fill="white")
                    self.ui.draw.line((cx + 1, cy + 12, cx + 1, cy - 12), fill="white", width=2)
                    self.ui.draw.line((cx + 1, cy - 12, cx + 14, cy - 8), fill="white", width=2)

                # -- Info (Right) --
                # Helper to truncate text to fit right column
                def truncate(text, font, max_w):
                    t = text
                    w, _ = self.ui.get_text_size(t, font)
                    while w > max_w and len(t) > 0:
                        t = t[:-1]
                        w, _ = self.ui.get_text_size(t + "...", font)
                    return t + "..." if len(t) < len(text) else t

                # Title (Bold)
                t_str = truncate(meta["title"], self.ui.font_n, text_width)
                self.ui.draw.text((text_x, art_y), t_str, font=self.ui.font_n, fill="white")
                
                # Artist (Regular)
                a_str = truncate(meta["artist"], self.ui.font_s, text_width)
                self.ui.draw.text((text_x, art_y + 25), a_str, font=self.ui.font_s, fill="#cccccc")
                
                # Album (Regular, below Artist)
                if meta["album"]:
                    al_str = truncate(meta["album"], self.ui.font_s, text_width)
                    self.ui.draw.text((text_x, art_y + 45), al_str, font=self.ui.font_s, fill="#999999")

                # -- Progress Bar (Bottom) --
                self.ui.draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + 4), fill="#333333")
                
                if meta["length"] > 0:
                    pct = min(1.0, current_elapsed / meta["length"])
                else:
                    pct = 0
                    
                fill_width = int(bar_width * pct)
                self.ui.draw.rectangle((bar_x, bar_y, bar_x + fill_width, bar_y + 4), fill="white")
                
                # Timestamps
                curr_str = self.format_time(int(current_elapsed))
                self.ui.draw.text((bar_x, bar_y - 15), curr_str, font=self.ui.font_s, fill="white")
                
                if meta["length"] > 0:
                    total_str = "-" + self.format_time(int(meta["length"] - current_elapsed))
                    w, h = self.ui.get_text_size(total_str, self.ui.font_s)
                    self.ui.draw.text((bar_x + bar_width - w, bar_y - 15), total_str, font=self.ui.font_s, fill="white")

                self.softkey.update("Pause" if not self.is_paused else "Play")
                needs_redraw = False

            # Input
            key = self.ui.read_keypress(1.0)
            if key is None:
                needs_redraw = True
                continue

            needs_redraw = True
            if key == 14: # STOP
                self.stop()
                return
            elif key == 28: # PAUSE
                self.toggle_pause()

    def run(self):
        while True:
            screen_w = getattr(self.ui, "W", 240)
            content_bottom = getattr(
                self.ui,
                "content_bottom",
                getattr(self.ui, "H", 175) - getattr(self.ui, "SOFTKEY_H", 30),
            )
            self.scan_music()
            if not self.playlist:
                self.ui.draw.rectangle((0, 0, screen_w, content_bottom), fill="black")
                y = max(12, int(content_bottom * 0.35))
                self.ui.draw.text((10, y), "No Music Found", font=self.ui.font_n, fill="white")
                self.ui.draw.text((10, y + 30), "Add mp3s to:", font=self.ui.font_s, fill="gray")
                self.ui.draw.text((10, y + 50), "/User/music", font=self.ui.font_s, fill="gray")
                self.softkey.update("Exit")
                while True:
                    k = self.ui.wait_for_key()
                    if k in (14, 28): return

            display_list = [os.path.basename(p) for p in self.playlist]
            vlist = VerticalList(self.ui, "Music", display_list, app_id=4)
            sel = vlist.show()
            if sel == -1: return

            full_path = self.playlist[sel]
            if self.play_file(full_path):
                self.run_now_playing(full_path)

def run(ui):
    app = MusicPlayer(ui)
    app.run()
