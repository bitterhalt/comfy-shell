import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from ignis import widgets

QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()


def load_tasks():
    """Load tasks from queue file"""
    try:
        if not QUEUE_FILE.exists():
            return []
        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_tasks(tasks):
    """Save tasks to queue file"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


def format_time_until(fire_at):
    """Format time until task fires"""
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


class TaskItem(widgets.Box):
    """Individual task in the list"""

    def __init__(self, task, on_delete, on_complete, on_edit, on_snooze):
        self._task = task
        self._on_delete = on_delete
        self._on_complete = on_complete
        self._on_edit = on_edit
        self._on_snooze = on_snooze

        fire_dt = datetime.fromtimestamp(task["fire_at"])
        time_str = fire_dt.strftime("%H:%M")
        date_str = fire_dt.strftime("%d.%m")

        task_info = widgets.Box(
            vertical=True,
            hexpand=True,
            child=[
                widgets.Label(
                    label=task["message"],
                    halign="start",
                    ellipsize="end",
                    max_width_chars=30,
                    css_classes=["task-title"],
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
                        image="media-playback-pause-symbolic", pixel_size=18
                    ),
                    css_classes=["task-action-btn", "task-snooze"],
                    tooltip_text="Snooze 5 minutes",
                    on_click=lambda x: self._on_snooze(task, 5),
                ),
                widgets.Button(
                    child=widgets.Icon(image="document-edit-symbolic", pixel_size=18),
                    css_classes=["task-action-btn", "task-edit"],
                    tooltip_text="Edit",
                    on_click=lambda x: self._on_edit(task),
                ),
                widgets.Button(
                    child=widgets.Icon(image="emblem-ok-symbolic", pixel_size=18),
                    css_classes=["task-action-btn", "task-complete"],
                    tooltip_text="Complete",
                    on_click=lambda x: self._on_complete(task),
                ),
                widgets.Button(
                    child=widgets.Icon(image="user-trash-symbolic", pixel_size=18),
                    css_classes=["task-action-btn", "task-delete"],
                    tooltip_text="Delete",
                    on_click=lambda x: self._on_delete(task),
                ),
            ],
        )

        main_col = widgets.Box(
            vertical=True,
            hexpand=True,
            spacing=4,
            child=[task_info, actions_row],
        )

        super().__init__(
            css_classes=["task-item"],
            spacing=12,
            child=[widgets.Icon(image="alarm-symbolic", pixel_size=24), main_col],
        )


class AddTaskDialog(widgets.Box):
    """Dialog to add a new task (with manual date support)"""

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
        """Set date offset (0=today, 1=tomorrow) and update date entry"""
        self._date_offset = offset
        base = datetime.now() + timedelta(days=offset)
        self._date_entry.text = base.strftime("%d-%m")

    def _add_task(self):
        """Parse and add the task (supports manual date)"""
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
    """Dialog to edit an existing task"""

    def __init__(self, task, on_save, on_cancel):
        self._task = task
        self._on_save = on_save
        self._on_cancel = on_cancel

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
            css_classes=["add-task-dialog", "edit-task-dialog"],
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
        """Validate and send updated task back to menu"""
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


class TaskMenu(widgets.Window):
    """Graphical task manager"""

    def __init__(self):
        self._task_list = widgets.Box(vertical=True, css_classes=["task-list"])
        # 👇 SCROLLBAR DISABLED HERE
        self._task_scroll = widgets.Scroll(
            vexpand=True,
            child=self._task_list,
            css_classes=["task-scroll"],
            vscrollbar_policy="never",  # Added this to disable vertical scrollbar
        )

        self._add_btn = widgets.Button(
            child=widgets.Box(
                child=[
                    widgets.Icon(image="list-add-symbolic", pixel_size=20),
                    widgets.Label(label="Add Task", style="margin-left: 8px;"),
                ]
            ),
            css_classes=["add-task-btn"],
            on_click=lambda x: self._show_add_dialog(),
        )

        self._header = widgets.Box(
            css_classes=["task-header"],
            child=[
                widgets.Label(
                    label="Tasks & Timers",
                    css_classes=["task-menu-title"],
                    halign="start",
                    hexpand=True,
                ),
                self._add_btn,
            ],
        )

        self._main_content = widgets.Box(
            vertical=True,
            css_classes=["task-menu"],
            child=[self._header, self._task_scroll],
        )

        overlay = widgets.Button(
            vexpand=True,
            hexpand=True,
            css_classes=["task-overlay"],
            can_focus=False,
            on_click=lambda x: self._close(),
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_TASK_MENU",
            layer="top",
            css_classes=["task-menu-window"],
            child=widgets.Overlay(
                child=overlay,
                overlays=[
                    widgets.Box(
                        valign="start",
                        halign="center",
                        style="margin-top: 8rem;",
                        child=[self._main_content],
                    )
                ],
            ),
            kb_mode="on_demand",
            setup=lambda self: self.connect("notify::visible", self._on_open),
        )

    def _on_open(self, *args):
        if self.visible:
            self._show_task_list()

    def _show_task_list(self):
        self._main_content.child = [self._header, self._task_scroll]
        self._reload_tasks()

    def _reload_tasks(self):
        tasks = load_tasks()
        now_ts = int(time.time())

        active_tasks = sorted(
            [t for t in tasks if t.get("fire_at", 0) > now_ts],
            key=lambda t: t["fire_at"],
        )

        if not active_tasks:
            self._task_list.child = [
                widgets.Label(label="No active tasks", css_classes=["task-empty"])
            ]
        else:
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

    def _show_add_dialog(self):
        self._main_content.child = [
            AddTaskDialog(on_add=self._add_task, on_cancel=self._cancel_add)
        ]

    def _open_edit_dialog(self, task):
        self._main_content.child = [
            EditTaskDialog(
                task,
                on_save=lambda new: self._update_task(task, new),
                on_cancel=self._cancel_add,
            )
        ]

    def _cancel_add(self):
        self._show_task_list()

    def _add_task(self, task):
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        self._show_task_list()

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
        self._show_task_list()

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

    def _close(self):
        self.visible = False
        self._show_task_list()


task_menu = TaskMenu()


def toggle_task_menu():
    task_menu.visible = not task_menu.visible
