import asyncio
import os
import re
import shlex
from pathlib import Path

from gi.repository import Gdk

from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator
from ignis.services.applications import (
    Application,
    ApplicationAction,
    ApplicationsService,
)
from ignis.window_manager import WindowManager

applications = ApplicationsService.get_default()
TERMINAL_FORMAT = "foot %command%"
EMOJI_FILE = Path("~/.local/share/emoji/emoji").expanduser()
window_manager = WindowManager.get_default()

# Cache for PATH binaries
_PATH_BINARIES: list[tuple[str, str]] | None = None


def is_url(url: str) -> bool:
    regex = re.compile(
        r"^(?:http|ftp)s?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"\[?[A-F0-9]*:[A-F0-9:]+\]?)"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(regex, url) is not None


def load_emojis():
    """Load emoji database from file"""
    emojis = []
    try:
        if not EMOJI_FILE.exists():
            return emojis

        with EMOJI_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Parse "😀 grinning face"
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    emoji_char, name = parts
                    emojis.append((emoji_char, name))
    except Exception as e:
        print(f"Error loading emojis: {e}")

    return emojis


def search_emojis(query: str, emojis: list, limit: int = 10):
    """Search emojis by name"""
    query_lower = query.lower()
    matches = []

    for emoji_char, name in emojis:
        if query_lower in name.lower():
            matches.append((emoji_char, name))
            if len(matches) >= limit:
                break

    return matches


def _scan_path_binaries() -> list[tuple[str, str]]:
    """
    Scan $PATH and return list of (name, full_path) for executables.
    Cached via _get_path_binaries().
    """
    bins: list[tuple[str, str]] = []
    seen: set[str] = set()
    path_env = os.environ.get("PATH", "")
    for directory in path_env.split(":"):
        if not directory:
            continue
        try:
            entries = os.listdir(directory)
        except FileNotFoundError:
            continue
        except NotADirectoryError:
            continue

        for entry in entries:
            if entry in seen:
                continue
            full = os.path.join(directory, entry)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                seen.add(entry)
                bins.append((entry, full))
    return bins


def _get_path_binaries() -> list[tuple[str, str]]:
    """Get cached PATH binaries, scanning once on first use."""
    global _PATH_BINARIES
    if _PATH_BINARIES is None:
        _PATH_BINARIES = _scan_path_binaries()
    return _PATH_BINARIES


def _fuzzy_score(name: str, query: str) -> int:
    """
    Very small fuzzy score:
    - exact match: 100
    - prefix match: 80
    - substring: 60
    - subsequence: 40
    - otherwise: 0
    """
    n = name.lower()
    q = query.lower()
    if not q:
        return 0
    if n == q:
        return 100
    if n.startswith(q):
        return 80
    if q in n:
        return 60

    # subsequence match
    i = 0
    for c in n:
        if i < len(q) and c == q[i]:
            i += 1
    if i == len(q):
        return 40
    return 0


class EmojiItem(widgets.Button):
    """Individual emoji result"""

    def __init__(self, emoji_char: str, name: str):
        self._emoji = emoji_char
        self._name = name

        super().__init__(
            css_classes=["emoji-item"],
            on_click=lambda x: self._copy(),
            child=widgets.Box(
                child=[
                    widgets.Label(
                        label=emoji_char,
                        css_classes=["emoji-char"],
                    ),
                    widgets.Label(
                        label=name,
                        halign="start",
                        hexpand=True,
                        ellipsize="end",
                        max_width_chars=30,
                        css_classes=["emoji-name"],
                    ),
                ]
            ),
        )

    def _copy(self):
        """Copy emoji to clipboard"""
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set(self._emoji)


class AppItem(widgets.Button):
    """Individual app in search results"""

    def __init__(self, app: Application):
        self._app = app
        self._menu = widgets.PopoverMenu()

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda x: self._launch(),
            on_right_click=lambda x: self._menu.popup(),
            child=widgets.Box(
                child=[
                    widgets.Icon(image=app.icon, pixel_size=38),
                    widgets.Label(
                        label=app.name,
                        halign="start",
                        hexpand=True,
                        ellipsize="end",
                        max_width_chars=30,
                        css_classes=["app-name"],
                    ),
                    self._menu,
                ]
            ),
        )

        self._sync_menu()
        app.connect("notify::is-pinned", lambda x, y: self._sync_menu())

    def _launch(self):
        self._app.launch(terminal_format=TERMINAL_FORMAT)
        window_manager.close_window("ignis_LAUNCHER")

    def launch_action(self, action: ApplicationAction) -> None:
        action.launch()
        window_manager.close_window("ignis_LAUNCHER")

    def _launch_action(self, action: ApplicationAction) -> None:
        self.launch_action(action)

    def _sync_menu(self):
        actions = [
            IgnisMenuItem(label="Launch", on_activate=lambda x: self._launch()),
        ]

        # Add app actions if any
        if self._app.actions:
            actions.append(IgnisMenuSeparator())
            for action in self._app.actions:
                actions.append(
                    IgnisMenuItem(
                        label=action.name,
                        on_activate=lambda x, a=action: self._launch_action(a),
                    )
                )

        self._menu.model = IgnisMenuModel(*actions)


