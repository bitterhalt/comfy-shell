"""
Weather pill widget for integrated center
"""

import asyncio

from ignis import utils, widgets
from ignis.window_manager import WindowManager

wm = WindowManager.get_default()


class WeatherPill:
    """Compact weather display that opens full weather popup on click"""

    def __init__(self):
        # Weather icon
        self._weather_icon = widgets.Icon(
            image="weather-clouds-symbolic",
            pixel_size=32,
        )

        # Temperature
        self._weather_temp = widgets.Label(
            label="--°",
            css_classes=["weather-temp-compact"],
        )

        # Description
        self._weather_desc = widgets.Label(
            label="…",
            css_classes=["weather-desc-compact"],
            ellipsize="end",
            max_width_chars=20,
        )

        # Clickable button
        self.button = widgets.Button(
            css_classes=["weather-compact"],
            on_click=lambda x: self._open_weather_popup(),
            child=widgets.Box(
                spacing=10,
                child=[self._weather_icon, self._weather_temp, self._weather_desc],
            ),
        )

        # Initial update
        self.update()

        # Periodic refresh (every 10 minutes)
        utils.Poll(600000, lambda *_: self.update())

    def update(self):
        """Update weather data"""
        asyncio.create_task(self._update_async())
        return True

    async def _update_async(self):
        """Async weather update"""
        from modules.weather.weather_data import fetch_weather_async

        data = await fetch_weather_async()
        if not data:
            return

        self._weather_icon.image = data["icon"]
        self._weather_temp.label = f"{data['temp']}°"
        self._weather_desc.label = data["desc"]

        tooltip = (
            f"{data['city']}\n"
            f"Feels like {data['feels_like']}°C\n"
            f"Humidity: {data['humidity']}%\n"
            f"Wind: {data['wind']:.1f} m/s\n"
            "\nClick to open weather details"
        )
        self._weather_icon.set_tooltip_text(tooltip)

    def _open_weather_popup(self):
        """Open the weather popup window"""
        wm.close_window("ignis_INTEGRATED_CENTER")
        wm.open_window("ignis_WEATHER")
