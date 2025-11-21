# weather_data.py
#
# Fetches OpenWeather data
# Produces clean dict for weather_window.py
# Loads your custom SVG icons
# Exposes:
#   fetch_weather_async()
#   format_time_hm()
#   icon_path()
#   (moon handled separately)

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ignis import utils

from .moon import moon_icon_for

# ───────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────

DEFAULT_CITY_ID = "643492"
API_KEY_ENV = "OPEN_WEATHER_APIKEY"

CACHE_FILE = Path(os.path.expanduser("~/.cache/ignis/weather_cache.json"))
CACHE_TTL = 600

USE_12H = os.getenv("IGNIS_WEATHER_12H", "").lower() in ("1", "true", "yes", "on")

ICON_BASE = os.path.expanduser("~/.config/ignis/assets/icons/weather")


# ───────────────────────────────────────────────
# ICON PATH
# ───────────────────────────────────────────────


def icon_path(name: str) -> str:
    return f"{ICON_BASE}/{name}.svg"


# ───────────────────────────────────────────────
# TIME FORMATTERS
# ───────────────────────────────────────────────


def format_time_hm(dt: datetime) -> str:
    """Return HH:MM in 24h or 12h based on user env."""
    if USE_12H:
        return dt.strftime("%-I:%M %p").lstrip("0")
    return dt.strftime("%H:%M")


# ───────────────────────────────────────────────
# CACHE HELPERS
# ───────────────────────────────────────────────


def _load_cache() -> Optional[Dict[str, Any]]:
    try:
        if not CACHE_FILE.exists():
            return None
        return json.loads(CACHE_FILE.read_text())
    except:
        return None


def _save_cache(data: Dict[str, Any]):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(data))
    except:
        pass


# ───────────────────────────────────────────────
# OPENWEATHER FETCH HELPERS
# ───────────────────────────────────────────────


def _build_url(endpoint: str) -> Optional[str]:
    api_key = os.getenv(API_KEY_ENV, "").strip()
    if not api_key:
        return None
    city_id = os.getenv("OPEN_WEATHER_CITY_ID", DEFAULT_CITY_ID).strip()
    base = "https://api.openweathermap.org/data/2.5"
    return f"{base}/{endpoint}?id={city_id}&units=metric&appid={api_key}"


async def _curl_json_async(url: str) -> Optional[dict]:
    try:
        res = await utils.exec_sh_async(f"curl -sfL '{url}'")
        if res.returncode != 0:
            return None
        return json.loads(res.stdout)
    except:
        return None


# ───────────────────────────────────────────────
# WEATHER → CUSTOM ICONS
# ───────────────────────────────────────────────


def _map_icon(code: str) -> str:
    """Map OpenWeather code → your custom SVG icons."""
    if not code:
        return icon_path("not-available")

    base = code[:2]
    day = code.endswith("d")

    if base == "01":
        return icon_path("clear-day" if day else "clear-night")
    if base == "02":
        return icon_path("partly-cloudy-day" if day else "partly-cloudy-night")
    if base in ("03", "04"):
        return icon_path("cloudy")
    if base == "09":
        return icon_path("drizzle")
    if base == "10":
        return icon_path("rain")
    if base == "11":
        return icon_path("thunderstorms")
    if base == "13":
        return icon_path("snow")
    if base == "50":
        return icon_path("fog")

    return icon_path("not-available")


# ───────────────────────────────────────────────
# MAIN FETCH FUNCTION
# ───────────────────────────────────────────────


async def fetch_weather_async() -> Optional[Dict[str, Any]]:
    cached = _load_cache()
    now = int(time.time())

    # valid cache?
    if cached and now - cached.get("timestamp", 0) < CACHE_TTL:
        return cached["data"]

    url_now = _build_url("weather")
    url_fc = _build_url("forecast")

    if not url_now or not url_fc:
        return cached["data"] if cached else None

    now_json, fc_json = await asyncio.gather(
        _curl_json_async(url_now),
        _curl_json_async(url_fc),
    )

    if not now_json or not fc_json:
        return cached["data"] if cached else None

    # Extract data
    try:
        main = now_json["main"]
        weather0 = now_json["weather"][0]
        wind = now_json.get("wind", {})

        temp = round(main["temp"])
        feels = round(main["feels_like"])
        humidity = int(main["humidity"])
        wind_speed = float(wind.get("speed", 0.0))

        sunrise = now_json["sys"]["sunrise"]
        sunset = now_json["sys"]["sunset"]
        desc = weather0["description"].title()
        icon_code = weather0["icon"]

        # Forecast
        forecast_list = fc_json["list"][:4]
        forecast = []
        for entry in forecast_list:
            dt = datetime.fromtimestamp(entry["dt"])
            w0 = entry["weather"][0]
            forecast.append(
                {
                    "time": format_time_hm(dt),
                    "temp": round(entry["main"]["temp"]),
                    "icon": _map_icon(w0["icon"]),
                }
            )

        data = {
            "city": now_json["name"],
            "temp": temp,
            "desc": desc,
            "feels_like": feels,
            "humidity": humidity,
            "wind": wind_speed,
            "sunrise": sunrise,
            "sunset": sunset,
            "icon": _map_icon(icon_code),
            "icon_code": icon_code,
            "forecast": forecast,
            "moon_icon": moon_icon_for(datetime.now()),
        }

        _save_cache({"timestamp": int(time.time()), "data": data})
        return data

    except:
        return cached["data"] if cached else None
