import asyncio
import html
import os
import shlex

from ignis import utils, widgets
from ignis.window_manager import WindowManager
from settings import config

window_manager = WindowManager.get_default()

_PATH_BINARIES = None
MATCH_COLOR = config.match_color


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


def get_path_binaries():
    global _PATH_BINARIES
    if _PATH_BINARIES is None:
        _PATH_BINARIES = _scan_path_binaries()
    return _PATH_BINARIES


def fuzzy_score(candidate: str, query: str) -> int:
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


class BinaryItem(widgets.Button):
    def __init__(self, name, path, query: str):
        self._path = path

        label = widgets.Label(
            label=highlight(name, query),
            use_markup=True,
            ellipsize="end",
            hexpand=True,
            style="line-height: 1.2;",
        )
        label.min_width_chars = 4

        row = widgets.Box(
            spacing=10,
            child=[
                widgets.Icon(image="system-run-symbolic", pixel_size=28),
                label,
            ],
        )

        row.set_height_request(32)

        super().__init__(
            css_classes=["bin-item", "unset"],
            on_click=lambda *_: self._launch(),
            child=row,
        )

    def _launch(self):
        asyncio.create_task(utils.exec_sh_async(f"{shlex.quote(self._path)} &"))
        window_manager.close_window("ignis_LAUNCHER")


def search_binaries(term: str) -> list:
    scored = []
    term_l = term.lower()

    for name, lower_name, path in get_path_binaries():
        s = fuzzy_score(lower_name, term_l)
        if s > 0:
            scored.append((s, name, path))

    scored.sort(key=lambda x: (-x[0], x[1]))

    return (
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
