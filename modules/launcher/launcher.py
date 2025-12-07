import asyncio
import html
import os
import shlex
from pathlib import Path

from gi.repository import Gdk, Gtk
from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator
from ignis.services.applications import Application, ApplicationsService
from ignis.window_manager import WindowManager

# Import mode helpers
from modules.launcher.launcher_modes import (
    MODE_BINARY,
    MODE_EMOJI,
    MODE_NORMAL,
    MODE_PLACEHOLDERS,
    MODE_SETTINGS,
    MODE_SHORTCUTS,
    MODE_WEB,
)
from modules.launcher.launcher_settings import search_settings

applications = ApplicationsService.get_default()
window_manager = WindowManager.get_default()

MATCH_COLOR = "#24837B"
TERMINAL_FORMAT = "foot %command%"
EMOJI_FILE = Path("~/.local/share/emoji/emoji").expanduser()
_PATH_BINARIES = None


# =============================================================================
# FUZZY MATCHER
# =============================================================================


def _scan_path_binaries():
    bins, seen = [], set()
    for directory in os.environ.get("PATH", "").split(":"):
        if not directory:
            continue
        try:
            for entry in os.listdir(directory):
                full = os.path.join(directory, entry)
                if (
                    entry not in seen
                    and os.path.isfile(full)
                    and os.access(full, os.X_OK)
                ):
                    seen.add(entry)
                    bins.append((entry, entry.lower(), full))
        except Exception:
            continue
    return bins


def _get_path_binaries():
    global _PATH_BINARIES
    if _PATH_BINARIES is None:
        _PATH_BINARIES = _scan_path_binaries()
    return _PATH_BINARIES


def _fuzzy_score(candidate: str, query: str) -> int:
    """Fast fuzzy scoring with subsequence + gap penalty."""
    n = candidate
    q = query.lower()

    if not q:
        return 0
    if n == q:
        return 1000
    if n.startswith(q):
        return 800
    if q in n:
        return 600

    i = 0
    last_pos = -1
    gaps = 0

    for idx, c in enumerate(n):
        if i < len(q) and c == q[i]:
            if last_pos >= 0:
                gaps += idx - last_pos - 1
            last_pos = idx
            i += 1
            if i == len(q):
                break

    if i == len(q):
        return max(400 - gaps, 50)

    return 0


# =============================================================================
# MATCH HIGHLIGHTING
# =============================================================================


def _highlight(text: str, query: str) -> str:
    """Return text with matched substring wrapped in colored span."""
    if not query:
        return html.escape(text)

    t = text
    q = query.lower()
    tl = t.lower()
    idx = tl.find(q)

    if idx == -1:
        return html.escape(t)

    end = idx + len(query)
    before = html.escape(t[:idx])
    match = html.escape(t[idx:end])
    after = html.escape(t[end:])

    return (
        f"{before}"
        f'<span foreground="{MATCH_COLOR}" weight="bold">{match}</span>'
        f"{after}"
    )


# =============================================================================
# EMOJI SEARCH
# =============================================================================


def load_emojis():
    out = []
    try:
        if EMOJI_FILE.exists():
            for line in EMOJI_FILE.read_text().splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    out.append((parts[0], parts[1]))
    except Exception:
        pass
    return out


def search_emojis(query, emojis, limit=10):
    q = query.lower()
    res = []
    for emoji_char, name in emojis:
        if q in name.lower():
            res.append((emoji_char, name))
            if len(res) >= limit:
                break
    return res


# =============================================================================
# RESULT ITEM WIDGETS
# =============================================================================


class EmojiItem(widgets.Button):
    def __init__(self, char, name):
        self._emoji = char
        super().__init__(
            css_classes=["emoji-item"],
            on_click=lambda *_: self._copy(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Label(label=char, css_classes=["emoji-char"]),
                    widgets.Label(
                        label=html.escape(name),
                        use_markup=True,
                        ellipsize="end",
                        hexpand=True,
                    ),
                ],
            ),
        )

    def _copy(self):
        Gdk.Display.get_default().get_clipboard().set(self._emoji)
        window_manager.close_window("ignis_LAUNCHER")


