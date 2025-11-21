import os
from datetime import datetime

ICON_BASE = os.path.expanduser("~/.config/ignis/assets/icons/weather")


def icon_path(name: str) -> str:
    return os.path.join(ICON_BASE, f"{name}.svg")


def moon_phase_index(date: datetime) -> int:
    """Conway's moon phase algorithm → returns 0–7."""
    year = date.year
    month = date.month
    day = date.day

    if month < 3:
        year -= 1
        month += 12

    k1 = int(365.25 * (year + 4712))
    k2 = int(30.6 * (month + 1))
    t = k1 + k2 + day - 694039.09
    t /= 29.5305882
    t -= int(t)

    if t < 0:
        t += 1

    return int(t * 8 + 0.5) % 8


PHASE_MAP = {
    0: "moon-new",
    1: "moon-waxing-crescent",
    2: "moon-first-quarter",
    3: "moon-waxing-gibbous",
    4: "moon-full",
    5: "moon-waning-gibbous",
    6: "moon-last-quarter",
    7: "moon-waning-crescent",
}


def moon_icon_for(date: datetime) -> str:
    idx = moon_phase_index(date)
    return icon_path(PHASE_MAP[idx])
