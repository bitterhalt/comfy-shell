import asyncio
import re
from pathlib import Path

from gi.repository import Gdk, Gio
from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator
from ignis.services.applications import (
    Application,
    ApplicationAction,
    ApplicationsService,
)

applications = ApplicationsService.get_default()
TERMINAL_FORMAT = "foot %command%"
EMOJI_FILE = Path("~/.local/share/emoji/emoji").expanduser()


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
        launcher.visible = False


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
        launcher.visible = False

    def _launch_action(self, action: ApplicationAction):
        action.launch()
        launcher.visible = False

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


class SearchWebButton(widgets.Button):
    """Web search/URL visit button"""

    def __init__(self, query: str):
        self._query = query

        browser_desktop_file = utils.exec_sh(
            "xdg-settings get default-web-browser"
        ).stdout.replace("\n", "")

        app_info = Gio.DesktopAppInfo.new(desktop_id=browser_desktop_file)
        icon_name = "applications-internet-symbolic"
        if app_info:
            icon_string = app_info.get_string("Icon")
            if icon_string:
                icon_name = icon_string

        if not query.startswith(("http://", "https://")) and "." in query:
            query = "https://" + query

        if is_url(query):
            label = f"Visit {query}"
            self._url = query
        else:
            label = "Search in Google"
            self._url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

        super().__init__(
            css_classes=["app-item"],
            on_click=lambda x: self._launch(),
            child=widgets.Box(
                child=[
                    widgets.Icon(image=icon_name, pixel_size=48),
                    widgets.Label(
                        label=label,
                        halign="start",
                        hexpand=True,
                        css_classes=["app-name"],
                    ),
                ]
            ),
        )

    def _launch(self):
        asyncio.create_task(utils.exec_sh_async(f"xdg-open {self._url}"))
        launcher.visible = False


class AppLauncher(widgets.Window):
    """Simple app launcher with emoji search"""

    def __init__(self):
        # Load emojis once at startup
        self._emojis = load_emojis()

        # Search entry
        self._entry = widgets.Entry(
            placeholder_text="Search or bang !e emoji",
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
        """Search for apps or emojis"""
        query = self._entry.text

        if not query:
            self._results.child = []
            self._results_container.visible = False
            return

        # Check for emoji bang command: !e <query>
        if query.startswith("!e "):
            emoji_query = query[3:].strip()
            if emoji_query:
                self._search_emojis(emoji_query)
            else:
                self._results.child = []
                self._results_container.visible = False
            return

        # Check for calculator: ends with = or contains math operators
        if query.endswith("=") or self._looks_like_math(query):
            self._calculate(query.rstrip("="))
            return

        # Regular app search
        apps = applications.search(applications.apps, query)

        if not apps:
            # No apps found, offer web search
            self._results.child = [SearchWebButton(query)]
        else:
            # Show first 5 apps
            self._results.child = [AppItem(app) for app in apps[:5]]

        self._results_container.visible = True

    def _looks_like_math(self, query: str) -> bool:
        """Check if query looks like a math expression"""
        # Contains math operators and mostly numbers/operators
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
            # Only allow basic math operations
            allowed_chars = set("0123456789+-*/().** ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")

            # Evaluate
            result = eval(expression, {"__builtins__": {}}, {})

            # Format result
            if isinstance(result, float):
                # Remove trailing zeros
                result_str = f"{result:.10f}".rstrip("0").rstrip(".")
            else:
                result_str = str(result)

            # Create result button
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
            # Don't show error, just hide results
            self._results.child = []
            self._results_container.visible = False

    def _copy_result(self, result: str):
        """Copy calculation result to clipboard"""
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set(result)
        launcher.visible = False

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
            if isinstance(first_item, (AppItem, SearchWebButton)):
                first_item._launch()
            elif isinstance(first_item, EmojiItem):
                first_item._copy()
            elif (
                hasattr(first_item, "get_css_classes")
                and "calc-result" in first_item.get_css_classes()
            ):
                # Copy calculation result
                result_label = first_item.child.child[1].child[1]
                result_text = result_label.label.replace("= ", "")
                self._copy_result(result_text)

    def _close(self):
        """Close launcher"""
        self.visible = False


# Create the launcher window
launcher = AppLauncher()


def toggle_launcher():
    """Toggle launcher visibility"""
    launcher.visible = not launcher.visible
