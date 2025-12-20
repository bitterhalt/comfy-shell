import asyncio

from gi.repository import Gdk, Gtk

from ignis import widgets
from ignis.window_manager import WindowManager

# Import mode search functions
from modules.launcher.launcher_apps import build_app_index, search_apps
from modules.launcher.launcher_binary import search_binaries
from modules.launcher.launcher_calculator import calculate, looks_like_math
from modules.launcher.launcher_emoji import load_emojis, search_emojis

# Import mode helpers
from modules.launcher.launcher_modes import (
    MODE_BINARY,
    MODE_EMOJI,
    MODE_NORMAL,
    MODE_PLACEHOLDERS,
    MODE_SHORTCUTS,
    MODE_WEB,
)
from modules.launcher.launcher_web import search_web
from settings import config

window_manager = WindowManager.get_default()


# =============================================================================
# MAIN LAUNCHER WINDOW
# =============================================================================


class AppLauncher(widgets.Window):
    def __init__(self):
        # Current mode
        self._mode = MODE_NORMAL

        # Load data
        self._emojis = load_emojis()
        self._app_index = build_app_index()

        # Debounce state
        self._search_task = None
        self._last_results_key = None

        # Entry
        self._entry = widgets.Entry(
            placeholder_text=MODE_PLACEHOLDERS[MODE_NORMAL],
            css_classes=["launcher-entry", "unset"],
            hexpand=True,
            on_change=lambda *_: self._debounced_search(
                0.02 if self._mode == MODE_BINARY else 0.04
            ),
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

        # Results
        self._results = widgets.Box(vertical=True, css_classes=["launcher-results"])
        self._results_container = widgets.Box(
            vertical=True,
            visible=False,
            style="margin-top: 0.7rem;",
            child=[self._results],
        )

        # Layout
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
            on_click=lambda *_: self._close(),
        )

        super().__init__(
            monitor=config.ui.launcher_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_LAUNCHER",
            layer="top",
            popup=True,
            css_classes=["launcher-window"],
            child=widgets.Overlay(child=overlay, overlays=[main]),
            kb_mode="on_demand",
            setup=lambda w: w.connect("notify::visible", self._on_open),
        )

        self._setup_keyboard_controller()

    # =========================================================================
    # Keyboard
    # =========================================================================

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

    def _toggle_mode(self, mode: str) -> bool:
        if self._mode == mode:
            self._mode = MODE_NORMAL
        else:
            self._mode = mode

        self._entry.placeholder_text = MODE_PLACEHOLDERS[self._mode]
        self._last_results_key = None

        self._debounced_search(0.02 if self._mode == MODE_BINARY else 0.04)

        return True

    def _cycle_mode(self, direction: int) -> bool:
        mode_order = [MODE_NORMAL, MODE_BINARY, MODE_EMOJI, MODE_WEB]

        try:
            current_idx = mode_order.index(self._mode)
        except ValueError:
            current_idx = 0

        new_idx = (current_idx + direction) % len(mode_order)
        self._mode = mode_order[new_idx]

        self._entry.placeholder_text = MODE_PLACEHOLDERS[self._mode]
        self._last_results_key = None

        if self._entry.text.strip():
            self._debounced_search(0.02 if self._mode == MODE_BINARY else 0.04)
        else:
            self._results.child = []
            self._results_container.visible = False

        return True

    # =========================================================================
    # Search
    # =========================================================================

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

        if self._mode == MODE_BINARY:
            self._results.child = search_binaries(q)
            self._results_container.visible = True
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

        results = search_apps(q, self._app_index)

        if not results:
            self._results.child = []
            self._results_container.visible = False
            return

        self._results.child = results
        self._results_container.visible = True

    # =========================================================================
    # Helpers
    # =========================================================================

    def _launch_first(self):
        if not self._results.child:
            return

        item = self._results.child[0]

        if hasattr(item, "on_click") and callable(item.on_click):
            item.on_click(None)
        elif "calc-result" in item.get_css_classes():
            label = item.child.child[1].child[1]
            Gdk.Display.get_default().get_clipboard().set(label.label.replace("= ", ""))

    def _close(self):
        self.visible = False

    def _on_open(self, *_):
        if self.visible:
            self._entry.text = ""
            self._results.child = []
            self._results_container.visible = False
            self._mode = MODE_NORMAL
            self._entry.placeholder_text = MODE_PLACEHOLDERS[MODE_NORMAL]
            self._entry.grab_focus()
