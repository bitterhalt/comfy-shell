import asyncio
import html
import os

from ignis import utils, widgets
from ignis.window_manager import WindowManager
from settings import config

wm = WindowManager.get_default()

# ═══════════════════════════════════════════════════════════════
# SETTINGS CONFIGURATION
# ═══════════════════════════════════════════════════════════════

TERMINAL = config.terminal
EDITOR = config.editor
FILE_OPENER = config.file_opener

SETTINGS = [
    {
        "name": "Hyprland",
        "path": "~/.config/hypr/",
        "icon": "preferences-system-symbolic",
        "command": f"{TERMINAL} -e {FILE_OPENER}",
    },
    {
        "name": "Ignis",
        "path": "~/.config/ignis/",
        "icon": "applications-system-symbolic",
        "command": f"{TERMINAL} -e {FILE_OPENER}",
    },
    {
        "name": "Neovim",
        "path": "~/.config/nvim/",
        "icon": "text-editor-symbolic",
        "command": f"{TERMINAL} -e {FILE_OPENER}",
    },
]


# ═══════════════════════════════════════════════════════════════
# SETTINGS ITEM WIDGET
# ═══════════════════════════════════════════════════════════════


class SettingItem(widgets.Button):
    """Individual setting item button"""

    def __init__(self, setting: dict, query: str = ""):
        self._setting = setting
        path = os.path.expanduser(setting["path"])

        super().__init__(
            css_classes=["setting-item"],
            on_click=lambda *_: self._open(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Icon(
                        image=setting.get("icon", "folder-symbolic"),
                        pixel_size=32,
                    ),
                    widgets.Box(
                        vertical=True,
                        spacing=2,
                        hexpand=True,
                        child=[
                            widgets.Label(
                                label=self._highlight(setting["name"], query),
                                use_markup=True,
                                halign="start",
                                css_classes=["setting-name"],
                            ),
                            widgets.Label(
                                label=html.escape(path),
                                use_markup=True,
                                halign="start",
                                ellipsize="end",
                                css_classes=["setting-path"],
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _highlight(self, text: str, query: str) -> str:
        """Highlight matching text"""
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
            f'<span foreground="#24837B" weight="bold">{match}</span>'
            f"{after}"
        )

    def _open(self):
        """Open the setting"""
        path = os.path.expanduser(self._setting["path"])
        command = f"{self._setting['command']} {path}"
        asyncio.create_task(utils.exec_sh_async(f"{command} &"))
        wm.close_window("ignis_LAUNCHER")


# ═══════════════════════════════════════════════════════════════
# SETTINGS SEARCH
# ═══════════════════════════════════════════════════════════════


def search_settings(query: str) -> list[SettingItem]:
    """Search settings by name"""
    if not query:
        return [SettingItem(s) for s in SETTINGS]

    q = query.lower()
    results = []

    for setting in SETTINGS:
        if q in setting["name"].lower():
            results.append(SettingItem(setting, query))

    return results
