# modules/notifications/integrated_center.py

import json
import time
from pathlib import Path

from ignis import utils, widgets
from ignis.options import options
from ignis.services.notifications import NotificationService
from modules.notifications.integrated_center_widgets import (
    AddTaskDialog,
    EditTaskDialog,
    NotificationHistoryItem,
    TaskItem,
)

notifications = NotificationService.get_default()
QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()
MAX_NOTIFICATIONS = 10


# ═══════════════════════════════════════════════════════════════
# TASK STORAGE
# ═══════════════════════════════════════════════════════════════


def load_tasks():
    try:
        if not QUEUE_FILE.exists():
            return []
        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_tasks(tasks):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


# ═══════════════════════════════════════════════════════════════
# INTEGRATED CENTER WINDOW
# ═══════════════════════════════════════════════════════════════


class IntegratedCenter(widgets.Window):
    """
    Top-centered popup control center:

    - Same visuals as before (integrated-center SCSS)
    - Slide-down reveal like the audio menu
    - Click outside to close
    - ESC closes (popup=True + kb_mode)
    """

    def __init__(self):
        # ── Tabs ────────────────────────────────────────────────
        self._notif_tab = widgets.Button(
            child=widgets.Label(label="Notifications"),
            css_classes=["tab-button", "tab-active"],
            on_click=lambda *_: self._switch_tab("notif"),
        )

        self._task_tab = widgets.Button(
            child=widgets.Label(label="Tasks"),
            css_classes=["tab-button"],
            on_click=lambda *_: self._switch_tab("task"),
        )

        tab_bar = widgets.Box(
            css_classes=["tab-bar"],
            homogeneous=True,
            child=[self._notif_tab, self._task_tab],
        )

        # ── Lists & empty states ────────────────────────────────
        self._notif_list = widgets.Box(vertical=True, css_classes=["content-list"])
        self._task_list = widgets.Box(vertical=True, css_classes=["content-list"])

        self._notif_empty = widgets.Label(
            label="No Notifications",
            css_classes=["empty-state"],
            vexpand=True,
            valign="center",
        )

        self._task_empty = widgets.Label(
            label="No active tasks",
            css_classes=["empty-state"],
            vexpand=True,
            valign="center",
        )

        self._notif_content = widgets.Box(
            vertical=True,
            child=[self._notif_list, self._notif_empty],
        )
        self._task_content = widgets.Box(
            vertical=True,
            child=[self._task_list, self._task_empty],
        )

        self._scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            child=self._notif_content,
        )

        # ── Bottom bar (DND + Clear/Add) ────────────────────────
        dnd_switch = widgets.Switch(
            active=options.notifications.bind("dnd"),
            on_change=lambda _, state: options.notifications.set_dnd(state),
        )

        dnd_box = widgets.Box(
            spacing=8,
            child=[
                widgets.Label(label="DND", css_classes=["bottom-label"]),
                dnd_switch,
            ],
        )
        dnd_box.hexpand = True
        dnd_box.halign = "start"

        self._bottom_btn = widgets.Button(
            child=widgets.Label(label="Clear"),
            css_classes=["bottom-clear-btn"],
            on_click=lambda *_: self._handle_bottom(),
        )

        bottom_bar = widgets.Box(
            css_classes=["bottom-bar"],
            child=[dnd_box, self._bottom_btn],
        )

        # ── Main panel (visual content) ─────────────────────────
        main_panel = widgets.Box(
            vertical=True,
            css_classes=["integrated-center"],
            child=[tab_bar, self._scroll, bottom_bar],
        )

        # Slide-down revealer for GNOME-style appearance
        self._revealer = widgets.Revealer(
            child=main_panel,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # Container to center the panel near top
        centered = widgets.Box(
            valign="start",
            halign="center",
            css_classes=["center-container"],
            child=[self._revealer],
        )

        # Fullscreen overlay button: click outside to close
        overlay_button = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["center-overlay"],
            on_click=lambda *_: toggle_integrated_center(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_button,
            overlays=[centered],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_INTEGRATED_CENTER",
            layer="top",
            popup=True,
            css_classes=["center-window"],
            child=root_overlay,
            kb_mode="on_demand",
        )

        # Internal state
        self._current_tab = "notif"

        # Initial load
        self._load_notifications()
        self._reload_tasks()

        notifications.connect("notified", self._on_notified)
        utils.Poll(30000, lambda *_: self._reload_tasks())

    # ───────────────────────────────────────────────────────────
    # Tabs
    # ───────────────────────────────────────────────────────────

    def _switch_tab(self, tab: str):
        self._current_tab = tab

        if tab == "notif":
            self._notif_tab.add_css_class("tab-active")
            self._task_tab.remove_css_class("tab-active")
            self._scroll.child = self._notif_content
            self._bottom_btn.child.set_label("Clear")
        else:
            self._task_tab.add_css_class("tab-active")
            self._notif_tab.remove_css_class("tab-active")
            self._scroll.child = self._task_content
            self._bottom_btn.child.set_label("Add Task")
            self._reload_tasks()

    # ───────────────────────────────────────────────────────────
    # Notifications
    # ───────────────────────────────────────────────────────────

    def _load_notifications(self):
        recent = notifications.notifications[:MAX_NOTIFICATIONS]
        self._notif_list.child = [NotificationHistoryItem(n) for n in recent]
        self._notif_empty.visible = len(self._notif_list.child) == 0

    def _on_notified(self, _, nt):
        self._notif_list.prepend(NotificationHistoryItem(nt))
        # Cap at MAX_NOTIFICATIONS
        if len(self._notif_list.child) > MAX_NOTIFICATIONS:
            oldest = self._notif_list.child[-1]
            oldest.visible = False
            oldest.unparent()
        self._notif_empty.visible = len(self._notif_list.child) == 0

    # ───────────────────────────────────────────────────────────
    # Tasks
    # ───────────────────────────────────────────────────────────

    def _reload_tasks(self, *_):
        now = int(time.time())
        tasks = [t for t in load_tasks() if t.get("fire_at", 0) > now]
        tasks.sort(key=lambda t: t["fire_at"])

        self._task_list.child = [
            TaskItem(
                t,
                self._delete_task,
                self._complete_task,
                self._open_edit_dialog,
                self._snooze_task,
            )
            for t in tasks
        ]
        self._task_empty.visible = len(tasks) == 0
        return True

    def _add_task_and_refresh(self, task):
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        self._hide_dialog()
        self._reload_tasks()

    def _update_task(self, old_task, new_task):
        tasks = load_tasks()
        updated = []
        used = False
        for t in tasks:
            if not used and t == old_task:
                updated.append(new_task)
                used = True
            else:
                updated.append(t)
        save_tasks(updated)
        self._hide_dialog()
        self._reload_tasks()

    def _delete_task(self, task):
        tasks = [t for t in load_tasks() if t != task]
        save_tasks(tasks)
        self._reload_tasks()

    def _complete_task(self, task):
        self._delete_task(task)

    def _snooze_task(self, task, minutes=5):
        now = int(time.time())
        tasks = load_tasks()
        updated = []
        used = False
        for t in tasks:
            if not used and t == task:
                nt = dict(t)
                nt["fire_at"] = now + minutes * 60
                updated.append(nt)
                used = True
            else:
                updated.append(t)
        save_tasks(updated)
        self._reload_tasks()

    # ───────────────────────────────────────────────────────────
    # Dialog handling (Add / Edit task)
    # ───────────────────────────────────────────────────────────

    def _show_dialog(self, dialog):
        """Show dialog inside scroll area, replacing list."""
        self._scroll.child = dialog

    def _hide_dialog(self):
        """Return scroll area to current tab's list."""
        if self._current_tab == "notif":
            self._scroll.child = self._notif_content
        else:
            self._scroll.child = self._task_content

    def _open_add_dialog(self):
        dlg = AddTaskDialog(
            on_add=self._add_task_and_refresh,
            on_cancel=lambda *_: self._hide_dialog(),
        )
        self._show_dialog(dlg)

    def _open_edit_dialog(self, task):
        dlg = EditTaskDialog(
            task,
            on_save=lambda new: self._update_task(task, new),
            on_cancel=lambda *_: self._hide_dialog(),
        )
        self._show_dialog(dlg)

    # ───────────────────────────────────────────────────────────
    # Bottom button
    # ───────────────────────────────────────────────────────────

    def _handle_bottom(self):
        if self._current_tab == "notif":
            notifications.clear_all()
            self._notif_list.child = []
            self._notif_empty.visible = True
        else:
            self._open_add_dialog()


# ═══════════════════════════════════════════════════════════════
# GLOBAL INSTANCE + TOGGLE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

integrated_center = IntegratedCenter()


def toggle_integrated_center():
    """Toggle the integrated center popup with slide animation."""
    if not integrated_center.visible:
        # Open: show window then reveal panel
        integrated_center.visible = True
        utils.Timeout(
            10,
            lambda: setattr(integrated_center._revealer, "reveal_child", True),
        )
    else:
        # Close: hide panel, then hide window after animation
        integrated_center._revealer.reveal_child = False
        utils.Timeout(
            integrated_center._revealer.transition_duration,
            lambda: setattr(integrated_center, "visible", False),
        )


def open_notifications():
    """Open center focused on notifications."""
    integrated_center._switch_tab("notif")
    if not integrated_center.visible:
        toggle_integrated_center()


def open_tasks():
    """Open center focused on tasks."""
    integrated_center._switch_tab("task")
    if not integrated_center.visible:
        toggle_integrated_center()
