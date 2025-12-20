from ignis import utils, widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService

hypr = HyprlandService.get_default()
niri = NiriService.get_default()

TITLE_EXCEPTIONS = ["firefox", "zen"]


def window_title(monitor_name: str):
    # ───────────────────────────────────────────────────────────────
    # LABEL
    # ───────────────────────────────────────────────────────────────

    if hypr.is_available:
        title_label = widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=42,
        )
    elif niri.is_available:
        title_label = widgets.Label(
            css_classes=["window-title"],
            ellipsize="end",
            max_width_chars=42,
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
    # ICON + LABEL UPDATE LOGIC
    # ───────────────────────────────────────────────────────────────

    def update_display(*_):
        """Update icon and label based on active window's class/app_id"""
        try:
            if hypr.is_available:
                win = hypr.active_window

                if not win or win.address == "0x0" or not win.initial_class:
                    icon.set_visible(False)
                    title_label.set_label("")
                    return

                win_class = win.initial_class
                win_title = win.title

            elif niri.is_available:
                win = niri.active_window

                if not win or not win.app_id:
                    icon.set_visible(False)
                    title_label.set_label("")
                    return

                win_class = win.app_id
                win_title = win.title

            else:
                return

            # --- CONDITIONAL LABEL LOGIC ---
            if win_class.lower() in TITLE_EXCEPTIONS:
                display_text = win_title
            else:
                display_text = win_class

            title_label.set_label(display_text)

            # --- ICON LOGIC  ---
            icon_name = utils.get_app_icon_name(win_class)

            if icon_name:
                icon.image = icon_name
                icon.set_visible(True)
            else:
                icon.set_visible(False)

        except Exception:
            icon.set_visible(False)
            title_label.set_label("")

    update_display()

    # ───────────────────────────────────────────────────────────────
    # CONNECT SIGNALS
    # ───────────────────────────────────────────────────────────────

    if hypr.is_available:
        hypr.active_window.connect("notify::initial-class", update_display)
        hypr.active_window.connect("notify::title", update_display)
        hypr.connect("notify::active-workspace", update_display)

    elif niri.is_available:
        niri.active_window.connect("notify::app-id", update_display)
        niri.active_window.connect("notify::title", update_display)
        niri.connect("notify::active-workspace", update_display)

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
