"""
Web search mode - Search the web with Google
"""

import asyncio
import shlex

from ignis import utils, widgets
from ignis.window_manager import WindowManager

window_manager = WindowManager.get_default()


class SearchWebButton(widgets.Button):
    def __init__(self, query):
        url = "https://www.google.com/search?q=" + query.replace(" ", "+")
        self._url = url

        super().__init__(
            css_classes=["app-item", "unset"],
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


def search_web(query: str) -> list:
    """Create web search button"""
    return [SearchWebButton(query)]
