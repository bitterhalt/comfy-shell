import html

from ignis import widgets
from ignis.services.applications import Application, ApplicationsService
from ignis.window_manager import WindowManager

from settings import config

applications = ApplicationsService.get_default()
window_manager = WindowManager.get_default()

TERMINAL_FORMAT = config.terminal_format
MATCH_COLOR = config.match_color


def highlight(text: str, query: str) -> str:
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

        super().__init__(
            css_classes=["app-item", "unset"],
            on_click=lambda *_: self._launch(),
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
                ],
            ),
        )

    def _launch(self):
        self._app.launch(terminal_format=TERMINAL_FORMAT)
        window_manager.close_window("ignis_LAUNCHER")


def build_app_index():
    return [(app.name.lower(), app) for app in applications.apps]


def search_apps(query: str, app_index: list) -> list:
    ql = query.lower()
    results = [app for name, app in app_index if ql in name][:4]
    return [AppItem(app, query) for app in results] if results else []
