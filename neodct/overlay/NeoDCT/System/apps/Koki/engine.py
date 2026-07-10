# Koki engine: a small Scratch-3-like runtime for NeoDCT.
#
# Design goals, in order:
#   1. Faithful: game logic is ported 1:1 from the decompiled sb3 as
#      cooperative generator "scripts" with Scratch broadcast semantics
#      (a broadcast RESTARTS a handler that is already running).
#   2. Fast on the Luckfox RV1103: all costumes are pre-scaled PNGs
#      (see tools/build_assets.py), so a frame is just a handful of
#      alpha pastes into a 240x175 canvas + one fb.update().
#
# Scratch stage is 480x360; NeoDCT UI is 240x175. Everything is uniform
# 0.5 scale with 2.5 stage-px cropped off the top and bottom.

import os
import random
import select
import shutil
import struct
import subprocess
import time
from collections import OrderedDict

from PIL import Image, ImageChops

STAGE_SCALE = 0.5
SCREEN_W = 240
SCREEN_H = 175
CENTER_X = SCREEN_W / 2.0
CENTER_Y = SCREEN_H / 2.0
FPS = 30
FRAME_DT = 1.0 / FPS

# alpha > 40 counts as solid for collision (Scratch-like)
ALPHA_THRESH_LUT = bytes(255 if v > 40 else 0 for v in range(256))

# evdev key codes -> logical game keys.
KEYMAP = {
    105: "left", 106: "right", 103: "up", 108: "down",
    44: "z", 45: "x", 28: "enter", 14: "back",
    # Phone keypad aliases (see MATRIX_NAME_TO_CODE in core/main.py):
    5: "left", 7: "right", 3: "up", 9: "down",   # num 4/6/2/8
    6: "z", 11: "x",                             # num 5 = jump, num 0 = action
    42: "z", 43: "x",                            # star = jump, hash = action
}


def _now():
    return time.monotonic()


# --------------------------------------------------------------------------
# Input: track HELD keys from the evdev stream (press + release), which the
# stock ui.read_keypress() cannot do (it only reports key-down).
# --------------------------------------------------------------------------
class Input:
    def __init__(self, ui):
        self.fd = getattr(ui, "keypad_fd", None)
        self.matrix = getattr(ui, "matrix_input", None)
        self.held = set()          # logical names currently held
        self.pressed = set()       # logical names newly pressed this frame
        self._matrix_code = None
        if self.matrix is not None:
            print("[Koki] matrix keypad detected: single-key input only "
                  "(no simultaneous move+jump).")

    def poll(self):
        self.pressed.clear()
        fd = self.fd
        if fd is not None:
            while True:
                try:
                    r, _, _ = select.select([fd], [], [], 0)
                except Exception:
                    break
                if not r:
                    break
                try:
                    data = os.read(fd, 24)
                except Exception:
                    break
                if len(data) == 24:
                    _, _, etype, code, val = struct.unpack("llHHI", data)
                elif len(data) == 16:
                    _, _, etype, code, val = struct.unpack("IIHHI", data)
                else:
                    continue
                if etype != 1:
                    continue
                name = KEYMAP.get(code)
                if name is None:
                    continue
                if val == 1:
                    if name not in self.held:
                        self.pressed.add(name)
                    self.held.add(name)
                elif val == 0:
                    self.held.discard(name)
                # val == 2 (autorepeat): already held, ignore

        # Matrix keypads report presses via read_key(); held state lives on
        # the backend: gpiozero MatrixKeypadInput keeps `_held` on itself,
        # pcf8575 I2CMatrixKeypadInput keeps it on its nested `scanner`.
        m = self.matrix
        if m is not None:
            try:
                code = m.read_key(0)
            except Exception:
                code = None
            if code is not None:
                name = KEYMAP.get(code)
                if name:
                    # the scanner reports ONE key at a time: a new press
                    # replaces the previous one, else it stays latched
                    # (walk right + press X used to drift right forever)
                    if self._matrix_code and self._matrix_code != name:
                        self.held.discard(self._matrix_code)
                    self.pressed.add(name)
                    self.held.add(name)
                    self._matrix_code = name
            if self._matrix_code is not None:
                holder = getattr(m, "scanner", m)
                if getattr(holder, "_held", None) is None:
                    self.held.discard(self._matrix_code)
                    self._matrix_code = None

    def key(self, name):
        return name in self.held

    def any_key(self):
        return bool(self.held)


