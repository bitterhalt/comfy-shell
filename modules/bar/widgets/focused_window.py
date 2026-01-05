from ignis import utils, widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService
from settings import config

hypr = HyprlandService.get_default()
niri = NiriService.get_default()


def _get_window_text(window, compositor: str) -> str:
    """Get display text for window based on compositor and config"""
    if not window:
        return ""

    if compositor == "hyprland":
        if not window.initial_class or window.address == "0x0":
            return ""

        win_class = window.initial_class
        win_title = window.title or ""

        if win_class.lower() in config.ui.bar_window_title_exceptions:
            return win_title
        return win_class

    elif compositor == "niri":
        if not window.app_id:
            return ""

        win_class = window.app_id
        win_title = window.title or ""

        if win_class.lower() in config.ui.bar_window_title_exceptions:
            return win_title
        return win_class

    return ""


def _get_window_icon(window, compositor: str) -> str:
    """Get icon name for window based on compositor"""
    if not window:
        return "application-x-executable-symbolic"

    if compositor == "hyprland":
        if not window.initial_class or window.address == "0x0":
            return "application-x-executable-symbolic"
        win_class = window.initial_class

    elif compositor == "niri":
        if not window.app_id:
            return "application-x-executable-symbolic"
        win_class = window.app_id
    else:
        return "application-x-executable-symbolic"

    icon_name = utils.get_app_icon_name(win_class)
    return icon_name if icon_name else "application-x-executable-symbolic"


def _should_show_icon(window, compositor: str) -> bool:
    """Determine if icon should be visible"""
    if not window:
        return False

    if compositor == "hyprland":
        return bool(window.initial_class and window.address != "0x0")
    elif compositor == "niri":
        return bool(window.app_id)

    return False


def window_title(monitor_name: str):
    """Window title widget with direct binding to prevent artifacts"""

    if hypr.is_available:
        icon = widgets.Icon(
            pixel_size=22,
            css_classes=["window-title-icon"],
            image=hypr.bind(
                "active_window",
                transform=lambda win: _get_window_icon(win, "hyprland"),
            ),
            visible=hypr.bind(
                "active_window",
                transform=lambda win: _should_show_icon(win, "hyprland"),
            ),
        )

        title_label = widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=42,
            halign="start",
            label=hypr.bind(
                "active_window",
                transform=lambda win: _get_window_text(win, "hyprland"),
            ),
        )

    elif niri.is_available:
        icon = widgets.Icon(
            pixel_size=22,
            css_classes=["window-title-icon"],
            image=niri.bind(
                "active_window",
                transform=lambda win: _get_window_icon(win, "niri"),
            ),
            visible=niri.bind(
                "active_window",
                transform=lambda win: _should_show_icon(win, "niri") and niri.active_output == monitor_name,
            ),
        )

        title_label = widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=42,
            halign="start",
            label=niri.bind(
                "active_window",
                transform=lambda win: _get_window_text(win, "niri"),
            ),
            visible=niri.bind(
                "active_output",
                transform=lambda output: output == monitor_name,
            ),
        )

    box = widgets.Box(
        spacing=10,
        halign="start",
        valign="center",
        css_classes=["window-title-box"],
        child=[icon, title_label],
    )

    return box
