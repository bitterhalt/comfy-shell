import json
import time
from datetime import datetime
from pathlib import Path

from ignis import widgets

# Configuration (matching your fuzzel_task.py)
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

    def __init__(self, task, on_delete, on_complete):
        self._task = task
        self._on_delete = on_delete
        self._on_complete = on_complete

        fire_dt = datetime.fromtimestamp(task["fire_at"])
        time_str = fire_dt.strftime("%H:%M")
        date_str = fire_dt.strftime("%d.%m")

        # Task info
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

        # Action buttons
        complete_btn = widgets.Button(
            child=widgets.Icon(image="emblem-ok-symbolic", pixel_size=18),
            css_classes=["task-action-btn", "task-complete"],
            tooltip_text="Complete",
            on_click=lambda x: self._on_complete(task),
        )

        delete_btn = widgets.Button(
            child=widgets.Icon(image="user-trash-symbolic", pixel_size=18),
            css_classes=["task-action-btn", "task-delete"],
            tooltip_text="Delete",
            on_click=lambda x: self._on_delete(task),
        )

        super().__init__(
            css_classes=["task-item"],
            child=[
                widgets.Icon(image="alarm-symbolic", pixel_size=24),
                task_info,
                complete_btn,
                delete_btn,
            ],
            spacing=12,
        )


class AddTaskDialog(widgets.Box):
    """Dialog to add a new task"""

    def __init__(self, on_add, on_cancel):
        self._on_add = on_add
        self._on_cancel = on_cancel

        # Task message input
        self._message_entry = widgets.Entry(
            placeholder_text="Task description...",
            css_classes=["task-input"],
            hexpand=True,
        )

        # Time input (HH:MM format)
        self._time_entry = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input"],
            width_request=80,
        )

        # Date offset buttons
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

        self._date_offset = 0
        self._selected_date_label = widgets.Label(
            label="Today",
            css_classes=["selected-date"],
        )

        # Action buttons
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
            child=[
                widgets.Label(
                    label="Add New Task",
                    css_classes=["dialog-title"],
                    halign="start",
                ),
                self._message_entry,
                widgets.Box(
                    child=[
                        widgets.Label(label="Time:", css_classes=["input-label"]),
                        self._time_entry,
                    ],
                    spacing=8,
                ),
                widgets.Box(
                    child=[
                        widgets.Label(label="Date:", css_classes=["input-label"]),
                        today_btn,
                        tomorrow_btn,
                        self._selected_date_label,
                    ],
                    spacing=8,
                ),
                widgets.Box(
                    child=[cancel_btn, add_btn],
                    spacing=8,
                    halign="end",
                ),
            ],
            spacing=12,
        )

    def _set_date(self, offset):
        """Set date offset (0=today, 1=tomorrow)"""
        self._date_offset = offset
        if offset == 0:
            self._selected_date_label.label = "Today"
        else:
            self._selected_date_label.label = "Tomorrow"

    def _add_task(self):
        """Parse and add the task"""
        message = self._message_entry.text.strip()
        time_str = self._time_entry.text.strip()

        if not message or not time_str:
            return

        try:
            # Parse time (HH:MM)
            hour, minute = map(int, time_str.split(":"))

            # Calculate fire time
            now = datetime.now()
            fire_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Add date offset
            if self._date_offset == 1:
                from datetime import timedelta

                fire_dt += timedelta(days=1)

            # If time is in the past for today, move to tomorrow
            if self._date_offset == 0 and fire_dt < now:
                from datetime import timedelta

                fire_dt += timedelta(days=1)

            task = {
                "message": message,
                "fire_at": int(fire_dt.timestamp()),
            }

            self._on_add(task)
        except ValueError:
            # Invalid time format
            pass


class TaskMenu(widgets.Window):
    """Graphical task manager"""

    def __init__(self):
        # Task list
        self._task_list = widgets.Box(
            vertical=True,
            css_classes=["task-list"],
        )

        # Scrollable task list
        self._task_scroll = widgets.Scroll(
            vexpand=True,
            child=self._task_list,
            css_classes=["task-scroll"],
        )

        # Add task button
        self._add_btn = widgets.Button(
            child=widgets.Box(
                child=[
                    widgets.Icon(image="list-add-symbolic", pixel_size=20),
                    widgets.Label(label="Add Task", style="margin-left: 8px;"),
                ],
            ),
            css_classes=["add-task-btn"],
            on_click=lambda x: self._show_add_dialog(),
        )

        # Header
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

        # Main content container
        self._main_content = widgets.Box(
            vertical=True,
            css_classes=["task-menu"],
            child=[self._header, self._task_scroll],
        )

        # Overlay
        overlay = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["task-overlay"],
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
        """Reload tasks when opened"""
        if self.visible:
            self._show_task_list()

    def _show_task_list(self):
        """Show main task list view"""
        # Restore header with Add button
        self._main_content.child = [self._header, self._task_scroll]
        self._reload_tasks()

    def _reload_tasks(self):
        """Reload and display tasks"""
        tasks = load_tasks()

        # Filter active tasks (not past)
        now_ts = int(time.time())
        active_tasks = sorted(
            [t for t in tasks if t.get("fire_at", 0) > now_ts],
            key=lambda t: t["fire_at"],
        )

        if not active_tasks:
            self._task_list.child = [
                widgets.Label(
                    label="No active tasks",
                    css_classes=["task-empty"],
                )
            ]
        else:
            self._task_list.child = [
                TaskItem(task, self._delete_task, self._complete_task)
                for task in active_tasks
            ]

    def _show_add_dialog(self):
        """Show add task dialog"""
        dialog = AddTaskDialog(
            on_add=self._add_task,
            on_cancel=self._cancel_add,
        )
        # Replace entire content with dialog
        self._main_content.child = [dialog]

    def _cancel_add(self):
        """Cancel adding task and return to list"""
        self._show_task_list()

    def _add_task(self, task):
        """Add a new task"""
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        # Return to task list after adding
        self._show_task_list()

    def _delete_task(self, task):
        """Delete a task"""
        tasks = load_tasks()
        tasks = [t for t in tasks if t != task]
        save_tasks(tasks)
        self._reload_tasks()

    def _complete_task(self, task):
        """Mark task as complete (delete it)"""
        self._delete_task(task)

    def _close(self):
        """Close the menu"""
        self.visible = False
        # Make sure we're showing task list when reopened
        self._show_task_list()


# Create the task menu window
task_menu = TaskMenu()


def toggle_task_menu():
    """Toggle task menu visibility"""
    task_menu.visible = not task_menu.visible
