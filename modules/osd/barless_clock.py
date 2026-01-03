import datetime
from ignis import widgets
from settings import config
from ignis.window_manager import WindowManager

wm = WindowManager.get_default()
_clock_window = None
_bar_visible = True


class BarlessClockWindow(widgets.Window):
    """Large clock display for barless mode - no separate poll needed"""

    def __init__(self):
        self._time_label = widgets.Label(
            css_classes=["barless-clock-time"],
        )

        self._date_label = widgets.Label(
            css_classes=["barless-clock-date"],
        )

        content = widgets.Box(
            vertical=True,
            spacing=8,
            css_classes=["barless-clock"],
            child=[self._time_label, self._date_label],
        )

        super().__init__(
            monitor=config.ui.primary_monitor,
            layer="background",
            anchor=["top", "right"],
            namespace="ignis_BARLESS_CLOCK",
            visible=False,
            css_classes=["barless-clock-window"],
            child=content,
        )

        self.update_time()
        self.connect("notify::visible", lambda *_: self.update_time() if self.visible else None)

    def update_time(self):
        """Update time and date labels - called by external poll"""
        now = datetime.datetime.now()
        self._time_label.label = now.strftime("%H:%M")
        self._date_label.label = now.strftime("%A, %d %B")


def init_barless_clock():
    """Initialize barless clock"""
    global _clock_window
    if _clock_window is None:
        _clock_window = BarlessClockWindow()
    return _clock_window


def update_barless_clock():
    """Update barless clock time - called by bar clock poll"""
    global _clock_window
    if _clock_window is not None and _clock_window.visible:
        _clock_window.update_time()


def set_barless_clock_visibility(bar_visible: bool):
    """Show/hide clock based on bar visibility"""
    global _bar_visible, _clock_window
    _bar_visible = bar_visible

    if _clock_window is None:
        return

    _clock_window.visible = not bar_visible
