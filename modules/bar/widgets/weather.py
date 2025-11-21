import asyncio

from ignis import utils, widgets
from modules.weather.weather_window import (
    fetch_weather_async,
    get_weather_popup,
    toggle_weather_popup,
)


class WeatherBarWidget(widgets.Button):
    """Small bar widget: icon + temperature."""

    def __init__(self):
        self._icon = widgets.Icon(
            image="weather-clouds-symbolic",
            pixel_size=18,
            css_classes=["bar-weather-icon"],
        )
        self._temp = widgets.Label(
            label="--°",
            css_classes=["bar-weather-temp"],
        )

        inner = widgets.Box(
            spacing=4,
            css_classes=["bar-weather"],
            child=[self._icon, self._temp],
        )

        super().__init__(
            child=inner,
            css_classes=["bar-weather-button"],
            on_click=lambda *_: toggle_weather_popup(),
        )

        self._update()
        utils.Poll(600000, lambda *_: self._update())

    def _update(self):
        asyncio.create_task(self._update_async())
        return True

    async def _update_async(self):
        popup = get_weather_popup()
        data = popup.get_last_data() or await fetch_weather_async()
        if not data:
            return
        self._icon.image = data["icon"]
        self._temp.label = f"{data['temp']}°"


def weather_widget():
    return WeatherBarWidget()
