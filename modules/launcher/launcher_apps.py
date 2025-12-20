import html

from ignis import widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator
from ignis.services.applications import Application, ApplicationsService
from ignis.window_manager import WindowManager

from settings import config

applications = ApplicationsService.get_default()
window_manager = WindowManager.get_default()

TERMINAL_FORMAT = config.terminal_format
MATCH_COLOR = config.match_color


def highlight(text: str, query: str) -> str:
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
        f'<span foreground="{MATCH_COLOR}" weight="600">{match}</span>'
        f"{after}"
    )


class AppItem(widgets.Button):
    def __init__(self, app: Application, query: str):
        self._app = app
        pop = widgets.PopoverMenu()

        super().__init__(
            css_classes=["app-item", "unset"],
            on_click=lambda *_: self._launch(),
            on_right_click=lambda *_: pop.popup(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Icon(image=app.icon, pixel_size=30),
                    widgets.Label(
                        label=highlight(app.name, query),
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


def build_app_index():
    """Build searchable index of applications"""
    return [(app.name.lower(), app) for app in applications.apps]


def search_apps(query: str, app_index: list) -> list:
    """Search for applications matching the query"""
    ql = query.lower()
    # limit to 5 app results (changed from 6 to 5)
    results = [app for name, app in app_index if ql in name][:4]

    return [AppItem(app, query) for app in results] if results else []
