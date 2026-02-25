import os

SETTINGS_PATH = "/NeoDCT/User/settings.prop"
DEFAULTS = {
    "system.audio.ringtone": "/NeoDCT/System/tones/Entertainer.wma",
    "system.ui.wallpaper": "NONE",
    "system.ui.engineering_mode": "ON",
    "system.os.versionnumber": "0.1.9a",
    "system.os.versionname": "NeoDCT System v0.1.9a M1",
}


def _parse_settings(text):
    settings = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        settings[key.strip()] = value.strip()
    return settings


def _format_settings(settings):
    lines = []
    for key in sorted(settings.keys()):
        value = settings[key]
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _ensure_parent(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r") as f:
            return _parse_settings(f.read())
    except Exception as exc:
        print(f"[Settings] Failed to read {SETTINGS_PATH}: {exc}")
        return {}


def save_settings(settings):
    _ensure_parent(SETTINGS_PATH)
    temp_path = SETTINGS_PATH + ".tmp"
    data = _format_settings(settings)
    with open(temp_path, "w") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, SETTINGS_PATH)


def load_with_defaults(defaults=None):
    settings = load_settings()
    defaults = defaults or {}
    changed = False
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
            changed = True
    if changed or not os.path.exists(SETTINGS_PATH):
        save_settings(settings)
    return settings


def get_setting(key, default=None):
    settings = load_with_defaults(DEFAULTS)
    return settings.get(key, default)


def set_setting(key, value):
    settings = load_with_defaults(DEFAULTS)
    settings[key] = value
    save_settings(settings)
