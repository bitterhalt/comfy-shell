"""
Moon phase calculation with emoji icons
Uses improved algorithm for accurate phase calculation
"""

import math
from datetime import datetime

# Moon phase emojis (Unicode)
MOON_EMOJIS = {
    "new": "🌑",  # New Moon
    "waxing_crescent": "🌒",  # Waxing Crescent
    "first_quarter": "🌓",  # First Quarter
    "waxing_gibbous": "🌔",  # Waxing Gibbous
    "full": "🌕",  # Full Moon
    "waning_gibbous": "🌖",  # Waning Gibbous
    "last_quarter": "🌗",  # Last Quarter
    "waning_crescent": "🌘",  # Waning Crescent
}


def moon_phase_accurate(date: datetime) -> float:
    """
    Calculate moon phase (0.0 = New, 0.5 = Full, 1.0 = New)
    Uses astronomical calculation similar to iPhone/online calculators

    Returns fraction of lunar cycle (0.0 to 1.0)
    """
    # Known new moon: January 6, 2000, 18:14 UTC (J2000.0 epoch)
    known_new_moon = datetime(2000, 1, 6, 18, 14)

    # Synodic month (new moon to new moon) = 29.53058867 days
    synodic_month = 29.53058867

    # Calculate days since known new moon
    days_diff = (date - known_new_moon).total_seconds() / 86400.0

    # Calculate phase as fraction of synodic month
    phase = (days_diff % synodic_month) / synodic_month

    return phase


def moon_illumination(date: datetime) -> float:
    """
    Calculate moon illumination percentage (0.0 to 100.0)
    0% = New Moon, 100% = Full Moon
    """
    phase = moon_phase_accurate(date)

    # Illumination follows cosine curve:
    # 0.0 (new) -> 0%, 0.5 (full) -> 100%, 1.0 (new) -> 0%
    illumination = (1 - math.cos(phase * 2 * math.pi)) / 2 * 100

    return illumination


def days_until_full_moon(date: datetime) -> float:
    """
    Calculate days until next full moon
    Returns decimal days
    """
    phase = moon_phase_accurate(date)
    synodic_month = 29.53058867

    # Full moon is at phase 0.5
    if phase < 0.5:
        # Before full moon in current cycle
        days_until = (0.5 - phase) * synodic_month
    else:
        # After full moon, wait for next cycle
        days_until = (1.0 - phase + 0.5) * synodic_month

    return days_until


def days_until_new_moon(date: datetime) -> float:
    """
    Calculate days until next new moon
    Returns decimal days
    """
    phase = moon_phase_accurate(date)
    synodic_month = 29.53058867

    # New moon is at phase 0.0/1.0
    days_until = (1.0 - phase) * synodic_month

    return days_until


def moon_phase_index(date: datetime) -> int:
    """
    Get moon phase index (0-7) for emoji selection

    0 = New Moon
    1 = Waxing Crescent
    2 = First Quarter
    3 = Waxing Gibbous
    4 = Full Moon
    5 = Waning Gibbous
    6 = Last Quarter
    7 = Waning Crescent
    """
    phase = moon_phase_accurate(date)

    # Convert to 0-7 index
    # Add 0.0625 (1/16) to center phases around their midpoints
    index = int((phase + 0.0625) * 8) % 8

    return index


def moon_phase_name(date: datetime) -> str:
    """Get the name of the current moon phase"""
    phase_names = [
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    ]
    return phase_names[moon_phase_index(date)]


def moon_emoji(date: datetime) -> str:
    """
    Get moon phase emoji for given date
    Returns Unicode emoji character
    """
    phase_map = [
        "new",
        "waxing_crescent",
        "first_quarter",
        "waxing_gibbous",
        "full",
        "waning_gibbous",
        "last_quarter",
        "waning_crescent",
    ]

    index = moon_phase_index(date)
    phase_key = phase_map[index]

    return MOON_EMOJIS[phase_key]


def moon_info(date: datetime) -> dict:
    """
    Get complete moon information for tooltip

    Returns dict with:
    - phase_name: str (e.g., "Full Moon")
    - emoji: str (e.g., "🌕")
    - illumination: float (0.0 to 100.0)
    - days_to_full: float
    - days_to_new: float
    """
    return {
        "phase_name": moon_phase_name(date),
        "emoji": moon_emoji(date),
        "illumination": moon_illumination(date),
        "days_to_full": days_until_full_moon(date),
        "days_to_new": days_until_new_moon(date),
    }


def moon_tooltip(date: datetime) -> str:
    """
    Generate formatted tooltip text for moon phase
    """
    info = moon_info(date)

    tooltip = f"{info['phase_name']} {info['emoji']}\n"
    tooltip += f"Illumination: {info['illumination']:.1f}%\n"

    # Show whichever is closer
    if info["days_to_full"] < info["days_to_new"]:
        days = info["days_to_full"]
        if days < 1:
            tooltip += f"Full moon in {days * 24:.1f} hours"
        else:
            tooltip += f"Full moon in {days:.1f} days"
    else:
        days = info["days_to_new"]
        if days < 1:
            tooltip += f"New moon in {days * 24:.1f} hours"
        else:
            tooltip += f"New moon in {days:.1f} days"

    return tooltip


def moon_icon_for(date: datetime) -> str:
    """
    Main function for compatibility with existing code
    Returns emoji instead of SVG path
    """
    return moon_emoji(date)


__all__ = [
    "moon_emoji",
    "moon_phase_name",
    "moon_illumination",
    "moon_info",
    "moon_tooltip",
    "days_until_full_moon",
    "days_until_new_moon",
    "moon_icon_for",
]
