import datetime

from ignis import utils, widgets

_time_osd_window = None


class TimeOsdWindow(widgets.Window):
    def __init__(self):
        self._timeout = None

        self._time_label = widgets.Label(
            css_classes=["time-osd-label"],
        )

        icon = widgets.Icon(
            image="clock-applet-symbolic",
            pixel_size=24,
            css_classes=["time-osd-icon"],
        )

        row = widgets.Box(
            spacing=12,
            child=[icon, self._time_label],
        )

        # PILL
        pill = widgets.Box(
            css_classes=["time-osd"],
            child=[row],
        )

        super().__init__(
            layer="overlay",
            anchor=["top", "right"],
            namespace="ignis_TIME_OSD",
            visible=False,
            css_classes=["time-osd-window"],
            child=pill,
        )

        self.connect("notify::visible", self._on_visible_changed)

    def _on_visible_changed(self, *_):
        if self.visible:
            now = datetime.datetime.now()
            self._time_label.set_label(now.strftime("%d.%m  %H:%M"))

            if self._timeout:
                self._timeout.cancel()

            self._timeout = utils.Timeout(8000, lambda: setattr(self, "visible", False))

        else:
            if self._timeout:
                self._timeout.cancel()
                self._timeout = None

    def show_osd(self):
        self.visible = True


def init_time_osd():
    global _time_osd_window
    if _time_osd_window is None:
        _time_osd_window = TimeOsdWindow()
    return _time_osd_window


def toggle_time_osd():
    win = init_time_osd()
    win.show_osd()
