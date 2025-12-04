import asyncio
import os
import shlex
from pathlib import Path

from gi.repository import Gdk, Gtk

from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator
from ignis.services.applications import Application, ApplicationsService
from ignis.window_manager import WindowManager

applications = ApplicationsService.get_default()
TERMINAL_FORMAT = "foot %command%"
EMOJI_FILE = Path("~/.local/share/emoji/emoji").expanduser()

window_manager = WindowManager.get_default()

# Cache for PATH binaries
_PATH_BINARIES = None


# ───────────────────────────────────────────────────────────────
# PATH BINARY HELPERS
# ───────────────────────────────────────────────────────────────
def _scan_path_binaries():
    bins = []
    seen = set()
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
                    bins.append((entry, full))
                    seen.add(entry)
        except Exception:
            continue
    return bins


def _get_path_binaries():
    global _PATH_BINARIES
    if _PATH_BINARIES is None:
        _PATH_BINARIES = _scan_path_binaries()
    return _PATH_BINARIES


def _fuzzy_score(name, query):
    n, q = name.lower(), query.lower()
    if not q:
        return 0
    if n == q:
        return 100
    if n.startswith(q):
        return 80
    if q in n:
        return 60

    # subsequence
    i = 0
    for c in n:
        if i < len(q) and c == q[i]:
            i += 1
    return 40 if i == len(q) else 0


# ───────────────────────────────────────────────────────────────
# EMOJI LOADING
# ───────────────────────────────────────────────────────────────
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


def search_emojis(query, emojis, limit=20):
    q = query.lower()
    results = []
    for emoji_char, name in emojis:
        if q in name.lower():
            results.append((emoji_char, name))
            if len(results) >= limit:
                break
    return results


# ───────────────────────────────────────────────────────────────
# RESULT ITEM WIDGETS
# ───────────────────────────────────────────────────────────────
class EmojiItem(widgets.Button):
    def __init__(self, emoji_char, name):
        self._emoji = emoji_char
        super().__init__(
            css_classes=["emoji-item"],
            on_click=lambda *_: self._copy(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Label(label=emoji_char, css_classes=["emoji-char"]),
                    widgets.Label(
                        label=name,
                        ellipsize="end",
                        hexpand=True,
                        css_classes=["emoji-name"],
                    ),
                ],
            ),
        )

    def _copy(self):
        Gdk.Display.get_default().get_clipboard().set(self._emoji)
        window_manager.close_window("ignis_LAUNCHER")


class AppItem(widgets.Button):
    def __init__(self, app: Application):
        self._app = app
        pop = widgets.PopoverMenu()

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda *_: self._launch(),
            on_right_click=lambda *_: pop.popup(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Icon(image=app.icon, pixel_size=38),
                    widgets.Label(
                        label=app.name,
                        ellipsize="end",
                        hexpand=True,
                        css_classes=["app-name"],
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
            for act in self._app.actions:
                actions.append(
                    IgnisMenuItem(act.name, on_activate=lambda *_a, a=act: a.launch())
                )
        self._menu.model = IgnisMenuModel(*actions)


class BinaryItem(widgets.Button):
    def __init__(self, name, path):
        self._path = path
        super().__init__(
            css_classes=["bin-item"],
            on_click=lambda *_: self._launch(),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Icon(image="system-run-symbolic", pixel_size=22),
                    widgets.Label(
                        label=name,
                        ellipsize="end",
                        hexpand=True,
                        css_classes=["bin-name"],
                    ),
                ],
            ),
        )

    def _launch(self):
        asyncio.create_task(utils.exec_sh_async(f"{shlex.quote(self._path)} &"))
        window_manager.close_window("ignis_LAUNCHER")


class SearchWebButton(widgets.Button):
    def __init__(self, query):
        raw = query.strip()
        url = "https://www.google.com/search?q=" + raw.replace(" ", "+")

        self._url = url

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda *_: asyncio.create_task(
                utils.exec_sh_async(f"xdg-open {shlex.quote(url)}")
            ),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Icon(
                        image="applications-internet-symbolic",
                        pixel_size=32,
                    ),
                    widgets.Label(
                        label=f"Search Web for “{raw}”",
                        ellipsize="end",
                        hexpand=True,
                    ),
                ],
            ),
        )


