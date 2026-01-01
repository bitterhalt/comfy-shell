from ignis import utils, widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService
from modules.utils.signal_manager import SignalManager
from settings import config

hypr = HyprlandService.get_default()
niri = NiriService.get_default()


def window_title(monitor_name: str):
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

    icon = widgets.Icon(
        pixel_size=22,
        css_classes=["window-title-icon"],
        visible=False,
        image="application-x-executable-symbolic",
    )

    box = widgets.Box(
        spacing=10,
        halign="start",
        valign="center",
        css_classes=["window-title-box"],
        child=[icon, title_label],
    )

    compositor_signals = SignalManager()
    window_signals = SignalManager()
    current = {"win": None}

    def update_display(*_):
        try:
            if hypr.is_available:
                win = current["win"]
                if not win or win.address == "0x0" or not win.initial_class:
                    icon.visible = False
                    title_label.label = ""
                    return

                win_class = win.initial_class
                win_title = win.title

            elif niri.is_available:
                win = current["win"]
                if not win or not win.app_id:
                    icon.visible = False
                    title_label.label = ""
                    return

                win_class = win.app_id
                win_title = win.title

            else:
                return

            title_label.label = win_title if win_class.lower() in config.ui.bar_window_title_exceptions else win_class

            icon_name = utils.get_app_icon_name(win_class)
            if icon_name:
                icon.image = icon_name
                icon.visible = True
            else:
                icon.visible = False

        except Exception:
            icon.visible = False
            title_label.label = ""

    def rewire_active_window(*_):
        if hypr.is_available:
            win = hypr.active_window
        elif niri.is_available:
            win = niri.active_window
        else:
            win = None

        if win is current["win"]:
            update_display()
            return

        window_signals.disconnect_all()
        current["win"] = win

        if not win:
            update_display()
            return

        if hypr.is_available:
            window_signals.connect(win, "notify::initial-class", update_display)
            window_signals.connect(win, "notify::title", update_display)
        elif niri.is_available:
            window_signals.connect(win, "notify::app-id", update_display)
            window_signals.connect(win, "notify::title", update_display)

        update_display()

    if hypr.is_available:
        compositor_signals.connect(hypr, "notify::active-window", rewire_active_window)
        compositor_signals.connect(hypr, "notify::active-workspace", rewire_active_window)
    elif niri.is_available:
        compositor_signals.connect(niri, "notify::active-window", rewire_active_window)
        compositor_signals.connect(niri, "notify::active-workspace", rewire_active_window)

    compositor_signals.connect(
        box,
        "destroy",
        lambda *_: (
            window_signals.disconnect_all(),
            compositor_signals.disconnect_all(),
        ),
    )

    rewire_active_window()
    return box
