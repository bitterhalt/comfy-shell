import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ignis import utils, widgets

# ───────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────

DEFAULT_CITY_ID = "643492"
API_KEY_ENV = "OPEN_WEATHER_APIKEY"

CACHE_FILE = Path(os.path.expanduser("~/.cache/ignis/weather_cache.json"))
CACHE_TTL = 600  # seconds

# Time format: default 24h, enable 12h via env
USE_12H = os.getenv("IGNIS_WEATHER_12H", "").lower() in ("1", "true", "yes", "on")

# Base path for your custom SVG icons
ICON_BASE = os.path.expanduser("~/.config/ignis/assets/icons/weather")


# ───────────────────────────────────────────────
# CACHE HELPERS
# ───────────────────────────────────────────────


def _load_cache() -> Optional[Dict[str, Any]]:
    try:
        if not CACHE_FILE.exists():
            return None
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None


def _save_cache(data: Dict[str, Any]) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


# ───────────────────────────────────────────────
# TIME FORMAT HELPERS
# ───────────────────────────────────────────────


def _format_hour(dt: datetime) -> str:
    if USE_12H:
        return dt.strftime("%-I %p").lstrip("0")  # 12h
    return dt.strftime("%H")  # 24h hour


def _format_time_hm(dt: datetime) -> str:
    if USE_12H:
        return dt.strftime("%-I:%M %p").lstrip("0")
    return dt.strftime("%H:%M")  # 24h time


# ───────────────────────────────────────────────
# ICON HELPERS (custom SVGs)
# ───────────────────────────────────────────────


def _icon_path(name: str) -> str:
    """Return absolute path to a custom SVG icon."""
    return os.path.join(ICON_BASE, f"{name}.svg")


def _map_icon(code: str) -> str:
    """
    Map OpenWeather icon code → your custom SVG path.

    Example OpenWeather codes:
      01d, 01n = clear sky
      02d, 02n = few clouds
      03d, 03n, 04d, 04n = clouds
      09x, 10x = rain/drizzle
      11x = thunderstorm
      13x = snow
      50x = mist/fog
    """
    if not code:
        return _icon_path("not-available")

    base = code[:2]
    is_day = code.endswith("d")

    if base == "01":
        # clear sky (day/night)
        return _icon_path("clear-day" if is_day else "clear-night")
    if base == "02":
        # few / scattered clouds
        return _icon_path("partly-cloudy-day" if is_day else "partly-cloudy-night")
    if base in ("03", "04"):
        # broken / overcast clouds
        return _icon_path("cloudy")
    if base == "09":
        # shower rain
        return _icon_path("drizzle")
    if base == "10":
        # rain
        return _icon_path("rain")
    if base == "11":
        # thunderstorm
        return _icon_path("thunderstorms")
    if base == "13":
        # snow
        return _icon_path("snow")
    if base == "50":
        # mist / fog / haze
        return _icon_path("fog")

    return _icon_path("not-available")


# ───────────────────────────────────────────────
# OPENWEATHER FETCH
# ───────────────────────────────────────────────


def _build_url(endpoint: str) -> Optional[str]:
    api_key = os.getenv(API_KEY_ENV, "").strip()
    if not api_key:
        return None
    city_id = os.getenv("OPEN_WEATHER_CITY_ID", DEFAULT_CITY_ID).strip()
    base = "https://api.openweathermap.org/data/2.5"
    return f"{base}/{endpoint}?id={city_id}&units=metric&appid={api_key}"


async def _curl_json_async(url: str) -> Optional[Dict[str, Any]]:
    try:
        res = await utils.exec_sh_async(f"curl -sfL '{url}'")
    except Exception:
        return None

    if res.returncode != 0:
        return None

    try:
        return json.loads(res.stdout)
    except Exception:
        return None


