import asyncio
import os

from gi.repository import Gdk, Gtk

from ignis import utils, widgets
from ignis.window_manager import WindowManager
from settings import config

wm = WindowManager.get_default()

# Configuration from settings
TERMINAL = config.terminal
FILE_OPENER = config.file_opener

# Settings definitions
SETTINGS = [
    {
        "name": "Hyprland",
        "path": "~/.config/hypr/",
        "icon": "preferences-system-symbolic",
        "command": f"{TERMINAL} -e {FILE_OPENER}",
    },
    {
        "name": "Ignis",
        "path": "~/.config/ignis/",
        "icon": "applications-system-symbolic",
        "command": f"{TERMINAL} -e {FILE_OPENER}",
    },
    {
        "name": "Neovim",
        "path": "~/.config/nvim/",
        "icon": "text-editor-symbolic",
        "command": f"{TERMINAL} -e {FILE_OPENER}",
    },
]


class SettingItem(widgets.Button):
    """Individual setting item button"""

    def __init__(self, setting: dict):
        self._setting = setting
        path = os.path.expanduser(setting["path"])

        super().__init__(
            css_classes=["setting-item", "unset"],
            on_click=lambda *_: self._open(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Icon(
                        image=setting.get("icon", "folder-symbolic"),
                        pixel_size=32,
                    ),
                    widgets.Box(
                        vertical=True,
                        spacing=2,
                        hexpand=True,
                        child=[
                            widgets.Label(
                                label=setting["name"],
                                halign="start",
                                css_classes=["setting-name"],
                            ),
                            widgets.Label(
                                label=path,
                                halign="start",
                                ellipsize="end",
                                css_classes=["setting-path"],
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _open(self):
        path = os.path.expanduser(self._setting["path"])
        command = f"{self._setting['command']} {path}"
        asyncio.create_task(utils.exec_sh_async(f"{command} &"))
        wm.close_window("ignis_SETTINGS_MANAGER")


class SettingsManager(widgets.Window):
    """Static settings manager (no search, keyboard only)"""

    def __init__(self):
        # Results list (static)
        self._results = widgets.Box(
            vertical=True,
            css_classes=["settings-results"],
            child=[SettingItem(s) for s in SETTINGS],
        )

        main = widgets.Box(
            vertical=True,
            valign="start",
            halign="center",
            css_classes=["settings-manager"],
            child=[self._results],
        )

        overlay = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["settings-overlay"],
            on_click=lambda *_: self._close(),
        )

        super().__init__(
            monitor=config.ui.primary_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_SETTINGS_MANAGER",
            layer="top",
            popup=True,
            css_classes=["settings-window"],
            child=widgets.Overlay(child=overlay, overlays=[main]),
            kb_mode="on_demand",
            setup=lambda w: w.connect("notify::visible", self._on_open),
        )

        self._setup_keyboard_controller()

    # ──────────────────────────────────────────────
    # Keyboard handling
    # ──────────────────────────────────────────────
    def _setup_keyboard_controller(self):
        keyc = Gtk.EventControllerKey()
        keyc.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keyc)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self._close()
            return True

        # Enter opens first item
        if keyval == Gdk.KEY_Return:
            if self._results.child:
                self._results.child[0].on_click(None)
            return True

        return False

    # ──────────────────────────────────────────────
    # Window lifecycle
    # ──────────────────────────────────────────────
    def _close(self):
        self.visible = False

    def _on_open(self, *_):
        if self.visible:
            pass
