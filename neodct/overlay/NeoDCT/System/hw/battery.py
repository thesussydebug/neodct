"""
battery.py -- LiPo fuel-gauge reader for NeoDCT presumably under the MAX17043.
"""

import fcntl
import os
import time

I2C_SLAVE = 0x0703  # linux/i2c-dev.h

DEFAULT_BUS = 1
DEFAULT_ADDR = 0x36
REG_VCELL = 0x02
REG_SOC = 0x04

VCELL_STEP_V = 0.00125  # 1.25 mV per LSB (MAX17043; MAX17048 differs)

_CACHE_TTL = 15.0       # seconds; render loop may call every frame
_cache = {"t": -1e9, "percent": None, "voltage": None}


def _env_int(name, default, base=10):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        if base == 16 or raw.lower().startswith("0x"):
            return int(raw, 16)
        return int(raw)
    except ValueError:
        return default


def _bus():
    return _env_int("NEODCT_FUELGAUGE_BUS", DEFAULT_BUS)


def _addr():
    return _env_int("NEODCT_FUELGAUGE_ADDR", DEFAULT_ADDR, base=16)


def _read_reg16(fd, reg):
    """Set the register pointer, then read the 16-bit big-endian value."""
    os.write(fd, bytes((reg,)))
    data = os.read(fd, 2)
    if len(data) != 2:
        raise OSError(f"short read from fuel gauge reg 0x{reg:02X}")
    return (data[0] << 8) | data[1]


def _read_raw():
    """Return (percent|None, voltage|None) by reading the gauge once."""
    path = f"/dev/i2c-{_bus()}"
    try:
        fd = os.open(path, os.O_RDWR)
    except OSError:
        return None, None
    try:
        fcntl.ioctl(fd, I2C_SLAVE, _addr())
        soc = _read_reg16(fd, REG_SOC)
        vcell = _read_reg16(fd, REG_VCELL)
    except OSError:
        return None, None
    finally:
        os.close(fd)

    # SOC: high byte = %, low byte = 1/256 % -> raw / 256 is the real value.
    percent = max(0, min(100, round(soc / 256.0)))
    voltage = round((vcell >> 4) * VCELL_STEP_V, 3)
    return percent, voltage


def read(force=False):
    """Return (percent|None, voltage|None), cached for _CACHE_TTL seconds."""
    now = time.monotonic()
    if force or (now - _cache["t"]) >= _CACHE_TTL:
        percent, voltage = _read_raw()
        _cache.update(t=now, percent=percent, voltage=voltage)
    return _cache["percent"], _cache["voltage"]


def read_percent(force=False):
    """Battery charge 0-100, or None when the gauge is not reachable."""
    return read(force=force)[0]


def read_voltage(force=False):
    """Cell voltage in volts, or None when the gauge is not reachable."""
    return read(force=force)[1]


def label(force=False):
    """Status-bar string: 'NN%' or '?' when the gauge is absent."""
    percent = read_percent(force=force)
    return "?" if percent is None else f"{percent}%"


if __name__ == "__main__":
    p, v = read(force=True)
    if p is None:
        print(f"no fuel gauge on /dev/i2c-{_bus()} @ 0x{_addr():02X} (shows '?')")
    else:
        print(f"battery: {p}%  ({v} V)  via /dev/i2c-{_bus()} @ 0x{_addr():02X}")