async def fetch_weather_async() -> Optional[Dict[str, Any]]:
    """
    Fetch current + forecast weather, with cache.

    Returns dict:
      {
        "city": str,
        "temp": int,
        "desc": str,
        "feels_like": int,
        "humidity": int,
        "wind": float,
        "sunrise": int,
        "sunset": int,
        "icon": str,        # custom SVG path
        "icon_code": str,   # raw OpenWeather icon code
        "forecast": [
          {"time": "17:00", "temp": 6, "icon": str},
          ...
        ]
      }
    """
    cached = _load_cache()
    now_ts = int(time.time())

    # Use fresh cache if valid
    if cached and now_ts - cached.get("timestamp", 0) < CACHE_TTL:
        return cached.get("data")

    url_current = _build_url("weather")
    url_forecast = _build_url("forecast")
    if not url_current or not url_forecast:
        return cached.get("data") if cached else None

    current, forecast_json = await asyncio.gather(
        _curl_json_async(url_current),
        _curl_json_async(url_forecast),
    )

    if not current or not forecast_json:
        return cached.get("data") if cached else None

    try:
        city = current["name"]
        main = current["main"]
        weather0 = current["weather"][0] if current.get("weather") else {}
        wind = current.get("wind", {})

        temp = round(main.get("temp"))
        feels = round(main.get("feels_like"))
        humidity = int(main.get("humidity", 0))
        wind_speed = float(wind.get("speed", 0.0))
        sunrise = int(current["sys"]["sunrise"])
        sunset = int(current["sys"]["sunset"])
        desc = weather0.get("description", "").title()
        icon_code = weather0.get("icon", "")
        icon = _map_icon(icon_code)

        # Next ~4 forecast entries (3h steps)
        forecast_list = forecast_json.get("list", [])[:4]
        forecast: List[Dict[str, Any]] = []
        for item in forecast_list:
            dt = datetime.fromtimestamp(int(item["dt"]))
            t_label = _format_time_hm(dt)
            f_temp = round(item["main"]["temp"])
            fw = (item.get("weather") or [{}])[0]
            f_icon = _map_icon(fw.get("icon", ""))
            forecast.append({"time": t_label, "temp": f_temp, "icon": f_icon})

        data: Dict[str, Any] = {
            "city": city,
            "temp": temp,
            "desc": desc,
            "feels_like": feels,
            "humidity": humidity,
            "wind": wind_speed,
            "sunrise": sunrise,
            "sunset": sunset,
            "icon": icon,  # custom SVG path
            "icon_code": icon_code,
            "forecast": forecast,
        }

        _save_cache({"timestamp": now_ts, "data": data})
        return data
    except Exception:
        return cached.get("data") if cached else None


# ───────────────────────────────────────────────
# POPUP WINDOW
# ───────────────────────────────────────────────


