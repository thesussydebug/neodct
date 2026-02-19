# Repository Guidelines

## Project Structure & Module Organization
- `configs/`: Buildroot defconfigs for QEMU and Radxa Zero 3W.
- `overlay/`: root filesystem overlay copied into the image.
  - `overlay/NeoDCT/`: Python UI/system code, apps, and UI assets.
  - `overlay/bin/`, `overlay/etc/`: runtime scripts and system config.
  - `overlay/tests/`: media fixtures and ad‑hoc files (e.g., mp3/avi) for manual playback checks.
- `nonfree/`: binary blobs/firmware; avoid edits unless required.

## Build, Run, and Development Commands
This repo is a Buildroot external tree. From a Buildroot checkout:
```sh
make BR2_EXTERNAL=/path/to/neodct neodct_qemu_defconfig
make
```
For hardware images:
```sh
make BR2_EXTERNAL=/path/to/neodct neodct_radxa_defconfig
```
The UI runs directly on `/dev/fb0` and uses keypad-style input. In QEMU, keyboard input is mapped for early development.

## Coding Style & Naming Conventions
- Python: 4-space indentation, `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants.
- Preserve absolute runtime paths (e.g., `/NeoDCT/System/...`) used by the UI.
- App layout: `overlay/NeoDCT/System/apps/<AppName>/` with `manifest.json`, `main.py`, `icon.png`.
- Shell scripts are only for launching external programs (e.g., `netsurf`, `mpv`, `libretro`); keep shebangs and executable bits.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and sentence‑case, often with a scope prefix (e.g., `Messages: ...`, `Fix ...`).
- PRs should include a concise summary, note overlay/config impacts, and attach screenshots or device photos for UI changes.

## Platform & Constraints
- Embedded Buildroot OS (not a traditional distro): no X11, no systemd, no package manager.
- Target hardware: Radxa Zero 3W (RK3566, 1GB RAM), ST7789 240×240 framebuffer, SIM7600G‑H LTE HAT.
- UI goal: emulate Nokia 5190 / DCT‑3 behavior and visuals.