class BinaryItem(widgets.Button):
    """Binary result for % bang search — launches directly."""

    def __init__(self, name: str, path: str):
        self._name = name
        self._path = path

        super().__init__(
            css_classes=["bin-item"],
            on_click=lambda *_: self._launch(),
            child=widgets.Box(
                spacing=8,
                child=[
                    widgets.Icon(
                        image="system-run-symbolic",
                        pixel_size=22,
                        css_classes=["bin-icon"],
                    ),
                    widgets.Label(
                        label=name,
                        halign="start",
                        hexpand=True,
                        ellipsize="end",
                        max_width_chars=30,
                        css_classes=["bin-name"],
                    ),
                ],
            ),
        )

    def _launch(self):
        """Launch binary exactly like dmenu (direct detached exec)."""
        cmd = f"{shlex.quote(self._path)} &"
        asyncio.create_task(utils.exec_sh_async(cmd))
        window_manager.close_window("ignis_LAUNCHER")


class SearchWebButton(widgets.Button):
    """Manual web search / URL open triggered by '@'."""

    def __init__(self, query: str):
        raw_query = query.strip()

        # Decide URL + label
        if raw_query.startswith(("http://", "https://")):
            self._url = raw_query
            label = f"Visit {raw_query}"
        elif "." in raw_query and " " not in raw_query:
            # Looks like a domain
            self._url = "https://" + raw_query
            label = f"Visit {self._url}"
        else:
            # Fallback to Google search
            self._url = "https://www.google.com/search?q=" + raw_query.replace(" ", "+")
            label = f"Search Google for “{raw_query}”"

        icon = "applications-internet-symbolic"

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda *_: asyncio.create_task(
                utils.exec_sh_async(f"xdg-open {shlex.quote(self._url)}")
            ),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Icon(image=icon, pixel_size=38),
                    widgets.Label(
                        label=label,
                        halign="start",
                        hexpand=True,
                        ellipsize="end",
                        max_width_chars=35,
                        css_classes=["app-name"],
                    ),
                ],
            ),
        )


