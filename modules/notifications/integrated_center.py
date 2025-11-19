import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from ignis import utils, widgets
from ignis.options import options
from ignis.services.notifications import Notification, NotificationService

notifications = NotificationService.get_default()
QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()
MAX_NOTIFICATIONS = 10


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


# ═══════════════════════════════════════════════════════════════
# TASK MANAGEMENT FUNCTIONS
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


def format_time_until(fire_at):
    now = int(time.time())
    diff = fire_at - now
    if diff < 0:
        return "Overdue!"
    hours = diff // 3600
    minutes = (diff % 3600) // 60
    if hours > 24:
        days = hours // 24
        return f"{days}d {hours % 24}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION COMPONENTS
# ═══════════════════════════════════════════════════════════════


class NotificationHistoryItem(widgets.Box):
    def __init__(self, notification: Notification):
        icon = widgets.Icon(
            image=(
                notification.icon
                if notification.icon
                else "dialog-information-symbolic"
            ),
            pixel_size=40,
            halign="start",
            valign="start",
        )

        summary = widgets.Label(
            label=notification.summary,
            halign="start",
            ellipsize="end",
            max_width_chars=35,
            css_classes=["notif-history-title"],
            wrap=True,
        )

        body = widgets.Label(
            label=notification.body,
            halign="start",
            ellipsize="end",
            max_width_chars=40,
            css_classes=["notif-history-body"],
            visible=notification.body != "",
            wrap=True,
        )

        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=18),
            css_classes=["notif-history-close"],
            valign="start",
            on_click=lambda x: notification.close(),
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=4,
            child=[summary, body],
            hexpand=True,
        )

        super().__init__(
            css_classes=["notif-history-item"],
            child=[icon, text_box, close_btn],
            spacing=12,
        )

        notification.connect("closed", lambda x: self.unparent())


# ═══════════════════════════════════════════════════════════════
# TASK COMPONENTS
# ═══════════════════════════════════════════════════════════════


class TaskItem(widgets.Box):
    def __init__(self, task, on_delete, on_complete, on_edit, on_snooze):
        self._task = task
        fire_dt = datetime.fromtimestamp(task["fire_at"])
        time_str = fire_dt.strftime("%H:%M")
        date_str = fire_dt.strftime("%d.%m")

        task_info = widgets.Box(
            vertical=True,
            hexpand=True,
            spacing=4,
            child=[
                widgets.Label(
                    label=task["message"],
                    halign="start",
                    ellipsize="end",
                    max_width_chars=30,
                    css_classes=["task-title"],
                    wrap=True,
                ),
                widgets.Label(
                    label=f"{date_str} @ {time_str} • {format_time_until(task['fire_at'])}",
                    halign="start",
                    css_classes=["task-time"],
                ),
            ],
        )

        actions_row = widgets.Box(
            halign="end",
            spacing=6,
            css_classes=["task-actions-row"],
            child=[
                widgets.Button(
                    child=widgets.Icon(
                        image="media-playback-pause-symbolic", pixel_size=16
                    ),
                    css_classes=["task-action-btn", "task-snooze"],
                    tooltip_text="Snooze 5min",
                    on_click=lambda x: on_snooze(task, 5),
                ),
                widgets.Button(
                    child=widgets.Icon(image="document-edit-symbolic", pixel_size=16),
                    css_classes=["task-action-btn", "task-edit"],
                    tooltip_text="Edit",
                    on_click=lambda x: on_edit(task),
                ),
                widgets.Button(
                    child=widgets.Icon(image="emblem-ok-symbolic", pixel_size=16),
                    css_classes=["task-action-btn", "task-complete"],
                    tooltip_text="Complete",
                    on_click=lambda x: on_complete(task),
                ),
                widgets.Button(
                    child=widgets.Icon(image="user-trash-symbolic", pixel_size=16),
                    css_classes=["task-action-btn", "task-delete"],
                    tooltip_text="Delete",
                    on_click=lambda x: on_delete(task),
                ),
            ],
        )

        main_col = widgets.Box(
            vertical=True,
            hexpand=True,
            spacing=6,
            child=[task_info, actions_row],
        )

        super().__init__(
            css_classes=["task-item"],
            spacing=12,
            child=[widgets.Icon(image="alarm-symbolic", pixel_size=32), main_col],
        )


