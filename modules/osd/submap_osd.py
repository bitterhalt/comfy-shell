"""
Submap OSD - Display only (controlled by bash watcher)
No async tasks = No zombies!
"""

from ignis import widgets
from ignis.services.hyprland import HyprlandService

hypr = HyprlandService.get_default()
_osd_window = None


class SubmapOSD(widgets.Window):
    """Minimal submap indicator OSD"""

    def __init__(self):
        # UI
        self._label = widgets.Label(css_classes=["submap-osd-label"])
        self._icon = widgets.Icon(
            image="input-keyboard-symbolic",
            pixel_size=24,
            css_classes=["submap-osd-icon"],
        )

        content = widgets.Box(
            css_classes=["submap-osd"],
            spacing=12,
            child=[self._icon, self._label],
        )

        super().__init__(
            layer="overlay",
            anchor=["top"],
            namespace="ignis_SUBMAP_OSD",
            visible=False,
            css_classes=["submap-osd-window"],
            child=content,
        )


def init_submap_osd():
    """Initialize the OSD window"""
    global _osd_window
    if _osd_window is None and hypr.is_available:
        _osd_window = SubmapOSD()


def show_submap_osd(message: str):
    """Show submap OSD (called via ignis run-command from bash watcher)"""
    if _osd_window:
        _osd_window._icon.set_from_icon_name("input-keyboard-symbolic")
        _osd_window._label.set_label(message.upper())
        _osd_window.visible = True


def hide_submap_osd():
    """Hide the OSD"""
    if _osd_window:
        _osd_window.visible = False
