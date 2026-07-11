# Koki → NeoDCT Port Notes

## Game summary (from decompiled sb3)

Koki is a boss-rush platformer. Flow:

1. **Boot**: Dynaris logo fade in/out → intro title (Koki icon bobbing, theme
   music) → flashing START button (Enter) → info panel (Sprite1, Enter) → lobby.
2. **Lobby** (backdrop5, lobby music): side-view room, platform floor.
   Koki walks (left/right), jumps (z). Doors 1-4 appear as unlocked
   (`doors` var). Touch door + press x/up → level. Lives icon shows 3/2/1.
3. **Level 1** (backdrop3): Boss "Enemy 1". Loop: idle → 3 volleys of ground
   shockwaves (two waves sweep from boss to left; jump them) → a cannon
   spawns; touch + x → cannonball arcs to boss → boss damage (health bar
   Enemy1Stats, ~4 hits) → boss pounce w/ "press X" quicktime dodge
   (rightdash) → repeat. Boss dead → unlock door 2 → lobby.
4. **Level 2** (backdrop4): plane section. Cutscene (Koki falls onto plane).
   Up/down to fly, z+up / z+down = boost dash (1s cooldown). Enemy2 (dragon,
   right side) tracks plane Y and lashes a long tongue. After 4 attacks a
   cannon drops from the top; touch + x → cannonball → dragon damage (7 hits,
   at ≥5 damage switches to faster "cycle 2" and gas tanks spawn = heal).
   Dead → doors=3 → lobby.
5. **Level 3** (backdrop6): auto-run chase. Koki fixed at x=90, jump only (z).
   Enemy 3 (popcorn machine "Popi", left, 150%) shoots cannonballs at head
   height (jump over), random floor shockwaves sweep right→left. Cannon
   slides by; touch + x → hit Popi. 5 shots per phase, 3 phases
   (cannondefeats 1→4). Falling in the abyss gap = lose a life. Dead →
   doors=4, music stops → lobby.
6. **Final level** (Door4 → cutscene: Riby (evil Koki) bursts out, knocks
   Koki around; then fight on lobby backdrop). Riby attack patterns:
   - run + ground-pound → shockwaves both directions (Shockwave3 left,
     Shockwave4 right) + delayed golden heal wave (Shockwave5, touch =
     +1 HP `partialrestore`)
   - evil cannon: crawls out at Riby, aims at Koki 1.5s, shoots ball(s)
     both directions at floor level (jump)
   - jump attacks: leaps to ceiling center, aims, slams onto Koki + shockwave,
     repeat random(3,6)
   - low HP (≥ costume5 on Enemy4Stats): possesses Enemy 1 (purple), Enemy 1
     pounce loop; hitting it (touch+x during vulnerable) ejects Riby → Riby
     dash sweeps → back to normal patterns.
   Riby is only vulnerable when `RibyDanger == 0`: touch + x = damage
   (14-step health bar). Riby dead → door4 reopens → enter → ending cutscene
   (walk across with trophy) → white → **score screen** (grade by
   knockouts/taken damage/has healed: A/B/C/D/F, each with its own art +
   music) → Enter → lobby.
- **Game over** (lives<0 handled at knockout): GameOver screen + music,
  Enter → reset lives=3, lock doors, lobby.

Global vars: lives, doors, taken damage, knockouts, has healed,
cannondefeats, RibyDanger, evilcanonballdirection, healwavedirection,
damageway4.

Health: KokiStats costume1→4 then Oof (4 hits + KO). Boss bars analogous.

## Controls mapping (Scratch → NeoDCT)

| Scratch | Action | QEMU keyboard (evdev) | Phone keypad |
|---|---|---|---|
| left/right arrow | walk | 105/106 | num4(5)/num6(7) |
| up arrow | enter door / plane up | 103 | num2(3) |
| down arrow | plane down | 108 | num8(9) |
| z | jump / boost | 44 | num5(6) or star(42) |
| x | action/shoot/dodge | 45 | num0(11) or hash(43) |
| enter | start/confirm | 28 | navikey(28) |
| — | quit app | 14 (hold/back) | clear(14) |

## Rendering / scaling

- Scratch stage 480×360 → screen 240×175. Uniform scale **0.5**, crop 2.5
  stage-px top/bottom (visible scratch y ∈ [-175,175]).
- screen_x = 120 + 0.5*x ; screen_y = 87.5 - 0.5*y (round).
- All costumes pre-rendered to final pixel size at build time
  (SVG via rsvg-convert --zoom; PNG res=2 scaled ×0.25; × sprite default
  size%). Rotation centers scaled identically, stored in assets manifest.
- Pixelate effect (set once everywhere, 10-15) ≈ 1.0-1.25px blocks at our
  resolution → **omitted** (half-res display already provides the chunk).
- Ghost/brightness flash effects: runtime variant cache per costume
  (quantized to 10% steps, computed lazily, bounded).
- rotation: only left-right flip is used for characters (cache flipped);
  EvilCannon/Riby "point towards" reduced to flip; no arbitrary rotation
  needed except cannon aim visual — use flip (rotationStyle is left-right).

## Engine model (the important part)

Generator-based cooperative scheduler replicating Scratch semantics:
- Each Scratch script = a Python generator; `yield` = one frame (30 FPS).
- `wait(t)` = max(1, round(t*30)) frames; `glide` = per-frame lerp.
- `broadcast(name)` starts handler generators (restarting a handler that is
  already running, like Scratch); `stop_other_scripts(sprite)` etc.
- Sprite objects: x, y, dir (flip), costume, visible, size, ghost, bright,
  layer; `touching(other)` = scaled-rect overlap (slight inset).
- Full-frame composite per tick into ui.canvas (240×175), one fb.update.
  ~10-20 alpha pastes/frame at this size is fast C-side work.
