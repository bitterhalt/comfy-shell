from ignis import widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService

hypr = HyprlandService.get_default()
niri = NiriService.get_default()


def window_title(monitor_name: str):
    if hypr.is_available:
        return widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=40,
            label=hypr.active_window.bind("title"),
        )
    elif niri.is_available:
        return widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=40,
            visible=niri.bind("active_output", lambda o: o == monitor_name),
            label=niri.active_window.bind("title"),
        )
    return widgets.Label(css_classes=["window-title"], label="No window")
