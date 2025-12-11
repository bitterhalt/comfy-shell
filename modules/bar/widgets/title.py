from ignis import utils, widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService

hypr = HyprlandService.get_default()
niri = NiriService.get_default()


def window_title(monitor_name: str):
    # ───────────────────────────────────────────────────────────────
    # TITLE LABEL
    # ───────────────────────────────────────────────────────────────

    if hypr.is_available:
        title_label = widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=42,
            label=hypr.active_window.bind("title"),
        )
    elif niri.is_available:
        title_label = widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=42,
            label=niri.active_window.bind("title"),
            visible=niri.bind("active_output", lambda o: o == monitor_name),
        )
    else:
        title_label = widgets.Label(
            css_classes=["window-title"],
            label="No compositor",
        )
        return widgets.Box(
            spacing=6,
            halign="start",
            valign="center",
            css_classes=["window-title-box"],
            child=[title_label],
        )

    # ───────────────────────────────────────────────────────────────
    # WINDOW ICON
    # ───────────────────────────────────────────────────────────────

    icon = widgets.Icon(
        pixel_size=22,
        css_classes=["window-title-icon"],
        visible=False,
        image="application-x-executable-symbolic",
    )

    # ───────────────────────────────────────────────────────────────
    # ICON UPDATE LOGIC
    # ───────────────────────────────────────────────────────────────

    def update_icon(*_):
        """Update icon based on active window's app_id/class"""
        try:
            if hypr.is_available:
                win = hypr.active_window

                if not win or win.address == "0x0" or not win.class_name:
                    icon.set_visible(False)
                    return

                app_id = win.class_name

            elif niri.is_available:
                win = niri.active_window

                if not win or not win.app_id:
                    icon.set_visible(False)
                    return

                app_id = win.app_id

            else:
                icon.set_visible(False)
                return

            icon_name = utils.get_app_icon_name(app_id)

            if icon_name:
                icon.image = icon_name
                icon.set_visible(True)
            else:
                icon.set_visible(False)

        except Exception as e:
            icon.set_visible(False)

    update_icon()

    # ───────────────────────────────────────────────────────────────
    # CONNECT SIGNALS
    # ───────────────────────────────────────────────────────────────

    if hypr.is_available:
        hypr.active_window.connect("notify::class-name", update_icon)
        hypr.active_window.connect("notify::title", update_icon)
        hypr.connect("notify::active-workspace", update_icon)

    elif niri.is_available:
        niri.active_window.connect("notify::app-id", update_icon)
        niri.active_window.connect("notify::title", update_icon)
        niri.connect("notify::active-workspace", update_icon)

    # ───────────────────────────────────────────────────────────────
    # FINAL LAYOUT
    # ───────────────────────────────────────────────────────────────

    return widgets.Box(
        spacing=6,
        halign="start",
        valign="center",
        css_classes=["window-title-box"],
        child=[icon, title_label],
    )