# ───────────────────────────────────────────────────────────────
# MAIN LAUNCHER WINDOW
# ───────────────────────────────────────────────────────────────
class AppLauncher(widgets.Window):
    def __init__(self):
        # Modes
        self._emojis = load_emojis()
        self._binary_mode = False
        self._emoji_mode = False
        self._web_mode = False

        # Entry
        self._entry = widgets.Entry(
            placeholder_text="Search…",
            css_classes=["launcher-entry"],
            hexpand=True,
            on_change=lambda *_: self._search(),
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
            style="margin-top: 1rem;",
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
            css_classes=["launcher-overlay"],
            can_focus=False,
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

    # ─────────────────────────────────────
    # Keyboard Controller
    # ─────────────────────────────────────
    def _setup_keyboard_controller(self):
        keyc = Gtk.EventControllerKey()
        keyc.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keyc)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        # Ctrl+B → Binary mode
        if ctrl and keyval == Gdk.KEY_b:
            self._binary_mode = not self._binary_mode
            self._emoji_mode = False
            self._web_mode = False
            self._entry.placeholder_text = (
                "Binary mode…" if self._binary_mode else "Search…"
            )
            self._search()
            return True

        # Ctrl+E → Emoji mode
        if ctrl and keyval == Gdk.KEY_e:
            self._emoji_mode = not self._emoji_mode
            self._binary_mode = False
            self._web_mode = False
            self._entry.placeholder_text = (
                "Emoji mode…" if self._emoji_mode else "Search…"
            )
            self._search()
            return True

        # Ctrl+W → Web mode
        if ctrl and keyval == Gdk.KEY_w:
            self._web_mode = not self._web_mode
            self._binary_mode = False
            self._emoji_mode = False
            self._entry.placeholder_text = "Web mode…" if self._web_mode else "Search…"
            self._search()
            return True

        return False

    # ─────────────────────────────────────
    # Window Lifecycle
    # ─────────────────────────────────────
    def _on_open(self, *_):
        if self.visible:
            self._entry.text = ""
            self._entry.grab_focus()
            self._results.child = []
            self._results_container.visible = False

    # ─────────────────────────────────────
    # Search Engine
    # ─────────────────────────────────────
    def _search(self):
        query = self._entry.text.strip()
        if not query:
            self._results.child = []
            self._results_container.visible = False
            return

        # Modes override everything else
        if self._binary_mode:
            return self._search_binaries(query)

        if self._emoji_mode:
            return self._search_emojis(query)

        if self._web_mode:
            return self._search_web(query)

        # Calculator (auto mode)
        if query.endswith("=") or self._looks_like_math(query):
            return self._calculate(query.rstrip("="))

        # Normal app search
        apps = applications.search(applications.apps, query)
        if not apps:
            self._results.child = []
            self._results_container.visible = False
            return

        self._results.child = [AppItem(a) for a in apps[:6]]
        self._results_container.visible = True

    # ─────────────────────────────────────
    # Search Paths
    # ─────────────────────────────────────
    def _search_binaries(self, term):
        results = []
        for name, path in _get_path_binaries():
            score = _fuzzy_score(name, term)
            if score > 0:
                results.append((score, name, path))

        results.sort(key=lambda x: x[0], reverse=True)

        if not results:
            self._results.child = [
                widgets.Label(
                    label=f"No binaries found for '{term}'",
                    css_classes=["no-results"],
                )
            ]
        else:
            self._results.child = [
                BinaryItem(name, path) for _, name, path in results[:10]
            ]

        self._results_container.visible = True

    def _search_emojis(self, term):
        matches = search_emojis(term, self._emojis, limit=8)
        if matches:
            self._results.child = [EmojiItem(char, name) for char, name in matches]
        else:
            self._results.child = [
                widgets.Label(
                    label=f"No emojis for '{term}'", css_classes=["no-results"]
                )
            ]
        self._results_container.visible = True

    def _search_web(self, term):
        """Always one button: Google search."""
        self._results.child = [SearchWebButton(term)]
        self._results_container.visible = True

    # ─────────────────────────────────────
    # Calculator
    # ─────────────────────────────────────
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

            self._results.child = [
                widgets.Button(
                    css_classes=["calc-result"],
                    on_click=lambda *_: self._copy_result(str(result)),
                    child=widgets.Box(
                        spacing=12,
                        child=[
                            widgets.Label(label="🔢", css_classes=["calc-icon"]),
                            widgets.Box(
                                vertical=True,
                                spacing=4,
                                child=[
                                    widgets.Label(
                                        label=expression,
                                        css_classes=["calc-expression"],
                                        halign="start",
                                    ),
                                    widgets.Label(
                                        label=f"= {result}",
                                        css_classes=["calc-answer"],
                                        halign="start",
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            ]
            self._results_container.visible = True

        except Exception:
            self._results.child = [
                widgets.Label(label="Invalid expression", css_classes=["calc-error"])
            ]
            self._results_container.visible = True

    def _copy_result(self, value):
        Gdk.Display.get_default().get_clipboard().set(value)

    # ─────────────────────────────────────
    # Launch First Result (Enter)
    # ─────────────────────────────────────
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
            text = label.label.replace("= ", "")
            self._copy_result(text)

    def _close(self):
        self.visible = False