class AppItem(widgets.Button):
    def __init__(self, app: Application, query: str):
        self._app = app
        pop = widgets.PopoverMenu()

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda *_: self._launch(),
            on_right_click=lambda *_: pop.popup(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Icon(image=app.icon, pixel_size=30),
                    widgets.Label(
                        label=_highlight(app.name, query),
                        use_markup=True,
                        ellipsize="end",
                        hexpand=True,
                    ),
                    pop,
                ],
            ),
        )

        self._menu = pop
        self._sync_menu()
        app.connect("notify::is-pinned", lambda *_: self._sync_menu())

    def _launch(self):
        self._app.launch(terminal_format=TERMINAL_FORMAT)
        window_manager.close_window("ignis_LAUNCHER")

    def _sync_menu(self):
        actions = [IgnisMenuItem("Launch", on_activate=lambda *_: self._launch())]
        if self._app.actions:
            actions.append(IgnisMenuSeparator())
            for a in self._app.actions:
                actions.append(
                    IgnisMenuItem(a.name, on_activate=lambda *_a, act=a: act.launch())
                )
        self._menu.model = IgnisMenuModel(*actions)


class BinaryItem(widgets.Button):
    def __init__(self, name, path, query: str):
        self._path = path
        super().__init__(
            css_classes=["bin-item"],
            on_click=lambda *_: self._launch(),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Icon(image="system-run-symbolic", pixel_size=22),
                    widgets.Label(
                        label=_highlight(name, query),
                        use_markup=True,
                        ellipsize="end",
                        hexpand=True,
                    ),
                ],
            ),
        )

    def _launch(self):
        asyncio.create_task(utils.exec_sh_async(f"{shlex.quote(self._path)} &"))
        window_manager.close_window("ignis_LAUNCHER")


class SearchWebButton(widgets.Button):
    def __init__(self, query):
        url = "https://www.google.com/search?q=" + query.replace(" ", "+")
        self._url = url

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda *_: (
                asyncio.create_task(
                    utils.exec_sh_async(f"xdg-open {shlex.quote(url)}")
                ),
                window_manager.close_window("ignis_LAUNCHER"),
            ),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Icon(image="applications-internet-symbolic", pixel_size=28),
                    widgets.Label(
                        label=f"Search Web for {query}", ellipsize="end", hexpand=True
                    ),
                ],
            ),
        )


# =============================================================================
# MAIN LAUNCHER WINDOW
# =============================================================================


