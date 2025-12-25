import json
import subprocess
from dataclasses import dataclass
from typing import List

from gi.repository import Gdk, Gtk

from ignis import widgets
from ignis.window_manager import WindowManager
from settings import config

wm = WindowManager.get_default()


# ───────────────────────────────────────────────────────────────
# Hyprland client helpers
# ───────────────────────────────────────────────────────────────


@dataclass
class ClientEntry:
    sortkey: int
    sort_ws: int
    address: str
    ws_label: str
    description: str


def _fetch_clients(reverse: bool = False) -> List[ClientEntry]:
    """Return sorted ClientEntry objects from hyprctl."""
    try:
        out = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
        data = json.loads(out)
    except Exception:
        return []

    entries: List[ClientEntry] = []

    for c in data:
        addr = c.get("address", "")
        cls = c.get("class", "") or "unknown"
        title = c.get("title", "") or "untitled"

        ws = c.get("workspace") or {}
        ws_id = ws.get("id", -1)
        ws_name = ws.get("name") or ""

        try:
            ws_id_int = int(ws_id)
        except Exception:
            ws_id_int = -1

        if isinstance(ws_name, str) and ws_name.startswith("special"):
            sortkey = 1
            sort_ws = 9999
            ws_label = "⭐"

        else:
            sortkey = 0
            sort_ws = ws_id_int
            ws_label = f"[{ws_id_int}]"

        desc = f"{cls} - {title}"

        entries.append(
            ClientEntry(
                sortkey=sortkey,
                sort_ws=sort_ws,
                address=addr,
                ws_label=ws_label,
                description=desc,
            )
        )

    entries.sort(key=lambda e: (e.sortkey, e.sort_ws))

    if reverse:
        entries.reverse()

    return entries


# ───────────────────────────────────────────────────────────────
# Row widget
# ───────────────────────────────────────────────────────────────


class WindowRow(widgets.Button):
    def __init__(self, client: ClientEntry):
        self._client = client

        super().__init__(
            css_classes=["winlist-row", "unset"],  # unset to remove focus ring
            on_click=lambda *_: self._focus(),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Label(label=client.ws_label, css_classes=["winlist-badge"]),
                    widgets.Label(
                        label=client.description,
                        ellipsize="end",
                        hexpand=True,
                        css_classes=["winlist-title"],
                    ),
                ],
            ),
        )

    def _focus(self):
        subprocess.run(
            [
                "hyprctl",
                "dispatch",
                "focuswindow",
                f"address:{self._client.address}",
            ],
            check=False,
        )
        wm.close_window("ignis_WINDOW_SWITCHER")


# ───────────────────────────────────────────────────────────────
# Main popup
# ───────────────────────────────────────────────────────────────


class WindowSwitcher(widgets.Window):
    def __init__(self, reverse: bool = False):
        self._reverse = reverse

        self._list = widgets.Box(
            vertical=True,
            spacing=4,
            css_classes=["winlist-list"],
        )

        panel = widgets.Box(
            vertical=True,
            spacing=8,
            css_classes=["winlist-panel"],
            child=[self._list],
        )

        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["winlist-overlay", "unset"],
            on_click=lambda *_: wm.close_window("ignis_WINDOW_SWITCHER"),
        )

        root = widgets.Overlay(
            child=overlay_btn,
            overlays=[
                widgets.Box(
                    valign="start",
                    halign="center",
                    child=[panel],
                )
            ],
        )

        super().__init__(
            monitor=config.ui.primary_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_WINDOW_SWITCHER",
            layer="top",
            popup=True,
            css_classes=["winlist-window", "unset"],
            child=root,
            kb_mode="on_demand",
        )

        self.connect("notify::visible", self._on_visible)
        self._setup_key_controller()

    def _setup_key_controller(self):
        keyc = Gtk.EventControllerKey()
        keyc.connect("key-pressed", self._on_key)
        self.add_controller(keyc)

    def _on_key(self, *_args):
        keyval = _args[1]
        if keyval == Gdk.KEY_Escape:
            wm.close_window("ignis_WINDOW_SWITCHER")
            return True
        return False

    def _on_visible(self, *_):
        if self.visible:
            self._reload()

    def _reload(self):
        rows = [WindowRow(c) for c in _fetch_clients(self._reverse)]
        self._list.child = rows

        if rows:
            rows[0].grab_focus()