# --------------------------------------------------------------------------
# Sound: music via a looping mpv child, sfx via short-lived mpv children.
# Degrades to log-only when audio is unavailable (kernel audio is WIP).
# --------------------------------------------------------------------------
class SoundManager:
    MAX_SFX = 3

    def __init__(self, base_dir):
        self.base = base_dir
        self.music_proc = None
        self.sfx_procs = []
        self.enabled = True
        self.reasons_logged = set()
        if os.environ.get("NEODCT_KOKI_NOSOUND"):
            self._disable("NEODCT_KOKI_NOSOUND set")
        elif shutil.which("mpv") is None:
            self._disable("mpv not found in PATH")
        elif not os.path.isdir("/dev/snd"):
            self._disable("/dev/snd missing (no ALSA device; kernel audio "
                          "not implemented yet?)")

    def _disable(self, reason):
        if reason not in self.reasons_logged:
            self.reasons_logged.add(reason)
            print(f"[Koki] SOUND DISABLED: {reason} -- game continues silent")
        self.enabled = False

    def _spawn(self, path, loop=False):
        cmd = ["mpv", "--no-video", "--really-quiet", "--no-terminal"]
        if loop:
            cmd.append("--loop=inf")
        cmd.append(path)
        try:
            return subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._disable(f"mpv spawn failed: {e}")
            return None

    def music(self, rel):
        """Play a track on repeat (replaces current music)."""
        self.stop_music()
        if not self.enabled:
            return
        self.music_proc = self._spawn(os.path.join(self.base, rel), loop=True)

    def stop_music(self):
        p = self.music_proc
        self.music_proc = None
        if p is not None:
            try:
                p.kill()
                p.wait()
            except Exception:
                pass

    def sfx(self, rel):
        if not self.enabled:
            return
        self.sfx_procs = [p for p in self.sfx_procs if p.poll() is None]
        if len(self.sfx_procs) >= self.MAX_SFX:
            return
        p = self._spawn(os.path.join(self.base, rel))
        if p is not None:
            self.sfx_procs.append(p)

    def stop_all(self):
        self.stop_music()
        for p in self.sfx_procs:
            try:
                p.kill()
                p.wait()
            except Exception:
                pass
        self.sfx_procs = []

    shutdown = stop_all


# --------------------------------------------------------------------------
# LRU image cache bounded by decoded bytes. The Luckfox has ~32MB for the
# whole of userspace (ISP reserves the rest), so decoded costumes must be
# evictable; a level's working set is well under 1MB, PNG re-decode of a
# small sprite is ~1ms.
# --------------------------------------------------------------------------
class LRUImages:
    def __init__(self, budget_bytes):
        self.budget = budget_bytes
        self.map = OrderedDict()
        self.bytes = 0

    @staticmethod
    def _cost(img):
        return img.width * img.height * len(img.getbands())

    def get(self, key):
        img = self.map.get(key)
        if img is not None:
            self.map.move_to_end(key)
        return img

    def put(self, key, img):
        if key in self.map:
            self.map.move_to_end(key)
            return
        self.map[key] = img
        self.bytes += self._cost(img)
        while self.bytes > self.budget and len(self.map) > 1:
            _, old = self.map.popitem(last=False)
            self.bytes -= self._cost(old)


# --------------------------------------------------------------------------
# Sprite
# --------------------------------------------------------------------------
class Costume:
    __slots__ = ("name", "path", "cx", "cy", "bbox")

    def __init__(self, name, path, cx, cy, bbox=None):
        self.name = name
        self.path = path
        self.cx = cx
        self.cy = cy
        self.bbox = bbox  # visible-pixel box [x0,y0,x1,y1] or None = full


