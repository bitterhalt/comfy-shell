import html

from gi.repository import Gdk

from ignis import widgets
from ignis.window_manager import WindowManager
from settings import config

window_manager = WindowManager.get_default()

EMOJI_FILE = config.paths.emoji_file


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


def search_emojis(query: str, emojis: list, limit: int = 8) -> list:
    """Search for emojis matching the query"""
    q = query.lower()
    matches = []
    for emoji_char, name in emojis:
        if q in name.lower():
            matches.append((emoji_char, name))
            if len(matches) >= limit:
                break

    return (
        [EmojiItem(c, n) for c, n in matches]
        if matches
        else [
            widgets.Label(
                label=f"No emojis for '{html.escape(query)}'",
                use_markup=True,
                css_classes=["no-results"],
            )
        ]
    )
