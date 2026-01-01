import asyncio
from ignis import utils, widgets


class CaffeineWidget(widgets.Button):
    def __init__(self):
        self._enabled = True
        self._poll = None

        self._icon = widgets.Icon(
            pixel_size=22,
            css_classes=["caffeine-icon"],
        )

        super().__init__(
            css_classes=["caffeine-button"],
            child=self._icon,
            on_click=lambda x: self._toggle(),
        )

        asyncio.create_task(self._update_state())

        self._poll = utils.Poll(10000, lambda x: asyncio.create_task(self._update_state()))

        self.connect("destroy", self._cleanup)

    def _cleanup(self, *_):
        """Cleanup poll on destroy"""
        if self._poll:
            try:
                self._poll.cancel()
            except:
                pass
            self._poll = None

    async def _update_state(self):
        """Check if hypridle is running"""
        try:
            result = await utils.exec_sh_async("pgrep -x hypridle")
            self._enabled = result.returncode == 0
        except:
            self._enabled = False

        self._update_ui()
        return True

    def _update_ui(self):
        """Update icon and styling based on state"""
        if self._enabled:
            self._icon.image = "weather-clear-night-symbolic"
            self.remove_css_class("caffeine-active")
            self.set_tooltip_text("Idle timeout enabled\n\nClick to disable")
        else:
            self._icon.image = "my-caffeine-on-symbolic"
            self.add_css_class("caffeine-active")
            self.set_tooltip_text("Caffee mode active ☕\n\nClick to enable idle timeout")

    def _toggle(self):
        """Toggle hypridle on/off"""
        asyncio.create_task(self._toggle_async())

    async def _toggle_async(self):
        """Toggle hypridle state"""
        if self._enabled:
            await utils.exec_sh_async("hypridle_toggle")
        else:
            await utils.exec_sh_async("hypridle_toggle")
        await self._update_state()


def caffeine_widget():
    return CaffeineWidget()
