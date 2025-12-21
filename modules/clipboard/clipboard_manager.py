import asyncio
from dataclasses import dataclass

from gi.repository import Gdk, Gtk
from ignis import utils, widgets
from ignis.window_manager import WindowManager

from settings import config

wm = WindowManager.get_default()


@dataclass
class ClipboardEntry:
    id: str
    content: str
    preview: str


async def _get_clipboard_history() -> list[ClipboardEntry]:
    try:
        result = await utils.exec_sh_async("cliphist list")
        if result.returncode != 0:
            return []

        entries: list[ClipboardEntry] = []

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue

            entry_id, content = parts

            preview = content.replace("\n", " ").strip()
            if len(preview) > 100:
                preview = preview[:97] + "..."

            entries.append(
                ClipboardEntry(
                    id=entry_id,
                    content=content,
                    preview=preview,
                )
            )

        return entries[:50]

    except Exception as e:
        print(f"Clipboard history error: {e}")
        return []


async def _copy_to_clipboard(entry_id: str):
    try:
        await utils.exec_sh_async(f"cliphist decode {entry_id} | wl-copy")
    except Exception as e:
        print(f"Clipboard copy error: {e}")


async def _delete_entry(entry_id: str):
    try:
        await utils.exec_sh_async(f"cliphist delete {entry_id}")
    except Exception as e:
        print(f"Clipboard delete error: {e}")


class ClipboardRow(widgets.Button):
    def __init__(self, entry: ClipboardEntry, manager, selected: bool):
        self._entry = entry
        self._manager = manager

        icon_name = "edit-copy-symbolic"
        if "\n" in entry.content:
            icon_name = "text-x-generic-symbolic"
        elif entry.content.startswith("http"):
            icon_name = "web-browser-symbolic"

        super().__init__(
            css_classes=[
                "clipboard-row",
                "unset",  # Remove focus ring
                "selected" if selected else "",
            ],
            on_click=lambda *_: self._copy(),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Icon(
                        image=icon_name,
                        pixel_size=22,
                        css_classes=["clipboard-icon"],
                    ),
                    widgets.Label(
                        label=entry.preview,
                        ellipsize="end",
                        hexpand=True,
                        halign="start",
                        css_classes=["clipboard-preview"],
                    ),
                    widgets.Button(
                        css_classes=[
                            "clipboard-delete",
                            "unset",
                        ],  # Remove focus ring
                        on_click=lambda *_: self._delete(),
                        child=widgets.Icon(
                            image="user-trash-symbolic",
                            pixel_size=16,
                        ),
                    ),
                ],
            ),
        )

    def _copy(self):
        asyncio.create_task(_copy_to_clipboard(self._entry.id))
        self._manager.visible = False

    def _delete(self):
        asyncio.create_task(self._delete_and_refresh())

    async def _delete_and_refresh(self):
        await _delete_entry(self._entry.id)
        self._manager._reload()


class ClipboardManager(widgets.Window):
    def __init__(self):
        self._all_entries: list[ClipboardEntry] = []
        self._filtered: list[ClipboardEntry] = []
        self._search_text = ""
        self._selected = 0

        self._search = widgets.Entry(
            placeholder_text="Search clipboard…",
            hexpand=True,
            css_classes=["clipboard-search"],
            on_change=lambda e: self._on_search(e.text),
            on_accept=lambda *_: self._activate_selected(),
        )

        # Keyboard handling
        keyc = Gtk.EventControllerKey()
        keyc.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        keyc.connect("key-pressed", self._on_key)
        self._search.add_controller(keyc)

        self._list = widgets.Box(
            vertical=True,
            spacing=4,
            css_classes=["clipboard-list"],
        )

        header = widgets.Box(
            spacing=8,
            css_classes=["clipboard-header"],
            child=[
                widgets.Label(
                    label="Clipboard History",
                    hexpand=True,
                    halign="start",
                    css_classes=["clipboard-title"],
                ),
                widgets.Button(
                    css_classes=["clipboard-clear", "unset"],  #  Remove focus ring
                    child=widgets.Label(label="Clear All"),
                    on_click=lambda *_: self._clear_all(),
                ),
            ],
        )

        scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            css_classes=["clipboard-scroll"],
            child=self._list,
        )

        panel = widgets.Box(
            vertical=True,
            spacing=8,
            css_classes=["clipboard-panel"],
            child=[header, self._search, scroll],
        )

        overlay = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["clipboard-overlay", "unset"],  # Remove focus ring
            on_click=lambda x: wm.close_window("ignis_INTEGRATED_CENTER"),
        )

        root = widgets.Overlay(
            child=overlay,
            overlays=[
                widgets.Box(
                    halign="center",
                    valign="start",
                    child=[panel],
                )
            ],
        )

        super().__init__(
            monitor=config.ui.primary_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            layer="top",
            popup=True,
            namespace="ignis_CLIPBOARD_MANAGER",
            css_classes=["clipboard-window", "unset"],  # Remove window focus ring
            child=root,
            kb_mode="on_demand",
        )

        self.connect("notify::visible", self._on_visible)

    def _on_key(self, _ctrl, keyval, *_):
        if keyval == Gdk.KEY_Down:
            self._move_selection(1)
            return True

        if keyval == Gdk.KEY_Up:
            self._move_selection(-1)
            return True

        return False

    def _move_selection(self, delta: int):
        if not self._filtered:
            return

        self._selected = max(
            0,
            min(self._selected + delta, len(self._filtered) - 1),
        )
        self._render()

    def _activate_selected(self):
        if not self._filtered:
            return

        entry = self._filtered[self._selected]
        asyncio.create_task(_copy_to_clipboard(entry.id))
        self.visible = False

    def _on_visible(self, *_):
        if self.visible:
            self._search.text = ""
            self._search.grab_focus()
            self._reload()

    def _reload(self):
        asyncio.create_task(self._load())

    async def _load(self):
        self._all_entries = await _get_clipboard_history()
        self._selected = 0
        self._apply_filter()

    def _on_search(self, text: str):
        self._search_text = text.lower().strip()
        self._selected = 0
        self._apply_filter()

    def _apply_filter(self):
        if self._search_text:
            self._filtered = [
                e for e in self._all_entries if self._search_text in e.content.lower()
            ]
        else:
            self._filtered = list(self._all_entries)

        self._render()

    def _render(self):
        if not self._filtered:
            self._list.child = [
                widgets.Label(
                    label="No matching clipboard entries",
                    css_classes=["clipboard-empty"],
                )
            ]
            return

        self._list.child = [
            ClipboardRow(
                entry=e,
                manager=self,
                selected=(i == self._selected),
            )
            for i, e in enumerate(self._filtered)
        ]

    def _clear_all(self):
        asyncio.create_task(self._clear_and_reload())

    async def _clear_and_reload(self):
        await utils.exec_sh_async("cliphist wipe")
        self._reload()
