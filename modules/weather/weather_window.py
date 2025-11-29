import asyncio
from datetime import datetime
from typing import List, Optional

from ignis import utils, widgets

from .weather_data import fetch_weather_async, format_time_hm, icon_path

CACHE_TTL = 600


class WeatherPopup(widgets.Window):

    def __init__(self):
        # ────────────────────────────────
        # Header: big icon + city + temp
        # ────────────────────────────────
        self._icon_label = widgets.Icon(
            image=icon_path("cloudy"),
            pixel_size=56,
            css_classes=["weather-main-icon"],
        )

        self._city_label = widgets.Label(label="—", css_classes=["weather-city"])
        self._temp_label = widgets.Label(label="--°C", css_classes=["weather-temp"])
        self._desc_label = widgets.Label(label="—", css_classes=["weather-desc"])
        self._extra_label = widgets.Label(label="—", css_classes=["weather-extra"])

        # Moon emoji (label, not icon)
        self._moon_label = widgets.Label(
            label="🌕",
            css_classes=["weather-moon-emoji"],
        )

        # Forecast row
        self._forecast_box = widgets.Box(
            spacing=16,
            halign="center",
            css_classes=["weather-forecast-row"],
        )

        # ────────────────────────────────
        # Layout structure
        # ────────────────────────────────
        left_row = widgets.Box(
            spacing=12,
            halign="start",
            hexpand=True,
            child=[self._icon_label, self._city_label, self._temp_label],
        )

        header_top = widgets.Box(
            spacing=12,
            halign="fill",
            hexpand=True,
            child=[left_row, self._moon_label],
        )

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

        #  static content
        centered = widgets.Box(
            valign="start",
            halign="center",
            css_classes=["weather-container"],
            child=[popup_box],
        )

        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["weather-overlay"],
            on_click=lambda *_: toggle_weather_popup(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_btn,
            overlays=[centered],
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

        # keep last data + prevent GC of task
        self._last_data: Optional[dict] = None
        self._update_task = None

        utils.Poll(CACHE_TTL * 1000, lambda *_: self._update_weather())

    # ──────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────
    def toggle(self):
        if not self.visible:
            self.visible = True
            self._update_weather()
        else:
            self.visible = False

    def get_last_data(self):
        return self._last_data

    # ──────────────────────────────────────────────────────────
    # DATA UPDATES
    # ──────────────────────────────────────────────────────────
    def _update_weather(self):
        # keep reference so task won't be GC'd
        self._update_task = asyncio.create_task(self._update_weather_async())
        return True

    async def _update_weather_async(self):
        data = await fetch_weather_async()
        if not data:
            return

        self._last_data = data

        # update header
        self._icon_label.image = data["icon"]
        self._city_label.label = data["city"]
        self._temp_label.label = f"{data['temp']}°C"
        self._desc_label.label = data["desc"]
        self._extra_label.label = (
            f"Feels like {data['feels_like']}°C  •  "
            f"Humidity {data['humidity']}%  •  "
            f"Wind {data['wind']:.1f} m/s"
        )

        # moon emoji + tooltip
        if moon := data.get("moon_icon"):
            self._moon_label.label = moon
        if tip := data.get("moon_tooltip"):
            self._moon_label.set_tooltip_text(tip)

        # forecast items
        items: List[widgets.Widget] = []

        # hourly forecast
        for it in data["forecast"]:
            items.append(
                widgets.Box(
                    vertical=True,
                    halign="center",
                    spacing=4,
                    css_classes=["weather-forecast-item"],
                    child=[
                        widgets.Label(
                            label=it["time"], css_classes=["weather-forecast-time"]
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

        # sunrise / sunset
        sunrise_str = format_time_hm(datetime.fromtimestamp(data["sunrise"]))
        sunset_str = format_time_hm(datetime.fromtimestamp(data["sunset"]))

        items.append(
            widgets.Box(
                vertical=True,
                halign="center",
                spacing=4,
                css_classes=["weather-forecast-item"],
                child=[
                    widgets.Label(
                        label="Sunrise", css_classes=["weather-forecast-time"]
                    ),
                    widgets.Icon(
                        image=icon_path("sunrise"),
                        pixel_size=40,
                        css_classes=["weather-forecast-icon"],
                    ),
                    widgets.Label(
                        label=sunrise_str, css_classes=["weather-forecast-temp"]
                    ),
                ],
            )
        )

        items.append(
            widgets.Box(
                vertical=True,
                halign="center",
                spacing=4,
                css_classes=["weather-forecast-item"],
                child=[
                    widgets.Label(
                        label="Sunset", css_classes=["weather-forecast-time"]
                    ),
                    widgets.Icon(
                        image=icon_path("sunset"),
                        pixel_size=40,
                        css_classes=["weather-forecast-icon"],
                    ),
                    widgets.Label(
                        label=sunset_str, css_classes=["weather-forecast-temp"]
                    ),
                ],
            )
        )

        self._forecast_box.child = items


# ──────────────────────────────────────────────────────────────
# SINGLETON API
# ──────────────────────────────────────────────────────────────

# Example for weather popup
_weather_popup = None


def toggle_weather_popup():
    global _weather_popup

    if _weather_popup is not None and _weather_popup.visible:
        # Close and destroy
        _weather_popup.close()
        _weather_popup = None
    else:
        # Create new instance
        _weather_popup = WeatherPopup()
        _weather_popup.visible = True