class Sprite:
    def __init__(self, eng, name):
        self.eng = eng
        self.name = name
        spec = eng.manifest["targets"][name]
        self.costumes = [
            Costume(c["name"], c["img"], c["cx"], c["cy"], c.get("bbox"))
            for c in spec["costumes"]
        ]
        self._by_name = {}
        for i, c in enumerate(self.costumes):
            self._by_name.setdefault(c.name.lower(), i)
        self.sounds = spec["sounds"]
        self.baked_size = spec["size"]

        # editor-left pose from the sb3 (scripts rely on these defaults);
        # visibility always starts False ("when flag clicked: hide").
        self.x = float(spec.get("x", 0))
        self.y = float(spec.get("y", 0))
        self.direction = float(spec.get("direction", 90))
        self.rotation_style = spec.get("rotation_style", "all around")
        self.visible = False
        self.size = spec.get("default_size", self.baked_size)
        self.ghost = 0.0
        self.brightness = 0.0
        self.costume_i = spec.get("current_costume", 0) % len(self.costumes)

    # -- looks ------------------------------------------------------------
    def set_costume(self, which):
        if isinstance(which, int):
            self.costume_i = which % len(self.costumes)
        else:
            i = self._by_name.get(str(which).lower())
            if i is None:
                print(f"[Koki] {self.name}: unknown costume {which!r}")
            else:
                self.costume_i = i

    def next_costume(self):
        self.costume_i = (self.costume_i + 1) % len(self.costumes)

    @property
    def costume_name(self):
        return self.costumes[self.costume_i].name

    @property
    def costume_number(self):
        return self.costume_i + 1  # Scratch is 1-based

    def costume_is(self, name):
        return self.costume_name.lower() == name.lower()

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def front(self):
        self.eng.layer_front(self)

    def back(self):
        self.eng.layer_back(self)

    def clear_fx(self):
        self.ghost = 0.0
        self.brightness = 0.0

    # -- motion -----------------------------------------------------------
    def goto(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def goto_sprite(self, other):
        self.x = other.x
        self.y = other.y

    def point(self, direction):
        self.direction = float(direction)

    def point_towards(self, other):
        import math
        dx = other.x - self.x
        dy = other.y - self.y
        self.direction = math.degrees(math.atan2(dx, dy))

    def move_steps(self, steps):
        import math
        rad = math.radians(self.direction)
        self.x += steps * math.sin(rad)
        self.y += steps * math.cos(rad)

    def glide(self, secs, tx, ty):
        """Generator: glide over wall-clock secs (min one frame)."""
        x0, y0 = self.x, self.y
        tx, ty = float(tx), float(ty)
        now = self.eng.now
        t0 = now()
        while True:
            yield
            k = (now() - t0) / secs if secs > 0 else 1.0
            if k >= 1.0:
                self.x, self.y = tx, ty
                return
            self.x = x0 + (tx - x0) * k
            self.y = y0 + (ty - y0) * k

    def glide_to_sprite(self, secs, other):
        # Scratch samples the target once, at glide start.
        return self.glide(secs, other.x, other.y)

    # -- rendering / collision --------------------------------------------
    def _image(self):
        return self.eng.load_image(self.costumes[self.costume_i].path)

    def screen_rect(self, inset=0.0):
        """(left, top, right, bottom) in screen px of the VISIBLE pixels of
        the current costume (Scratch costumes often have transparent canvas
        margins much larger than the art)."""
        c = self.costumes[self.costume_i]
        img = self._image()
        iw = img.width
        bx0, by0, bx1, by1 = c.bbox or (0, 0, iw, img.height)
        cx, cy = c.cx, c.cy
        if self.rotation_style == "left-right" and self.direction < 0:
            cx = iw - cx
            bx0, bx1 = iw - bx1, iw - bx0
        scale = self.size / self.baked_size
        left = CENTER_X + self.x * STAGE_SCALE + (bx0 - cx) * scale
        top = CENTER_Y - self.y * STAGE_SCALE + (by0 - cy) * scale
        w = (bx1 - bx0) * scale
        h = (by1 - by0) * scale
        if inset:
            dx, dy = w * inset / 2, h * inset / 2
            return (left + dx, top + dy, left + w - dx, top + h - dy)
        return (left, top, left + w, top + h)

    def _alpha_mask(self):
        """Thresholded alpha channel (flip-aware), for pixel collision."""
        c = self.costumes[self.costume_i]
        flip = (self.rotation_style == "left-right" and self.direction < 0)
        key = (c.path, flip)
        cached = self.eng._mask_cache.get(key)
        if cached is not None:
            return cached
        a = self._image().getchannel("A")
        if flip:
            a = a.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        a = a.point(ALPHA_THRESH_LUT)
        self.eng._mask_cache.put(key, a)
        return a

    def _paste_origin(self):
        """Top-left screen position of the full costume image (flip-aware,
        assumes unscaled sprite -- all collision users run at baked size)."""
        c = self.costumes[self.costume_i]
        cx = c.cx
        if self.rotation_style == "left-right" and self.direction < 0:
            cx = self._image().width - cx
        return (CENTER_X + self.x * STAGE_SCALE - cx,
                CENTER_Y - self.y * STAGE_SCALE - c.cy)

    def touching(self, other, inset=0.0):
        """Scratch-style collision: visible-pixel rects as the cheap gate,
        then an actual alpha-mask overlap test. `inset` shrinks the gate
        rects (used to make a few checks intentionally lenient)."""
        if not self.visible or not other.visible:
            return False
        a = self.screen_rect(inset)
        b = other.screen_rect(inset)
        ox0 = max(a[0], b[0])
        oy0 = max(a[1], b[1])
        ox1 = min(a[2], b[2])
        oy1 = min(a[3], b[3])
        if ox0 >= ox1 or oy0 >= oy1:
            return False
        if self.size != self.baked_size or other.size != other.baked_size:
            return True   # runtime-scaled sprites (menus only): rect result

        ma = self._alpha_mask()
        mb = other._alpha_mask()
        ax, ay = self._paste_origin()
        bx, by = other._paste_origin()
        # overlap region in each image's local pixels
        ca = ma.crop((int(ox0 - ax), int(oy0 - ay),
                      int(ox1 - ax) + 1, int(oy1 - ay) + 1))
        cb = mb.crop((int(ox0 - bx), int(oy0 - by),
                      int(ox1 - bx) + 1, int(oy1 - by) + 1))
        if ca.size != cb.size:
            w = min(ca.width, cb.width)
            h = min(ca.height, cb.height)
            ca = ca.crop((0, 0, w, h))
            cb = cb.crop((0, 0, w, h))
        return ImageChops.multiply(ca, cb).getbbox() is not None

    # -- sound ------------------------------------------------------------
    def play(self, sound_name):
        s = self.sounds.get(sound_name)
        if s is None:
            print(f"[Koki] {self.name}: unknown sound {sound_name!r}")
            return
        self.eng.sound.sfx(s["file"])

    def play_until_done(self, sound_name):
        """Generator: start sfx, wait its duration."""
        s = self.sounds.get(sound_name)
        if s is None:
            print(f"[Koki] {self.name}: unknown sound {sound_name!r}")
            return
        self.eng.sound.sfx(s["file"])
        yield from self.eng.wait(s["dur"])

    def music(self, sound_name):
        """Loop a track as background music (replaces current music)."""
        s = self.sounds.get(sound_name)
        if s is None:
            print(f"[Koki] {self.name}: unknown music {sound_name!r}")
            return
        self.eng.sound.music(s["file"])


# --------------------------------------------------------------------------
# Script scheduler with Scratch broadcast semantics.
# --------------------------------------------------------------------------
class Script:
    __slots__ = ("key", "sprite", "fn", "gen", "dead")

    def __init__(self, key, sprite, fn):
        self.key = key
        self.sprite = sprite
        self.fn = fn
        gen = fn()
        # allow plain functions as instant handlers
        self.gen = gen if hasattr(gen, "__next__") else iter(())
        self.dead = False


class Engine:
    def __init__(self, ui, app_dir):
        import json
        self.ui = ui
        self.app_dir = app_dir
        self.assets = os.path.join(app_dir, "assets")
        with open(os.path.join(self.assets, "manifest.json")) as f:
            self.manifest = json.load(f)

        self.canvas = ui.canvas          # 240x175 RGB
        self.input = Input(ui)
        self.sound = SoundManager(self.assets)
        self.vars = {}                   # Scratch global variables
        self.random = random.Random()

        # byte-budgeted caches: the RV1103 has ~32MB for all of userspace
        # (ISP reserves the rest of the 64MB), so shrink on small systems
        img_default, fx_default = "3072", "1024"
        try:
            with open("/proc/meminfo") as f:
                total_kb = int(f.readline().split()[1])
            if total_kb < 48 * 1024:
                img_default, fx_default = "1536", "512"
                print(f"[Koki] small RAM ({total_kb // 1024}MB): "
                      "using reduced cache budgets")
        except Exception:
            pass
        img_kb = int(os.environ.get("NEODCT_KOKI_IMG_CACHE_KB", img_default))
        fx_kb = int(os.environ.get("NEODCT_KOKI_FX_CACHE_KB", fx_default))
        self._img_cache = LRUImages(img_kb * 1024)   # path -> RGBA
        self._fx_cache = LRUImages(fx_kb * 1024)     # (path,size,flip,fx) -> img
        self._mask_cache = LRUImages(256 * 1024)     # (path,flip) -> alpha L

        self.sprites = {}
        self.layers = []                 # draw order, back -> front
        self.backdrop_img = None
        self.backdrop_name = None

        self.handlers = {}               # event -> [(sprite, fn, key)]
        self.active = {}                 # key -> Script
        self._current = None
        self._hkey = 0
        self.quit = False

        self.perf = bool(os.environ.get("NEODCT_KOKI_PERF"))
        self.headless_frames = None      # harness hook
        self._vtime = None               # virtual clock (headless mode)

    def now(self):
        """Game clock: wall time normally, virtual time when headless."""
        return self._vtime if self._vtime is not None else _now()

    # -- assets -------------------------------------------------------------
    def load_image(self, rel):
        img = self._img_cache.get(rel)
        if img is None:
            img = Image.open(os.path.join(self.assets, rel)).convert("RGBA")
            self._img_cache.put(rel, img)
        return img

    # -- sprites / layers ----------------------------------------------------
    def sprite(self, name):
        s = self.sprites.get(name)
        if s is None:
            s = Sprite(self, name)
            self.sprites[name] = s
            self.layers.append(s)
        return s

    def layer_front(self, s):
        if s in self.layers:
            self.layers.remove(s)
        self.layers.append(s)

    def layer_back(self, s):
        if s in self.layers:
            self.layers.remove(s)
        self.layers.insert(0, s)

    def set_layer_order(self, names):
        """Initial paint order (back first), from the sb3 layerOrder."""
        order = {n: i for i, n in enumerate(names)}
        self.layers.sort(key=lambda s: order.get(s.name, 999))

    def backdrop(self, name):
        stage = self.manifest["targets"]["Stage"]
        for c in stage["costumes"]:
            if c["name"].lower() == str(name).lower():
                img = self.load_image(c["img"]).convert("RGB")
                # Backdrops render centered on the stage; crop to screen.
                left = int(round(c["cx"] - CENTER_X))
                top = int(round(c["cy"] - CENTER_Y))
                left = max(0, min(left, max(0, img.width - SCREEN_W)))
                top = max(0, min(top, max(0, img.height - SCREEN_H)))
                img = img.crop((left, top, left + SCREEN_W, top + SCREEN_H))
                self.backdrop_img = img
                self.backdrop_name = c["name"]
                return
        print(f"[Koki] unknown backdrop {name!r}")

    # -- stage sounds ----------------------------------------------------------
    def _stage_sound(self, name):
        s = self.manifest["targets"]["Stage"]["sounds"].get(name)
        if s is None:
            print(f"[Koki] Stage: unknown sound {name!r}")
        return s

    def stage_music(self, name):
        s = self._stage_sound(name)
        if s:
            self.sound.music(s["file"])

    def stage_sfx(self, name):
        s = self._stage_sound(name)
        if s:
            self.sound.sfx(s["file"])

    def stop_music(self):
        self.sound.stop_music()

    # -- script scheduling ----------------------------------------------------
    def on(self, event, sprite):
        """Decorator: register a generator function as a script handler.

        event: 'flag' or a broadcast message name. A message may have many
        handlers, even on one sprite (Scratch allows it); each gets its own
        restart key.
        """
        def deco(fn):
            self._hkey += 1
            key = self._hkey
            self.handlers.setdefault(event, []).append((sprite, fn, key))
            return fn
        return deco

    def broadcast(self, event):
        for sprite, fn, key in self.handlers.get(event, ()):
            old = self.active.get(key)
            if old is not None:
                old.dead = True           # Scratch: broadcast restarts scripts
            self.active[key] = Script(key, sprite, fn)

    def start_flag(self):
        self.broadcast("flag")

    def stop_other_scripts(self, sprite):
        cur = self._current
        for sc in self.active.values():
            if sc.sprite is sprite and sc is not cur:
                sc.dead = True

    def stop_all_scripts(self):
        for sc in self.active.values():
            sc.dead = True

    def teardown(self):
        """Break reference cycles and drop caches so repeated launches
        don't ratchet memory on a 32MB device."""
        self.stop_all_scripts()
        self.active.clear()
        self.handlers.clear()
        self._img_cache.map.clear()
        self._img_cache.bytes = 0
        self._fx_cache.map.clear()
        self._fx_cache.bytes = 0
        self._mask_cache.map.clear()
        self._mask_cache.bytes = 0
        self.sprites.clear()
        self.layers.clear()
        self.backdrop_img = None
        self.sound.shutdown()

    # -- script helpers (all generators) ---------------------------------------
    def wait(self, secs):
        end = self.now() + secs
        while True:
            yield
            if self.now() >= end:
                return

    def wait_until(self, pred):
        while not pred():
            yield

    def key(self, name):
        return self.input.key(name)

    def kdir(self):
        """Scratch's (key right - key left) as -1/0/1."""
        return (1 if self.input.key("right") else 0) - \
               (1 if self.input.key("left") else 0)

    def randint(self, a, b):
        lo, hi = (a, b) if a <= b else (b, a)
        return self.random.randint(int(lo), int(hi))

    # -- rendering ---------------------------------------------------------------
    def _costume_variant(self, s):
        """Current costume image with flip/size/ghost/brightness applied,
        cached with quantized effect levels so flashes reuse entries."""
        c = s.costumes[s.costume_i]
        img = s._image()

        flip = (s.rotation_style == "left-right" and s.direction < 0)
        size_q = int(round(s.size / s.baked_size * 20))       # 5% steps
        # Scratch clamps effects; scripts can push the raw values outside
        ghost_q = max(0, min(90, int(max(0.0, s.ghost) // 10) * 10))
        bri_q = max(-100, min(100, int(s.brightness // 25) * 25))

        if not flip and size_q == 20 and ghost_q == 0 and bri_q == 0:
            return img, c.cx, c.cy

        key = (c.path, size_q, flip, ghost_q, bri_q)
        cached = self._fx_cache.get(key)
        cx, cy = c.cx, c.cy
        scale = size_q / 20.0
        if scale != 1.0:
            cx *= scale
            cy *= scale
        if flip:
            w = img.width * scale
            cx = w - cx
        if cached is not None:
            return cached, cx, cy

        out = img
        if scale != 1.0:
            out = out.resize(
                (max(1, int(out.width * scale)), max(1, int(out.height * scale))),
                Image.Resampling.NEAREST)
        if flip:
            out = out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if bri_q:
            add = int(2.55 * bri_q)
            lut = bytes(max(0, min(255, v + add)) for v in range(256))
            r, g, b, a = out.split()
            out = Image.merge("RGBA", (r.point(lut), g.point(lut),
                                       b.point(lut), a))
        if ghost_q:
            factor = (100 - ghost_q) / 100.0
            lut = bytes(int(v * factor) for v in range(256))
            r, g, b, a = out.split()
            out = Image.merge("RGBA", (r, g, b, a.point(lut)))

        self._fx_cache.put(key, out)
        return out, cx, cy

    def render(self):
        cv = self.canvas
        if self.backdrop_img is not None:
            cv.paste(self.backdrop_img, (0, 0))
        else:
            cv.paste((0, 0, 0), (0, 0, SCREEN_W, SCREEN_H))
        for s in self.layers:
            if not s.visible or s.ghost >= 95:
                continue
            img, cx, cy = self._costume_variant(s)
            px = int(round(CENTER_X + s.x * STAGE_SCALE - cx))
            py = int(round(CENTER_Y - s.y * STAGE_SCALE - cy))
            if px > SCREEN_W or py > SCREEN_H or \
               px + img.width < 0 or py + img.height < 0:
                continue
            cv.paste(img, (px, py), img)
        self.ui.fb.update(cv)

    # -- pause / quit -----------------------------------------------------------
    def _pause_menu(self):
        """Back key: small confirm overlay. Returns True to quit the app."""
        ui = self.ui
        d = ui.draw
        d.rectangle((30, 55, 210, 120), fill="black", outline="white")
        d.text((45, 62), "Quit Koki?", font=ui.font_n, fill="white")
        d.text((45, 90), "Enter=Yes  C=No", font=ui.font_s, fill="white")
        ui.fb.update(self.canvas)
        # swallow the held back key first
        while self.input.key("back"):
            self.input.poll()
            time.sleep(0.02)
        while True:
            self.input.poll()
            if "enter" in self.input.pressed:
                return True
            if "back" in self.input.pressed:
                return False
            time.sleep(0.02)

    # -- main loop ---------------------------------------------------------------
    def run(self):
        if self.headless_frames is not None:
            self._vtime = 0.0  # virtual clock must exist before any script runs
        self.start_flag()
        frames = 0
        busy_acc = 0.0
        t_report = _now()
        try:
            while not self.quit:
                t0 = _now()
                self.input.poll()
                if "back" in self.input.pressed:
                    if self._pause_menu():
                        break
                    self.input.poll()

                # advance scripts (snapshot: new scripts run next frame)
                for sc in list(self.active.values()):
                    if sc.dead:
                        continue
                    self._current = sc
                    try:
                        next(sc.gen)
                    except StopIteration:
                        sc.dead = True
                    except Exception:
                        import traceback
                        print(f"[Koki] script crashed in {sc.sprite.name if sc.sprite else '?'}")
                        traceback.print_exc()
                        sc.dead = True
                self._current = None
                for key in [k for k, sc in self.active.items() if sc.dead]:
                    # a restarted script may have replaced this key already
                    if self.active[key].dead:
                        del self.active[key]

                self.render()

                busy = _now() - t0
                busy_acc += busy
                frames += 1
                if self.perf and _now() - t_report >= 5.0:
                    print(f"[Koki] avg frame {busy_acc / frames * 1000:.1f}ms "
                          f"({frames / (_now() - t_report):.1f} fps)")
                    frames = 0
                    busy_acc = 0.0
                    t_report = _now()

                if self.headless_frames is not None:
                    self._vtime = (self._vtime or 0.0) + FRAME_DT
                    self.headless_frames -= 1
                    if self.headless_frames <= 0:
                        break
                else:
                    rest = FRAME_DT - busy
                    if rest > 0:
                        time.sleep(rest)
        finally:
            self.teardown()
