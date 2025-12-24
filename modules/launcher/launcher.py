"""Main launcher window"""

import asyncio

from ignis import widgets
from ignis.window_manager import WindowManager

from settings import config

from .keyboard import KeyboardController
from .launcher_modes import MODE_NORMAL, MODE_PLACEHOLDERS
from .search import SearchCoordinator

wm = WindowManager.get_default()


class AppLauncher(widgets.Window):
    """Main launcher window with search and mode switching"""

    def __init__(self):
        # State
        self._mode = MODE_NORMAL
        self._search_task = None
        self._last_results_key = None

        # Search coordinator
        self._search_coordinator = SearchCoordinator()

        # Entry
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
            on_click=lambda x: wm.close_window("ignis_LAUNCHER"),
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

        # Setup keyboard handling
        self._keyboard = KeyboardController(self)

    # =========================================================================
    # Search
    # =========================================================================

    def _debounced_search(self, delay: float = 0.04):
        """Debounce search to avoid excessive updates"""
        if self._search_task:
            self._search_task.cancel()

        async def run():
            await asyncio.sleep(delay)
            self._search()

        self._search_task = asyncio.create_task(run())

    def _search(self):
        """Perform search based on current query and mode"""
        q = self._entry.text.strip()
        key = f"{q}|{self._mode}"

        # Skip if same search
        if key == self._last_results_key:
            return
        self._last_results_key = key

        # Clear if empty query
        if not q:
            self._results.child = []
            self._results_container.visible = False
            return

        # Get results from search coordinator
        results = self._search_coordinator.search(q, self._mode)

        if not results:
            self._results.child = []
            self._results_container.visible = False
            return

        self._results.child = results
        self._results_container.visible = True

    # =========================================================================
    # Actions
    # =========================================================================

    def _launch_first(self):
        """Launch/activate first result on Enter"""
        if not self._results.child:
            return

        item = self._results.child[0]

        if hasattr(item, "on_click") and callable(item.on_click):
            item.on_click(None)
        elif "calc-result" in item.get_css_classes():
            # Special handling for calculator results (copy to clipboard)
            from gi.repository import Gdk

            label = item.child.child[1].child[1]
            Gdk.Display.get_default().get_clipboard().set(label.label.replace("= ", ""))

    def _on_open(self, *_):
        """Reset state when window opens"""
        if self.visible:
            self._entry.text = ""
            self._results.child = []
            self._results_container.visible = False
            self._mode = MODE_NORMAL
            self._entry.placeholder_text = MODE_PLACEHOLDERS[MODE_NORMAL]
            self._entry.grab_focus()
