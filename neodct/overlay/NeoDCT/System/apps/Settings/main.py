import os

from System.ui.framework import SoftKeyBar, MessageDialog, VerticalList
from System.core.SettingsStorage import get_setting, set_setting

ROOT_ID = 4
WALLPAPER_DIR = "/NeoDCT/User/wallpapers"
SUPPORTED_WALLPAPERS = (".jpg", ".jpeg")


def _scan_wallpapers():
    wallpapers = []
    if not os.path.exists(WALLPAPER_DIR):
        return wallpapers
    for root, _, files in os.walk(WALLPAPER_DIR):
        for filename in sorted(files):
            if filename.lower().endswith(SUPPORTED_WALLPAPERS):
                full_path = os.path.join(root, filename)
                display = os.path.splitext(os.path.basename(filename))[0]
                wallpapers.append({"name": display, "path": full_path})
    wallpapers.sort(key=lambda item: item["name"].lower())
    return wallpapers


def _show_wallpaper_menu(ui):
    try:
        os.makedirs(WALLPAPER_DIR, exist_ok=True)
    except Exception:
        pass

    wallpapers = _scan_wallpapers()
    if not wallpapers:
        MessageDialog(ui, f"No wallpapers found.\nAdd .jpg files to\n{WALLPAPER_DIR}").show()

    wallpapers.insert(0, {"name": "None", "path": "NONE"})
    names = [wallpaper["name"] for wallpaper in wallpapers]
    vlist = VerticalList(ui, "Wallpaper", names, app_id=ROOT_ID)
    SoftKeyBar(ui).update("Select", present=False)
    selection = vlist.show()
    if selection == -1:
        return

    selected = wallpapers[selection]
    set_setting("system.ui.wallpaper", selected["path"])
    if selected["path"] == "NONE":
        ui.wallpaper = None
    else:
        ui.wallpaper = ui.load_wallpaper(selected["path"])
    MessageDialog(ui, f"Wallpaper set to\n{selected['name']}").show()


def _wrap_text(ui, text, max_width, font):
    words = (text or "").split()
    if not words:
        return [""]
    lines = []
    current = ""

    def fits(candidate):
        width, _ = ui.get_text_size(candidate, font)
        return width <= max_width

    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if fits(candidate):
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def _show_about(ui):
    title = "NeoDCT"
    screen_w = getattr(ui, "W", 300)
    screen_h = getattr(ui, "H", 172)
    softkey_h = getattr(ui, "SOFTKEY_H", 30)
    content_bottom = getattr(ui, "content_bottom", screen_h - softkey_h)
    header_y = max(30, int(screen_h * 0.11))

    version_name = get_setting("system.os.versionname", "NeoDCT OS")
    version_number = get_setting("system.os.versionnumber", "")
    build_time = get_setting("system.os.buildtime", "Unknown")
    if not build_time or build_time.upper() == "NONE":
        build_time = "Unknown"

    ui.draw.rectangle((0, 0, screen_w, screen_h), fill="black")

    w, _ = ui.get_text_size(title, ui.font_n)
    ui.draw.text(((screen_w - w) // 2, 12), title, font=ui.font_n, fill="white")
    line_pad = max(10, int(screen_w * 0.12))
    ui.draw.line((line_pad, header_y, screen_w - line_pad, header_y), fill="white")

    y = header_y + 12
    if version_name:
        name_lines = _wrap_text(ui, version_name, screen_w - 20, ui.font_s)
        for line in name_lines[:2]:
            w, _ = ui.get_text_size(line, ui.font_s)
            if y > content_bottom - 18:
                break
            ui.draw.text(((screen_w - w) // 2, y), line, font=ui.font_s, fill="white")
            y += 16
        y += 6

    if version_number:
        if y <= content_bottom - 18:
            ui.draw.text((10, y), f"Version: {version_number}", font=ui.font_s, fill="gray")
        y += 16
    if y <= content_bottom - 18:
        ui.draw.text((10, y), "Build time:", font=ui.font_s, fill="gray")
    y += 16
    build_lines = _wrap_text(ui, build_time, screen_w - 20, ui.font_s)
    for line in build_lines[:2]:
        if y > content_bottom - 18:
            break
        ui.draw.text((10, y), line, font=ui.font_s, fill="gray")
        y += 16

    SoftKeyBar(ui).update("Back", present=False)
    ui.fb.update(ui.canvas)

    while True:
        key = ui.wait_for_key()
        if key == 14:
            return

def run(ui):
    while True:
        menu = VerticalList(ui, "Settings", ["Wallpaper", "About"], app_id=ROOT_ID)
        SoftKeyBar(ui).update("Select", present=False)
        selection = menu.show()
        if selection == -1:
            return
        if selection == 0:
            _show_wallpaper_menu(ui)
        elif selection == 1:
            _show_about(ui)
