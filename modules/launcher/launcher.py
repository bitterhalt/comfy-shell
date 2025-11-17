import asyncio
import re

from gi.repository import Gio
from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator
from ignis.services.applications import (
    Application,
    ApplicationAction,
    ApplicationsService,
)

applications = ApplicationsService.get_default()
TERMINAL_FORMAT = "foot %command%"


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
    """Simple app launcher"""

    def __init__(self):
        # Search entry
        self._entry = widgets.Entry(
            placeholder_text="Search",
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
        """Search for apps"""
        query = self._entry.text

        if not query:
            self._results.child = []
            self._results_container.visible = False
            return

        # Search apps
        apps = applications.search(applications.apps, query)

        if not apps:
            # No apps found, offer web search
            self._results.child = [SearchWebButton(query)]
        else:
            # Show first 5 apps
            self._results.child = [AppItem(app) for app in apps[:5]]

        self._results_container.visible = True

    def _launch_first(self):
        """Launch first result on Enter"""
        if len(self._results.child) > 0:
            first_item = self._results.child[0]
            first_item._launch()

    def _close(self):
        """Close launcher"""
        self.visible = False


# Create the launcher window
launcher = AppLauncher()


def toggle_launcher():
    """Toggle launcher visibility"""
    launcher.visible = not launcher.visible