class WeatherPopup(widgets.Window):
    """GNOME-style centered popup with custom SVG icons."""

    def __init__(self):
        # Top info: big icon + city + temp
        self._icon_label = widgets.Icon(
            image=_icon_path("cloudy"),  # fallback icon before data loads
            pixel_size=56,
            css_classes=["weather-main-icon"],
        )
        self._city_label = widgets.Label(label="—", css_classes=["weather-city"])
        self._temp_label = widgets.Label(label="--°C", css_classes=["weather-temp"])
        self._desc_label = widgets.Label(label="—", css_classes=["weather-desc"])
        self._extra_label = widgets.Label(label="—", css_classes=["weather-extra"])

        # Forecast row (centered)
        self._forecast_box = widgets.Box(
            spacing=16,
            halign="center",
            css_classes=["weather-forecast-row"],
        )

        # --- layout: big icon row (left) + text block (centered) ---

        header_top = widgets.Box(
            spacing=12,
            halign="start",
            hexpand=True,
            child=[self._icon_label, self._city_label, self._temp_label],
        )

        middle_column = widgets.Box(
            vertical=True,
            spacing=4,
            halign="center",
            hexpand=True,
            child=[
                self._desc_label,
                self._extra_label,
            ],
        )

        header = widgets.Box(
            vertical=True,
            spacing=10,
            hexpand=True,
            css_classes=["weather-header"],
            child=[
                header_top,
                middle_column,
            ],
        )

        popup_box = widgets.Box(
            vertical=True,
            spacing=18,
            css_classes=["weather-popup"],
            child=[header, self._forecast_box],
        )

        # Slide-down revealer animation
        self._revealer = widgets.Revealer(
            child=popup_box,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        centered_box = widgets.Box(
            valign="start",
            halign="center",
            css_classes=["weather-container"],
            child=[self._revealer],
        )

        # Fullscreen click-to-close overlay
        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["weather-overlay"],
            on_click=lambda *_: toggle_weather_popup(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_btn,
            overlays=[centered_box],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_WEATHER",
            layer="top",
            popup=True,
            kb_mode="on_demand",
            css_classes=["weather-window"],
            child=root_overlay,
        )

        self._last_data: Optional[Dict[str, Any]] = None
        utils.Poll(CACHE_TTL * 1000, lambda *_: self._update_weather())

    # ───────────────────────────────────────────
    # Public
    # ───────────────────────────────────────────

    def toggle(self):
        if not self.visible:
            self.visible = True
            self._update_weather()
            utils.Timeout(10, lambda: setattr(self._revealer, "reveal_child", True))
        else:
            self._revealer.reveal_child = False
            utils.Timeout(
                self._revealer.transition_duration,
                lambda: setattr(self, "visible", False),
            )

    def get_last_data(self) -> Optional[Dict[str, Any]]:
        return self._last_data

    # ───────────────────────────────────────────
    # Internal update plumbing
    # ───────────────────────────────────────────

    def _update_weather(self):
        asyncio.create_task(self._update_weather_async())
        return True

    async def _update_weather_async(self):
        data = await fetch_weather_async()
        if not data:
            return

        self._last_data = data

        sunrise_dt = datetime.fromtimestamp(data["sunrise"])
        sunset_dt = datetime.fromtimestamp(data["sunset"])
        sunrise = _format_time_hm(sunrise_dt)
        sunset = _format_time_hm(sunset_dt)

        self._city_label.label = data["city"]
        self._temp_label.label = f"{data['temp']}°C"
        self._desc_label.label = data["desc"]
        self._icon_label.image = data["icon"]
        self._extra_label.label = (
            f"Feels like {data['feels_like']}°C  •  "
            f"Humidity {data['humidity']}%  •  "
            f"Wind {data['wind']:.1f} m/s"
        )

        items: List[widgets.Widget] = []

        # Forecast items
        for item in data.get("forecast", []):
            items.append(
                widgets.Box(
                    vertical=True,
                    halign="center",
                    spacing=4,
                    css_classes=["weather-forecast-item"],
                    child=[
                        widgets.Label(
                            label=item["time"],
                            css_classes=["weather-forecast-time"],
                        ),
                        widgets.Icon(
                            image=item["icon"],  # custom SVG path
                            pixel_size=40,
                            css_classes=["weather-forecast-icon"],
                        ),
                        widgets.Label(
                            label=f"{item['temp']}°C",
                            css_classes=["weather-forecast-temp"],
                        ),
                    ],
                )
            )

        # Sunrise
        items.append(
            widgets.Box(
                vertical=True,
                halign="center",
                spacing=4,
                css_classes=["weather-forecast-item"],
                child=[
                    widgets.Label(
                        label="Sunrise",
                        css_classes=["weather-forecast-time"],
                    ),
                    widgets.Icon(
                        image=_icon_path("sunrise"),
                        pixel_size=40,
                        css_classes=["weather-forecast-icon"],
                    ),
                    widgets.Label(
                        label=sunrise,
                        css_classes=["weather-forecast-temp"],
                    ),
                ],
            )
        )

        # Sunset
        items.append(
            widgets.Box(
                vertical=True,
                halign="center",
                spacing=4,
                css_classes=["weather-forecast-item"],
                child=[
                    widgets.Label(
                        label="Sunset",
                        css_classes=["weather-forecast-time"],
                    ),
                    widgets.Icon(
                        image=_icon_path("sunset"),
                        pixel_size=40,
                        css_classes=["weather-forecast-icon"],
                    ),
                    widgets.Label(
                        label=sunset,
                        css_classes=["weather-forecast-temp"],
                    ),
                ],
            )
        )

        self._forecast_box.child = items


# ───────────────────────────────────────────────
# GLOBAL INSTANCE
# ───────────────────────────────────────────────

_weather_popup: Optional[WeatherPopup] = None


def get_weather_popup() -> WeatherPopup:
    global _weather_popup
    if _weather_popup is None:
        _weather_popup = WeatherPopup()
    return _weather_popup


def toggle_weather_popup():
    get_weather_popup().toggle()