class AddTaskDialog(widgets.Box):
    def __init__(self, on_add, on_cancel):
        self._on_add = on_add
        self._on_cancel = on_cancel
        self._date_offset = 0

        self._message_entry = widgets.Entry(
            placeholder_text="Task description...",
            css_classes=["task-input"],
            hexpand=True,
        )

        self._time_entry = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input"],
            width_request=80,
        )

        self._date_entry = widgets.Entry(
            placeholder_text="DD-MM or DD-MM-YYYY",
            css_classes=["task-input"],
            width_request=140,
        )
        self._date_entry.text = datetime.now().strftime("%d-%m")

        today_btn = widgets.Button(
            child=widgets.Label(label="Today"),
            css_classes=["date-btn"],
            on_click=lambda x: self._set_date(0),
        )
        tomorrow_btn = widgets.Button(
            child=widgets.Label(label="Tomorrow"),
            css_classes=["date-btn"],
            on_click=lambda x: self._set_date(1),
        )

        cancel_btn = widgets.Button(
            child=widgets.Label(label="Cancel"),
            css_classes=["dialog-btn", "cancel-btn"],
            on_click=lambda x: on_cancel(),
        )
        add_btn = widgets.Button(
            child=widgets.Label(label="Add Task"),
            css_classes=["dialog-btn", "add-btn"],
            on_click=lambda x: self._add_task(),
        )

        super().__init__(
            vertical=True,
            css_classes=["add-task-dialog"],
            spacing=12,
            child=[
                widgets.Label(
                    label="Add New Task",
                    css_classes=["dialog-title"],
                    halign="start",
                ),
                self._message_entry,
                widgets.Box(
                    spacing=8,
                    child=[
                        widgets.Label(label="Time:", css_classes=["input-label"]),
                        self._time_entry,
                    ],
                ),
                widgets.Box(
                    spacing=8,
                    child=[
                        widgets.Label(label="Date:", css_classes=["input-label"]),
                        self._date_entry,
                        today_btn,
                        tomorrow_btn,
                    ],
                ),
                widgets.Box(
                    css_classes=["dialog-footer"],
                    hexpand=True,
                    child=[cancel_btn, add_btn],
                ),
            ],
        )

    def _set_date(self, offset):
        self._date_offset = offset
        base = datetime.now() + timedelta(days=offset)
        self._date_entry.text = base.strftime("%d-%m")

    def _add_task(self):
        message = self._message_entry.text.strip()
        time_str = self._time_entry.text.strip()
        date_str = self._date_entry.text.strip()

        if not message or not time_str:
            return

        try:
            hour, minute = map(int, time_str.split(":"))
            now = datetime.now()

            if date_str:
                parts = date_str.split("-")
                if len(parts) == 2:
                    day, month = map(int, parts)
                    year = now.year
                elif len(parts) == 3:
                    day, month, year = map(int, parts)
                else:
                    return

                fire_dt = datetime(year, month, day, hour, minute)
                if fire_dt <= now:
                    return
            else:
                base = now.date() + timedelta(days=self._date_offset)
                fire_dt = datetime(base.year, base.month, base.day, hour, minute)
                if fire_dt <= now:
                    fire_dt += timedelta(days=1)

            self._on_add({"message": message, "fire_at": int(fire_dt.timestamp())})
        except Exception:
            return


