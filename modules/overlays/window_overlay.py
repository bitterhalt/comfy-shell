import json
import subprocess
from dataclasses import dataclass
from typing import List

from gi.repository import Gdk, Gtk
from ignis import utils, widgets
from ignis.window_manager import WindowManager
from settings import config

wm = WindowManager.get_default()

MAX_WINDOWS = 18
COLUMNS = 9


@dataclass
class WindowEntry:
    index: int
    address: str
    workspace: str
    app_class: str
    icon: str


def _workspace_sort_key(client) -> tuple:
    """
    Sort order:
      1. Normal numeric workspaces (1, 2, 3, …)
      2. Unknown / negative ids
      3. Special workspaces last
    """
    ws = client.get("workspace") or {}
    ws_id = ws.get("id", -1)
    ws_name = ws.get("name") or ""

    if isinstance(ws_name, str) and ws_name.startswith("special"):
        return (9999, ws_name)

    if isinstance(ws_id, int) and ws_id >= 0:
        return (ws_id, ws_name)

    return (9998, ws_name)


def _fetch_windows() -> List[WindowEntry]:
    try:
        out = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
        data = json.loads(out)
    except Exception:
        return []

    data.sort(key=_workspace_sort_key)

    entries: List[WindowEntry] = []

    for idx, client in enumerate(data, start=1):
        if idx > MAX_WINDOWS:
            break

        address = client.get("address", "")
        app_class = client.get("class") or "unknown"

        ws = client.get("workspace") or {}
        ws_id = ws.get("id", -1)
        ws_name = ws.get("name") or str(ws_id)

        if isinstance(ws_name, str) and ws_name.startswith("special"):
            workspace = "⭐"
        else:
            workspace = str(ws_id)

        icon_name = utils.get_app_icon_name(app_class)
        if not icon_name:
            icon_name = "application-x-executable-symbolic"

        entries.append(
            WindowEntry(
                index=idx,
                address=address,
                workspace=workspace,
                app_class=app_class,
                icon=icon_name,
            )
        )

    return entries


def shortcut_label(index: int) -> str:
    """1–9 => '1'..'9', 10–18 => '⌃1'..'⌃9'"""
    if index <= 9:
        return str(index)
    return f"⌃{index - 9}"


def shortcut_css(index: int) -> List[str]:
    if index > 9:
        return ["window-card-ctrlkey"]
    return ["window-card-numkey"]


def _is_ctrl(state) -> bool:
    return bool(state & Gdk.ModifierType.CONTROL_MASK)


class WindowCard(widgets.Button):
    def __init__(self, window: WindowEntry):
        self._window = window

        app_icon = widgets.Icon(
            image=window.icon,
            pixel_size=48,
            css_classes=["window-card-icon"],
        )

        keybind_label = widgets.Label(
            label=shortcut_label(window.index),
            css_classes=["window-card-keybind"],
        )

        app_label = widgets.Label(
            label=window.app_class,
            ellipsize="end",
            max_width_chars=12,
            css_classes=["window-card-app"],
        )

        content = widgets.Box(
            vertical=True,
            spacing=6,
            css_classes=["window-card-content"],
            child=[
                widgets.Box(
                    child=[
                        widgets.Box(hexpand=True),
                        keybind_label,
                    ],
                ),
                app_icon,
                app_label,
            ],
        )

        super().__init__(
            css_classes=["window-card", "unset", *shortcut_css(window.index)],
            on_click=lambda *_: self._focus(),
            child=content,
        )

    def _focus(self):
        subprocess.run(
            ["hyprctl", "dispatch", "focuswindow", f"address:{self._window.address}"],
            check=False,
        )
        wm.close_window("ignis_WINDOW_SWITCHER")


class WindowSwitcherOverlay(widgets.Window):
    def __init__(self):
        self._windows: List[WindowEntry] = []

        self._grid = widgets.Box(
            vertical=True,
            spacing=16,
            halign="center",
            css_classes=["window-grid"],
        )

        content = widgets.Box(
            vertical=True,
            valign="center",
            halign="center",
            css_classes=["window-switcher-overlay"],
            child=[self._grid],
        )

        background = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["window-switcher-background", "unset"],
            on_click=lambda *_: self.toggle(),
        )

        root = widgets.Overlay(
            child=background,
            overlays=[content],
        )

        super().__init__(
            monitor=config.ui.window_switcher_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_WINDOW_SWITCHER",
            exclusivity="ignore",
            layer="overlay",
            popup=True,
            css_classes=["window-switcher-window", "unset"],
            child=root,
            kb_mode="exclusive",
        )

        self.connect("notify::visible", self._on_visible)
        self._setup_keyboard_controller()

    def _setup_keyboard_controller(self):
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)

        if keyname == "Escape":
            self.toggle()
            return True

        ctrl = _is_ctrl(state)

        if keyname and keyname.isdigit():
            n = int(keyname)
            if 1 <= n <= 9:
                idx = (n + 9) if ctrl else n
                self._focus_window_by_index(idx)
                return True

        if keyname and keyname.startswith("KP_") and keyname[3:].isdigit():
            n = int(keyname[3:])
            if 1 <= n <= 9:
                idx = (n + 9) if ctrl else n
                self._focus_window_by_index(idx)
                return True

        return False

    def _focus_window_by_index(self, index: int):
        if 0 < index <= len(self._windows):
            window = self._windows[index - 1]
            subprocess.run(
                ["hyprctl", "dispatch", "focuswindow", f"address:{window.address}"],
                check=False,
            )
            self.toggle()

    def _on_visible(self, *_):
        if self.visible:
            self._reload()

    def _reload(self):
        self._windows = _fetch_windows()

        if not self._windows:
            self._grid.child = [
                widgets.Label(
                    label="No windows open",
                    css_classes=["window-switcher-empty"],
                )
            ]
            return

        rows = []
        for i in range(0, len(self._windows), COLUMNS):
            row = widgets.Box(
                spacing=16,
                halign="center",
                child=[WindowCard(w) for w in self._windows[i : i + COLUMNS]],
            )
            rows.append(row)

        self._grid.child = rows

    def toggle(self):
        self.visible = not self.visible