class AppLauncher(widgets.Window):
    def __init__(self):
        self._mode = MODE_NORMAL

        self._emojis = load_emojis()

        self._app_index = [(app.name.lower(), app) for app in applications.apps]

        self._search_task = None
        self._last_results_key = None

        self._entry = widgets.Entry(
            placeholder_text=MODE_PLACEHOLDERS[MODE_NORMAL],
            css_classes=["launcher-entry"],
            hexpand=True,
            on_change=lambda *_: (
                self._search()
                if self._mode == MODE_BINARY
                else self._debounced_search()
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
            css_classes=["launcher-overlay"],
            on_click=lambda *_: self._close(),
        )

        super().__init__(
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
        """Toggle between modes"""
        if self._mode == mode:
            self._mode = MODE_NORMAL
        else:
            self._mode = mode

        self._entry.placeholder_text = MODE_PLACEHOLDERS[self._mode]
        self._last_results_key = None

        if self._mode == MODE_SETTINGS:
            self._search_settings_mode("")
        else:
            self._debounced_search()

        return True

    def _cycle_mode(self, direction: int) -> bool:
        """Cycle through modes with Alt+Left/Right"""
        mode_order = [MODE_NORMAL, MODE_BINARY, MODE_EMOJI, MODE_WEB, MODE_SETTINGS]

        try:
            current_idx = mode_order.index(self._mode)
        except ValueError:
            current_idx = 0

        new_idx = (current_idx + direction) % len(mode_order)
        new_mode = mode_order[new_idx]

        self._mode = new_mode
        self._entry.placeholder_text = MODE_PLACEHOLDERS[self._mode]
        self._last_results_key = None

        if self._mode == MODE_SETTINGS:
            self._search_settings_mode("")
        else:
            if self._entry.text.strip():
                self._debounced_search()
            else:
                self._results.child = []
                self._results_container.visible = False

        return True

    # =========================================================================
    # Search
    # =========================================================================

    def _debounced_search(self):
        if self._search_task:
            self._search_task.cancel()

        async def run():
            await asyncio.sleep(0.04)
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

        # Route to mode
        if self._mode == MODE_BINARY:
            return self._search_binaries(q)
        if self._mode == MODE_EMOJI:
            return self._search_emojis(q)
        if self._mode == MODE_WEB:
            return self._search_web(q)
        if self._mode == MODE_SETTINGS:
            return self._search_settings_mode(q)

        # Calculator
        if q.endswith("=") or self._looks_like_math(q):
            return self._calculate(q.rstrip("="))

        # Normal app search
        ql = q.lower()
        results = [app for name, app in self._app_index if ql in name][:6]

        if not results:
            self._results.child = []
            self._results_container.visible = False
            return

        self._results.child = [AppItem(app, q) for app in results]
        self._results_container.visible = True

    # =========================================================================
    # Mode searches
    # =========================================================================

    def _search_binaries(self, term):
        scored = []
        term_l = term.lower()
        for name, lower_name, path in _get_path_binaries():
            s = _fuzzy_score(lower_name, term_l)
            if s > 0:
                scored.append((s, name, path))

        scored.sort(key=lambda x: x[0], reverse=True)

        self._results.child = (
            [BinaryItem(name, path, term) for _, name, path in scored[:10]]
            if scored
            else [
                widgets.Label(
                    label=f"No binaries for '{html.escape(term)}'",
                    use_markup=True,
                    css_classes=["no-results"],
                )
            ]
        )
        self._results_container.visible = True

    def _search_emojis(self, term):
        matches = search_emojis(term, self._emojis, limit=8)
        self._results.child = (
            [EmojiItem(c, n) for c, n in matches]
            if matches
            else [
                widgets.Label(
                    label=f"No emojis for '{html.escape(term)}'",
                    use_markup=True,
                )
            ]
        )
        self._results_container.visible = True

    def _search_web(self, term):
        self._results.child = [SearchWebButton(term)]
        self._results_container.visible = True

    def _search_settings_mode(self, term):
        """Search settings/config files"""
        results = search_settings(term)
        self._results.child = (
            results
            if results
            else [
                widgets.Label(
                    label=f"No settings for '{html.escape(term)}'",
                    use_markup=True,
                    css_classes=["no-results"],
                )
            ]
        )
        self._results_container.visible = True

    # =========================================================================
    # Calculator
    # =========================================================================

    def _looks_like_math(self, text):
        return any(c.isdigit() for c in text) and any(op in text for op in "+-*/()^.")

    def _calculate(self, expression):
        try:
            expr = expression.replace("^", "**")
            allowed = set("0123456789+-*/(). ")
            if not all(c in allowed or c == "*" for c in expr):
                raise ValueError

            result = eval(expr, {"__builtins__": {}}, {})
            if isinstance(result, float):
                result = f"{result:.10f}".rstrip("0").rstrip(".")

            btn = widgets.Button(
                css_classes=["calc-result"],
                on_click=lambda *_: self._copy_result(str(result)),
                child=widgets.Box(
                    spacing=12,
                    child=[
                        widgets.Label(label="🔢"),
                        widgets.Box(
                            vertical=True,
                            child=[
                                widgets.Label(
                                    label=html.escape(expression),
                                    use_markup=True,
                                ),
                                widgets.Label(
                                    label=f"= {html.escape(str(result))}",
                                    use_markup=True,
                                ),
                            ],
                        ),
                    ],
                ),
            )

            self._results.child = [btn]
            self._results_container.visible = True

        except Exception:
            self._results.child = [widgets.Label(label="Invalid expression")]
            self._results_container.visible = True

    # =========================================================================
    # Helpers
    # =========================================================================

    def _copy_result(self, value):
        Gdk.Display.get_default().get_clipboard().set(value)

    def _launch_first(self):
        if not self._results.child:
            return

        item = self._results.child[0]

        if isinstance(item, (AppItem, BinaryItem, SearchWebButton)):
            item.on_click(None)
        elif isinstance(item, EmojiItem):
            item._copy()
        elif "calc-result" in item.get_css_classes():
            label = item.child.child[1].child[1]
            self._copy_result(label.label.replace("= ", ""))

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