class EditTaskDialog(widgets.Box):
    def __init__(self, task, on_save, on_cancel):
        self._task = task
        self._on_save = on_save
        fire_dt = datetime.fromtimestamp(task["fire_at"])

        self._message_entry = widgets.Entry(
            placeholder_text="Task description...",
            css_classes=["task-input"],
            hexpand=True,
        )
        self._message_entry.text = task.get("message", "")

        self._time_entry = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input"],
            width_request=80,
        )
        self._time_entry.text = fire_dt.strftime("%H:%M")

        self._date_entry = widgets.Entry(
            placeholder_text="DD-MM-YYYY",
            css_classes=["task-input"],
            width_request=140,
        )
        self._date_entry.text = fire_dt.strftime("%d-%m-%Y")

        cancel_btn = widgets.Button(
            child=widgets.Label(label="Cancel"),
            css_classes=["dialog-btn", "cancel-btn"],
            on_click=lambda x: on_cancel(),
        )
        save_btn = widgets.Button(
            child=widgets.Label(label="Save"),
            css_classes=["dialog-btn", "add-btn"],
            on_click=lambda x: self._save_task(),
        )

        super().__init__(
            vertical=True,
            css_classes=["add-task-dialog"],
            spacing=12,
            child=[
                widgets.Label(
                    label="Edit Task",
                    css_classes=["dialog-title"],
                    halign="start",
                ),
                self._message_entry,
                widgets.Box(
                    spacing=8,
                    child=[
                        widgets.Label(label="Time:", css_classes=["input-label"]),
                        self._time_entry,
                    ],
                ),
                widgets.Box(
                    spacing=8,
                    child=[
                        widgets.Label(label="Date:", css_classes=["input-label"]),
                        self._date_entry,
                    ],
                ),
                widgets.Box(
                    css_classes=["dialog-footer"],
                    hexpand=True,
                    child=[cancel_btn, save_btn],
                ),
            ],
        )

    def _save_task(self):
        message = self._message_entry.text.strip()
        time_str = self._time_entry.text.strip()
        date_str = self._date_entry.text.strip()

        if not message or not time_str or not date_str:
            return

        try:
            hour, minute = map(int, time_str.split(":"))
            day, month, year = map(int, date_str.split("-"))
            now = datetime.now()
            fire_dt = datetime(year, month, day, hour, minute)

            if fire_dt <= now:
                return

            new_task = dict(self._task)
            new_task["message"] = message
            new_task["fire_at"] = int(fire_dt.timestamp())

            self._on_save(new_task)
        except Exception:
            return


# ═══════════════════════════════════════════════════════════════
# MAIN INTEGRATED CENTER
# ═══════════════════════════════════════════════════════════════