class AppLauncher(widgets.Window):
    """Simple app launcher with emoji search and % PATH binary search"""

    def __init__(self):
        # Load emojis once at startup
        self._emojis = load_emojis()

        # Search entry
        self._entry = widgets.Entry(
            placeholder_text="Search... ",
            css_classes=["launcher-entry"],
            hexpand=True,
            on_change=lambda x: self._search(),
            on_accept=lambda x: self._launch_first(),
        )

        # Search box
        self._search_box = widgets.Box(
            css_classes=["launcher-search-box"],
            child=[
                widgets.Icon(
                    image="system-search-symbolic",
                    pixel_size=24,
                    style="margin-right: 0.5rem;",
                ),
                self._entry,
            ],
        )

        # Results list
        self._results = widgets.Box(
            vertical=True,
            css_classes=["launcher-results"],
        )

        # Results container (hidden by default)
        self._results_container = widgets.Box(
            vertical=True,
            visible=False,
            style="margin-top: 1rem;",
            child=[self._results],
        )

        # Main container
        main_box = widgets.Box(
            vertical=True,
            valign="start",
            halign="center",
            css_classes=["launcher"],
            child=[
                self._search_box,
                self._results_container,
            ],
        )

        # Overlay to close
        overlay = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["launcher-overlay"],
            on_click=lambda x: self._close(),
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_LAUNCHER",
            layer="top",
            popup=True,
            css_classes=["launcher-window"],
            child=widgets.Overlay(
                child=overlay,
                overlays=[main_box],
            ),
            kb_mode="on_demand",
            setup=lambda self: self.connect("notify::visible", self._on_open),
        )

    def _on_open(self, *args):
        """Focus entry when opened"""
        if self.visible:
            self._entry.text = ""
            self._entry.grab_focus()
            self._results.child = []
            self._results_container.visible = False

    def _search(self):
        """Search for apps, emojis, binaries, web, or math"""
        query = self._entry.text

        if not query:
            self._results.child = []
            self._results_container.visible = False
            return

        # Emoji bang: !e <query>
        if query.startswith("!e"):
            emoji_query = query[3:].strip()
            if emoji_query:
                self._search_emojis(emoji_query)
            else:
                self._results.child = []
                self._results_container.visible = False
            return

        # Binary bang: %<query> or % <query>
        if query.startswith("%"):
            bin_query = query[1:].strip()
            if bin_query:
                self._search_binaries(bin_query)
            else:
                self._results.child = []
                self._results_container.visible = False
            return

        # Manual web search: @<query>
        if query.startswith("@"):
            web_query = query[1:].strip()
            if web_query:
                self._results.child = [SearchWebButton(web_query)]
                self._results_container.visible = True
            else:
                self._results.child = []
                self._results_container.visible = False
            return

        # Calculator: ends with = or looks like math
        if query.endswith("=") or self._looks_like_math(query):
            self._calculate(query.rstrip("="))
            return

        # Regular app search
        apps = applications.search(applications.apps, query)

        if not apps:
            # No apps found; do NOT auto web search
            self._results.child = []
            self._results_container.visible = False
            return

        # Show first 5 apps
        self._results.child = [AppItem(app) for app in apps[:5]]
        self._results_container.visible = True

    def _search_binaries(self, term: str):
        """Search binaries in PATH via fuzzy match"""
        binaries = _get_path_binaries()
        scored: list[tuple[int, str, str]] = []

        for name, path in binaries:
            score = _fuzzy_score(name, term)
            if score > 0:
                scored.append((score, name, path))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:10]

        if not top:
            self._results.child = [
                widgets.Label(
                    label=f"No binaries found for '{term}'",
                    css_classes=["no-results"],
                )
            ]
        else:
            self._results.child = [BinaryItem(name, path) for _, name, path in top]

        self._results_container.visible = True

    def _looks_like_math(self, query: str) -> bool:
        """Check if query looks like a math expression"""
        has_operators = any(
            op in query for op in ["+", "-", "*", "/", "^", "(", ")", "."]
        )
        has_numbers = any(c.isdigit() for c in query)
        return has_operators and has_numbers

    def _calculate(self, expression: str):
        """Evaluate math expression and show result"""
        try:
            # Replace ^ with ** for exponentiation
            expression = expression.replace("^", "**")

            # Safely evaluate the expression
            allowed_chars = set("0123456789+-*/().** ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")

            result = eval(expression, {"__builtins__": {}}, {})

            if isinstance(result, float):
                result_str = f"{result:.10f}".rstrip("0").rstrip(".")
            else:
                result_str = str(result)

            result_button = widgets.Button(
                css_classes=["calc-result"],
                on_click=lambda x: self._copy_result(result_str),
                child=widgets.Box(
                    child=[
                        widgets.Label(
                            label="🔢",
                            css_classes=["calc-icon"],
                        ),
                        widgets.Box(
                            vertical=True,
                            halign="start",
                            hexpand=True,
                            child=[
                                widgets.Label(
                                    label=expression,
                                    halign="start",
                                    css_classes=["calc-expression"],
                                ),
                                widgets.Label(
                                    label=f"= {result_str}",
                                    halign="start",
                                    css_classes=["calc-answer"],
                                ),
                            ],
                        ),
                    ]
                ),
            )

            self._results.child = [result_button]
            self._results_container.visible = True

        except Exception:
            self._results.child = []
            self._results_container.visible = False

    def _copy_result(self, result: str):
        """Copy calculation result to clipboard"""
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set(result)

    def _search_emojis(self, query: str):
        """Search and display emojis"""
        matches = search_emojis(query, self._emojis, limit=10)

        if matches:
            self._results.child = [
                EmojiItem(emoji_char, name) for emoji_char, name in matches
            ]
        else:
            self._results.child = [
                widgets.Label(
                    label=f"No emojis found for '{query}'",
                    css_classes=["no-results"],
                )
            ]

        self._results_container.visible = True

    def _launch_first(self):
        """Launch/copy first result on Enter"""
        if len(self._results.child) > 0:
            first_item = self._results.child[0]
            if isinstance(first_item, (AppItem, SearchWebButton, BinaryItem)):
                first_item._launch()
            elif isinstance(first_item, EmojiItem):
                first_item._copy()
            elif (
                hasattr(first_item, "get_css_classes")
                and "calc-result" in first_item.get_css_classes()
            ):
                result_label = first_item.child.child[1].child[1]
                result_text = result_label.label.replace("= ", "")
                self._copy_result(result_text)

    def _close(self):
        """Close launcher"""
        self.visible = False
