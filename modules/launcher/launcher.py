import asyncio

from gi.repository import Gdk, Gtk
from ignis import widgets
from ignis.window_manager import WindowManager
from modules.launcher.launcher_apps import build_app_index, search_apps
from modules.launcher.launcher_binary import search_binaries
from modules.launcher.launcher_calculator import calculate, looks_like_math
from modules.launcher.launcher_emoji import load_emojis, search_emojis
from modules.launcher.launcher_modes import (
    MODE_EMOJI,
    MODE_NORMAL,
    MODE_PLACEHOLDERS,
    MODE_SHORTCUTS,
    MODE_WEB,
)
from modules.launcher.launcher_web import search_web

from settings import config

wm = WindowManager.get_default()


class AppLauncher(widgets.Window):
    def __init__(self):
        self._mode = MODE_NORMAL

        self._emojis = load_emojis()
        self._app_index = build_app_index()

        self._search_task = None
        self._last_results_key = None

        self._entry = widgets.Entry(
            placeholder_text=MODE_PLACEHOLDERS[MODE_NORMAL],
            css_classes=["launcher-entry", "unset"],
            hexpand=True,
            on_change=lambda *_: self._debounced_search(0.04),
            on_accept=lambda *_: self._launch_first(),
        )

        search_box = widgets.Box(
            css_classes=["launcher-search-box"],
            spacing=8,
            child=[
                widgets.Icon(image="system-search-symbolic", pixel_size=20),
                self._entry,
            ],
        )

        self._results = widgets.Box(vertical=True, css_classes=["launcher-results"])
        self._results_container = widgets.Box(
            vertical=True,
            visible=False,
            style="margin-top: 0.7rem;",
            child=[self._results],
        )

        main = widgets.Box(
            vertical=True,
            valign="start",
            halign="center",
            css_classes=["launcher"],
            child=[search_box, self._results_container],
        )

        overlay = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["launcher-overlay", "unset"],
            on_click=lambda *_: wm.close_window("ignis_LAUNCHER"),
        )

        super().__init__(
            monitor=config.ui.launcher_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_LAUNCHER",
            layer="top",
            popup=True,
            css_classes=["launcher-window", "unset"],
            child=widgets.Overlay(child=overlay, overlays=[main]),
            kb_mode="on_demand",
            setup=lambda w: w.connect("notify::visible", self._on_open),
        )

        self._setup_keyboard_controller()

    # ──────────────────────────────────────────────
    # Keyboard
    # ──────────────────────────────────────────────

    def _setup_keyboard_controller(self):
        keyc = Gtk.EventControllerKey()
        keyc.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keyc)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        alt = state & Gdk.ModifierType.ALT_MASK

        if alt and keyval == Gdk.KEY_Left:
            return self._cycle_mode(-1)
        elif alt and keyval == Gdk.KEY_Right:
            return self._cycle_mode(1)

        if alt:
            keyname = Gdk.keyval_name(keyval)
            if not keyname:
                return False
            key = keyname.lower()
            if key in MODE_SHORTCUTS:
                return self._toggle_mode(MODE_SHORTCUTS[key])

        return False

    # ──────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────

    def _debounced_search(self, delay: float = 0.04):
        if self._search_task:
            self._search_task.cancel()

        async def run():
            await asyncio.sleep(delay)
            self._search()

        self._search_task = asyncio.create_task(run())

    def _search(self):
        q = self._entry.text.strip()
        key = f"{q}|{self._mode}"

        if key == self._last_results_key:
            return
        self._last_results_key = key

        if not q:
            self._results.child = []
            self._results_container.visible = False
            return

        if self._mode == MODE_EMOJI:
            self._results.child = search_emojis(q, self._emojis)
            self._results_container.visible = True
            return

        if self._mode == MODE_WEB:
            self._results.child = search_web(q)
            self._results_container.visible = True
            return

        if q.endswith("=") or looks_like_math(q):
            self._results.child = calculate(q.rstrip("="))
            self._results_container.visible = True
            return

        app_results = search_apps(q, self._app_index)
        bin_results = search_binaries(q)

        if bin_results and len(bin_results) == 1:
            item = bin_results[0]
            if "no-results" in getattr(item, "css_classes", []):
                if app_results:
                    bin_results = []

        results = app_results + bin_results

        if not results:
            self._results.child = []
            self._results_container.visible = False
            return

        self._results.child = results
        self._results_container.visible = True

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _launch_first(self):
        if self._results.child:
            item = self._results.child[0]
            if hasattr(item, "on_click"):
                item.on_click(None)

    def _on_open(self, *_):
        if self.visible:
            self._entry.text = ""
            self._results.child = []
            self._results_container.visible = False
            self._mode = MODE_NORMAL
            self._entry.placeholder_text = MODE_PLACEHOLDERS[MODE_NORMAL]
            self._entry.grab_focus()
        else:
            # 🔴 critical cleanup
            if self._search_task:
                self._search_task.cancel()
                self._search_task = None