class IntegratedCenter(widgets.Window):
    def __init__(self):
        # Tab buttons
        self._notif_tab = widgets.Button(
            child=widgets.Label(label="Notifications"),
            css_classes=["tab-button", "tab-active"],
            on_click=lambda x: self._switch_tab("notif"),
        )

        self._task_tab = widgets.Button(
            child=widgets.Label(label="Tasks"),
            css_classes=["tab-button"],
            on_click=lambda x: self._switch_tab("task"),
        )

        tab_bar = widgets.Box(
            css_classes=["tab-bar"],
            homogeneous=True,
            child=[self._notif_tab, self._task_tab],
        )

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

        # Scrollable content
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

        # Bottom bar with DND and Clear/Add button (GNOME style)
        dnd_box = widgets.Box(
            spacing=8,
            child=[
                widgets.Label(
                    label="DND",
                    css_classes=["bottom-label"],
                ),
                widgets.Switch(
                    active=options.notifications.bind("dnd"),
                    on_change=lambda x, state: options.notifications.set_dnd(state),
                ),
            ],
        )
        dnd_box.hexpand = True
        dnd_box.halign = "start"

        self._bottom_action_button = widgets.Button(
            child=widgets.Label(label="Clear"),
            css_classes=["bottom-clear-btn"],
            on_click=lambda x: self._handle_bottom_action(),
        )

        bottom_bar = widgets.Box(
            css_classes=["bottom-bar"],
            child=[dnd_box, self._bottom_action_button],
        )

        # Main container
        self._main_content = widgets.Box(
            vertical=True,
            css_classes=["integrated-center"],
            child=[tab_bar, self._scroll, bottom_bar],
        )

        # Dialog overlay (for add/edit)
        self._dialog_overlay = widgets.Box(
            vertical=True,
            css_classes=["dialog-overlay"],
            visible=False,
        )

        overlay_button = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["center-overlay"],
            on_click=lambda x: toggle_integrated_center(),
        )

        # Center container with margin
        centered_container = widgets.Box(
            valign="start",
            halign="center",
            css_classes=["center-container"],
            child=[
                widgets.Overlay(
                    child=self._main_content,
                    overlays=[self._dialog_overlay],
                )
            ],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_INTEGRATED_CENTER",
            layer="top",
            popup=True,
            css_classes=["center-window"],
            child=widgets.Overlay(
                child=overlay_button,
                overlays=[centered_container],
            ),
            kb_mode="on_demand",
            setup=lambda self: self.connect("notify::visible", self._on_open),
        )

        self._current_tab = "notif"
        self._load_notifications()
        self._reload_tasks()

        notifications.connect("notified", self._on_notified)

        # Auto-refresh tasks
        utils.Poll(30000, self._reload_tasks)

    def _on_open(self, *args):
        if self.visible:
            self._reload_tasks()

    def _switch_tab(self, tab):
        self._current_tab = tab

        if tab == "notif":
            self._notif_tab.add_css_class("tab-active")
            self._task_tab.remove_css_class("tab-active")
            self._scroll.child = self._notif_content
            self._bottom_action_button.child.set_label("Clear")
        else:
            self._task_tab.add_css_class("tab-active")
            self._notif_tab.remove_css_class("tab-active")
            self._scroll.child = self._task_content
            self._bottom_action_button.child.set_label("Add Task")
            self._reload_tasks()

    def _handle_bottom_action(self):
        """Handle bottom action button based on current tab"""
        if self._current_tab == "notif":
            notifications.clear_all()
        else:
            self._show_add_dialog()

    # ─── Notification Methods ───
    def _load_notifications(self):
        recent_notifs = notifications.notifications[:MAX_NOTIFICATIONS]
        for notif in recent_notifs:
            self._notif_list.append(NotificationHistoryItem(notif))
        self._update_notif_empty()

    def _on_notified(self, service, notification):
        self._notif_list.prepend(NotificationHistoryItem(notification))
        if len(self._notif_list.child) > MAX_NOTIFICATIONS:
            oldest = self._notif_list.child[-1]
            oldest.unparent()
        self._update_notif_empty()

    def _update_notif_empty(self, *args):
        self._notif_empty.visible = len(self._notif_list.child) == 0

    # ─── Task Methods ───
    def _reload_tasks(self, *args):
        tasks = load_tasks()
        now_ts = int(time.time())
        active_tasks = sorted(
            [t for t in tasks if t.get("fire_at", 0) > now_ts],
            key=lambda t: t["fire_at"],
        )

        self._task_list.child = [
            TaskItem(
                task,
                self._delete_task,
                self._complete_task,
                self._open_edit_dialog,
                self._snooze_task,
            )
            for task in active_tasks
        ]

        self._task_empty.visible = len(active_tasks) == 0
        return True

    def _show_add_dialog(self):
        self._dialog_overlay.child = [
            AddTaskDialog(on_add=self._add_task, on_cancel=self._cancel_dialog)
        ]
        self._dialog_overlay.visible = True

    def _open_edit_dialog(self, task):
        self._dialog_overlay.child = [
            EditTaskDialog(
                task,
                on_save=lambda new: self._update_task(task, new),
                on_cancel=self._cancel_dialog,
            )
        ]
        self._dialog_overlay.visible = True

    def _cancel_dialog(self):
        self._dialog_overlay.visible = False
        self._dialog_overlay.child = []

    def _add_task(self, task):
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        self._cancel_dialog()
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
        self._cancel_dialog()
        self._reload_tasks()

    def _delete_task(self, task):
        tasks = load_tasks()
        tasks = [t for t in tasks if t != task]
        save_tasks(tasks)
        self._reload_tasks()

    def _complete_task(self, task):
        self._delete_task(task)

    def _snooze_task(self, task, minutes=5):
        now = int(time.time())
        new_tasks = []
        used = False
        for t in load_tasks():
            if not used and t == task:
                nt = dict(t)
                nt["fire_at"] = now + minutes * 60
                new_tasks.append(nt)
                used = True
            else:
                new_tasks.append(t)
        save_tasks(new_tasks)
        self._reload_tasks()


integrated_center = IntegratedCenter()


def toggle_integrated_center():
    """Toggle integrated center visibility"""
    integrated_center.visible = not integrated_center.visible


def open_notifications():
    """Open integrated center and focus on notifications tab"""
    integrated_center._switch_tab("notif")
    integrated_center.visible = True


def open_tasks():
    """Open integrated center and focus on tasks tab"""
    integrated_center._switch_tab("task")
    integrated_center.visible = True
