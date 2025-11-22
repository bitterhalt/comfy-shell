import asyncio
from datetime import datetime
from typing import List, Optional

from ignis import utils, widgets

# Reuse helpers + data fetcher from weather_data.py
from .weather_data import fetch_weather_async, format_time_hm, icon_path

# Same TTL as in weather_data
CACHE_TTL = 600


class WeatherPopup(widgets.Window):
    """GNOME-style centered popup (UI only, uses weather_data)."""

    def __init__(self):
        # ── Top info: big icon + city + temp ────────────────────────
        self._icon_label = widgets.Icon(
            image=icon_path("cloudy"),  # fallback before data loads
            pixel_size=56,
            css_classes=["weather-main-icon"],
        )
        self._city_label = widgets.Label(label="—", css_classes=["weather-city"])
        self._temp_label = widgets.Label(label="--°C", css_classes=["weather-temp"])
        self._desc_label = widgets.Label(label="—", css_classes=["weather-desc"])
        self._extra_label = widgets.Label(label="—", css_classes=["weather-extra"])

        # Moon emoji (top-right) - CHANGED: Label instead of Icon for emoji
        self._moon_label = widgets.Label(
            label="🌕",  # fallback emoji
            css_classes=["weather-moon-emoji"],
        )

        # Forecast row (bottom)
        self._forecast_box = widgets.Box(
            spacing=16,
            halign="center",
            css_classes=["weather-forecast-row"],
        )

        # ── Layout ──────────────────────────────────────────────────

        # Left side: big icon + city + temp
        left_row = widgets.Box(
            spacing=12,
            halign="start",
            hexpand=True,
            child=[self._icon_label, self._city_label, self._temp_label],
        )

        # Top header row: left block + moon emoji on the right
        header_top = widgets.Box(
            spacing=12,
            halign="fill",
            hexpand=True,
            child=[left_row, self._moon_label],
        )

        # Middle text (centered): description + extra line
        middle_column = widgets.Box(
            vertical=True,
            spacing=4,
            halign="center",
            hexpand=True,
            child=[self._desc_label, self._extra_label],
        )

        header = widgets.Box(
            vertical=True,
            spacing=10,
            hexpand=True,
            css_classes=["weather-header"],
            child=[header_top, middle_column],
        )

        popup_box = widgets.Box(
            vertical=True,
            spacing=18,
            css_classes=["weather-popup"],
            child=[header, self._forecast_box],
        )

        # Slide-down revealer
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
            anchor=["top", "left", "right", "bottom"],
            namespace="ignis_WEATHER",
            layer="top",
            popup=True,
            kb_mode="on_demand",
            css_classes=["weather-window"],
            child=root_overlay,
        )

        self._last_data: Optional[dict] = None
        self._update_task = None  # ← ADDED: Track the update task
        utils.Poll(CACHE_TTL * 1000, lambda *_: self._update_weather())

    # ── Public API (used by bar widget) ─────────────────────────────

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

    def get_last_data(self):
        return self._last_data

    # ── Internal plumbing ──────────────────────────────────────────

    def _update_weather(self):
        # FIXED: Store task reference to prevent garbage collection
        self._update_task = asyncio.create_task(self._update_weather_async())
        return True

    async def _update_weather_async(self):
        data = await fetch_weather_async()
        if not data:
            return

        self._last_data = data

        # Header data
        self._icon_label.image = data["icon"]
        self._city_label.label = data["city"]
        self._temp_label.label = f"{data['temp']}°C"
        self._desc_label.label = data["desc"]
        self._extra_label.label = (
            f"Feels like {data['feels_like']}°C  •  "
            f"Humidity {data['humidity']}%  •  "
            f"Wind {data['wind']:.1f} m/s"
        )

        # FIXED: Moon emoji with tooltip
        moon_emoji = data.get("moon_icon")
        moon_tip = data.get("moon_tooltip")
        if moon_emoji:
            self._moon_label.label = moon_emoji
        if moon_tip:
            self._moon_label.set_tooltip_text(moon_tip)

        # Sunrise / sunset strings
        sunrise_str = format_time_hm(datetime.fromtimestamp(data["sunrise"]))
        sunset_str = format_time_hm(datetime.fromtimestamp(data["sunset"]))

        items: List[widgets.Widget] = []

        # Forecast items (bottom row)
        for it in data["forecast"]:
            items.append(
                widgets.Box(
                    vertical=True,
                    halign="center",
                    spacing=4,
                    css_classes=["weather-forecast-item"],
                    child=[
                        widgets.Label(
                            label=it["time"],
                            css_classes=["weather-forecast-time"],
                        ),
                        widgets.Icon(
                            image=it["icon"],
                            pixel_size=40,
                            css_classes=["weather-forecast-icon"],
                        ),
                        widgets.Label(
                            label=f"{it['temp']}°C",
                            css_classes=["weather-forecast-temp"],
                        ),
                    ],
                )
            )

        # Sunrise block
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
                        image=icon_path("sunrise"),
                        pixel_size=40,
                        css_classes=["weather-forecast-icon"],
                    ),
                    widgets.Label(
                        label=sunrise_str,
                        css_classes=["weather-forecast-temp"],
                    ),
                ],
            )
        )

        # Sunset block
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
                        image=icon_path("sunset"),
                        pixel_size=40,
                        css_classes=["weather-forecast-icon"],
                    ),
                    widgets.Label(
                        label=sunset_str,
                        css_classes=["weather-forecast-temp"],
                    ),
                ],
            )
        )

        self._forecast_box.child = items


# ── Singleton API used by bar widget ──────────────────────────────

_weather_popup: Optional[WeatherPopup] = None


def get_weather_popup() -> WeatherPopup:
    global _weather_popup
    if _weather_popup is None:
        _weather_popup = WeatherPopup()
    return _weather_popup


def toggle_weather_popup():
    get_weather_popup().toggle()