- Input: read ui.keypad_fd evdev press AND release → held-key set
  (`key_pressed()` equivalent); missing on Scratch's global key state
  otherwise.

## Sound

- Music: ffmpeg → mono 2205kHz 64k MP3, played via `mpv --loop=inf` child
  process (MusicPlayer already proves mpv works on target).
- SFX: short WAVs → 22050 Hz mono 16-bit, played via short-lived mpv
  (rate limited); all audio wrapped in SoundManager that degrades to
  log-only when device/audio missing (kernel audio not done yet).

## Deployment

- App dir: `neodct/overlay/NeoDCT/System/apps/Koki/`
  (manifest.json id=10, main.py, engine.py, game.py, assets/, icon.png)
- Asset builder (host-side): `tools/build_assets.py` in app dir; reads
  `koki.sb3 files/` at repo root, writes `assets/`. Not needed on device.
- No system file changes anticipated → stay on main branch (koki-tests
  branch only if system edits become necessary).

## Status (2026-07-09)

Port is complete and passing headless tests. All 47 sprites / ~3600 blocks
ported; every level, the final boss, game over, ending and score screens
verified via screenshot harness.

### Testing without QEMU or hardware

The app only touches `ui.canvas`, `ui.fb.update()` and `ui.keypad_fd`, so
`tools/harness.py` stubs those and runs the real engine headlessly with a
virtual 30fps clock and scripted keys:

    # venv with Pillow needed on host (system python lacks PIL)
    python3 tools/harness.py --frames 900 --press 200:enter \
        --press 320:enter --hold 400-416:right --shot 500 --trace --out /tmp/shots

`tools/smoke.py` jump-starts each level/screen directly (lv1 lv2 lv3 final
gameover ending) and saves screenshots.

### Rebuilding assets

    python3 tools/build_assets.py   # host-side; needs rsvg-convert, ffmpeg,
                                    # imagemagick; reads <repo>/koki.sb3 files/

### Performance

Host: ~0.16 ms/frame during a boss fight (full composite + script tick).
Budget on RV1103 at 30fps is 33ms — expected comfortably smooth given the
11.5x display driver speedup and all costumes pre-scaled at build time.
Set NEODCT_KOKI_PERF=1 to print avg frame ms every 5s on device.

### Known deviations from the Scratch original

- Pixelate effect omitted (blocks would be ~1px at 240x175 — invisible).
- "Possessed" Enemy 1 uses darkened sprite instead of Scratch color-shift.
- Final-cutscene music pitch-slide replaced by a delayed stop (mpv can't
  pitch-bend a running track).
- Music loops via `mpv --loop=inf` instead of `forever/play until done`.
- Collision is pixel-mask based like Scratch (visible-pixel bbox rects as
  the cheap gate, alpha-mask overlap as the truth; alpha > 40 = solid).

### Sound

WAVs converted to 22kHz mono (sfx=WAV, music=64k MP3, 13MB total).
SoundManager degrades to silent-with-log when /dev/snd or mpv is missing
(kernel audio still WIP), controlled by NEODCT_KOKI_NOSOUND=1 as well.

### Hardware input caveat

The I2C matrix keypad driver reports one key at a time (no chords), so
run+jump simultaneously won't work on the physical keypad until the
pcf8575 scanner supports multi-key. QEMU/evdev keyboards are fine.

### Memory (added 2026-07-09 after hardware OOM, exit 137)

Decoded costume images are now held in byte-budgeted LRU caches instead of
forever: img cache 3MB / fx cache 1MB, automatically halved when
/proc/meminfo reports < 48MB total (the ISP-carved 32MB case). Override with
NEODCT_KOKI_IMG_CACHE_KB / NEODCT_KOKI_FX_CACHE_KB. Verified: full-game tour
peaks exactly at budget; evictions cost ~1ms PNG re-decode on scene changes
only. If the ISP reserved memory is ever reclaimed in the device tree
(camera unused by NeoDCT), the defaults get roomier automatically.

### Hardware bugfix round (2026-07-10)

- Matrix keypad is single-key: a new press now RELEASES the previously held
  key (fixes 'walk right + press X = drift right forever').
- Engine.teardown() + main.py module purge/gc on exit: repeated launches no
  longer ratchet memory / lag the OS on the 32MB device.
- Collision switched from full-canvas rects to Scratch-style pixel masks;
  fixes early hits from transparent canvas margins (Enemy 1 pounce killed
  before visual contact; Enemy2's tongue hit as a 64px-tall band). Dodge
  verified both ways in the harness (X held -> dodge, no X -> damage).

### Playability round (2026-07-10, user-sanctioned deviations)

- FIXED PORT BUG: walk/jump/idle animation gates checked the invisible
  physics dot instead of CharacterAnim (as the original does) -- the walk
  cycle never played. Koki animates properly now.
- Post-hit invincibility: 'take damage'/'takeplanedamage' gate through
  0.9s i-frames, fanning out as 'koki hurt'/'plane hurt' (double shockwave
  no longer costs 2 HP).
- Quicktime dash flees away from Enemy 1 instead of always dashing right.
- Plane boost is chordless: Z boosts in the last vertical direction tapped
  within 2s, else toward open space (keypads/ghosting keyboards can't chord).
- Attack speeds scaled by NEODCT_KOKI_ATTACK_SLOW (default 1.35 = 35%
  slower): lvl1 shockwaves, Enemy1 pounce, Popi balls, Riby shockwaves/
  cannonballs/dives, Enemy2 cycle-2 pace. Set to 1.0 for original speeds.
- sb3 source moved out of the repo; build_assets.py now also looks in
  ~/Downloads/Koki/resources/app/koki.sb3 files/.
