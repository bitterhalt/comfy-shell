"""
Task/timer management for integrated center
"""

import fcntl
import json
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

from ignis import utils, widgets

# Clean imports from widgets package
from modules.notifications.widgets import (
    AddTaskDialog,
    EditTaskDialog,
    TaskItem,
    format_time_until,
)
from settings import config

QUEUE_FILE = config.paths.timer_queue


# ============================================================================
# File locking helpers
# ============================================================================


@contextmanager
def _locked_queue_file(mode: str = "r"):
    """File lock helper for the timer/task JSON."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not QUEUE_FILE.exists():
        QUEUE_FILE.write_text("[]")

    with open(QUEUE_FILE, mode, encoding="utf-8") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_tasks():
    try:
        with _locked_queue_file("r") as f:
            txt = f.read()
            return json.loads(txt) if txt.strip() else []
    except Exception:
        return []


def save_tasks(tasks):
    try:
        with _locked_queue_file("w") as f:
            json.dump(tasks, f, indent=2)
    except Exception:
        pass


# ============================================================================
# Task list widget
# ============================================================================


class TaskList:
    """Manages the task list in the integrated center"""

    def __init__(self, on_show_dialog):
        self._on_show_dialog = on_show_dialog

        # Task list container
        self._task_list = widgets.Box(vertical=True, css_classes=["content-list"])

        # Empty state
        self._task_empty = widgets.Label(
            label="No tasks",
            css_classes=["empty-state"],
            valign="center",
        )

        # Scrollable container (initially hidden)
        self.scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            visible=False,
            child=widgets.Box(
                vertical=True,
                child=[self._task_list, self._task_empty],
            ),
        )

        # Next task pill
        self._next_task_title = widgets.Label(
            label="No tasks for today",
            ellipsize="end",
            max_width_chars=30,
            css_classes=["next-task-title"],
        )
        self._next_task_meta = widgets.Label(
            label="",
            visible=False,
            css_classes=["next-task-meta"],
        )

        self.next_task_box = widgets.Box(
            spacing=8,
            css_classes=["next-task-box"],
            child=[
                widgets.Box(
                    vertical=True,
                    hexpand=True,
                    css_classes=["next-task-text-column"],
                    child=[self._next_task_title, self._next_task_meta],
                ),
                widgets.Button(
                    child=widgets.Label(label="Add Task"),
                    css_classes=["add-task-btn"],
                    on_click=lambda *_: self._open_add_dialog(),
                ),
            ],
        )

        # Initial load
        self.reload()

        # Periodic refresh
        utils.Poll(30000, lambda *_: self.reload())

    def reload(self):
        """Reload tasks from file"""
        now = int(time.time())
        tasks = [t for t in load_tasks() if t.get("fire_at", 0) > now]
        tasks.sort(key=lambda t: t["fire_at"])

        # Update full list
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

        # Update next task pill
        if tasks:
            nxt = tasks[0]
            fire = nxt["fire_at"]
            fire_dt = datetime.fromtimestamp(fire)

            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            if fire_dt.date() == today:
                day = "Today"
            elif fire_dt.date() == tomorrow:
                day = "Tomorrow"
            else:
                day = fire_dt.strftime("%d.%m")

            time_label = fire_dt.strftime("%H:%M")
            remain = format_time_until(fire)

            self._next_task_title.label = nxt.get("message", "")
            self._next_task_meta.label = f"{day} • {time_label} • {remain}"
            self._next_task_meta.visible = True
        else:
            self._next_task_title.label = "No tasks for today"
            self._next_task_meta.visible = False

        return True

    # Task actions
    def _add_task(self, task):
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        self.reload()

    def _update_task(self, old, new):
        tasks = load_tasks()
        out = []
        replaced = False
        for t in tasks:
            if not replaced and t == old:
                out.append(new)
                replaced = True
            else:
                out.append(t)
        save_tasks(out)
        self.reload()

    def _delete_task(self, task):
        tasks = load_tasks()
        save_tasks([t for t in tasks if t != task])
        self.reload()

    def _complete_task(self, task):
        self._delete_task(task)

    def _snooze_task(self, task, minutes=5):
        now = int(time.time())
        tasks = load_tasks()
        out = []
        used = False
        for t in tasks:
            if not used and t == task:
                nt = dict(t)
                nt["fire_at"] = now + minutes * 60
                out.append(nt)
                used = True
            else:
                out.append(t)
        save_tasks(out)
        self.reload()

    # Dialog management
    def _open_add_dialog(self):
        dlg = AddTaskDialog(
            on_add=lambda task: (self._add_task(task), self._on_show_dialog(None)),
            on_cancel=lambda *_: self._on_show_dialog(None),
        )
        self._on_show_dialog(dlg)

    def _open_edit_dialog(self, task):
        dlg = EditTaskDialog(
            task,
            on_save=lambda new: (
                self._update_task(task, new),
                self._on_show_dialog(None),
            ),
            on_cancel=lambda *_: self._on_show_dialog(None),
        )
        self._on_show_dialog(dlg)
