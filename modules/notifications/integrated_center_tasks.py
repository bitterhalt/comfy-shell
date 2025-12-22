"""
Task/timer management for integrated center - OPTIMIZED
"""

import time
from datetime import datetime, timedelta
from typing import Dict

from ignis import utils, widgets
from modules.notifications.storage_manager import TaskStorageManager
from modules.notifications.widgets import (
    AddTaskDialog,
    EditTaskDialog,
    TaskItem,
    format_time_until,
)
from settings import config

# Create storage manager instance (shared across all instances)
_storage_manager = TaskStorageManager(config.paths.timer_queue)


class TaskList:
    """Manages the task list in the integrated center"""

    def __init__(self, on_show_dialog):
        self._on_show_dialog = on_show_dialog
        self._storage = _storage_manager

        # Task list container
        self._task_list = widgets.Box(vertical=True, css_classes=["content-list"])

        # Empty state
        self._task_empty = widgets.Label(
            label="No tasks",
            css_classes=["empty-state"],
            valign="center",
        )

        # Scrollable container
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
        """Reload tasks from storage (uses cache for performance)"""
        now = int(time.time())

        # Single cached read
        all_tasks = self._storage.load_tasks()

        # Filter and sort in memory
        pending_tasks = [task for task in all_tasks if task.get("fire_at", 0) > now]
        pending_tasks.sort(key=lambda t: t["fire_at"])

        # Update UI
        self._task_list.child = [
            TaskItem(
                task,
                self._delete_task,
                self._complete_task,
                self._open_edit_dialog,
                self._snooze_task,
            )
            for task in pending_tasks
        ]
        self._task_empty.visible = len(pending_tasks) == 0

        # Update next task pill
        self._update_next_task_pill(pending_tasks)

        return True

    def _update_next_task_pill(self, pending_tasks: list):
        """Update the next task pill display"""
        if not pending_tasks:
            self._next_task_title.label = "No tasks for today"
            self._next_task_meta.visible = False
            return

        next_task = pending_tasks[0]
        fire_timestamp = next_task["fire_at"]
        fire_dt = datetime.fromtimestamp(fire_timestamp)

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        if fire_dt.date() == today:
            day_label = "Today"
        elif fire_dt.date() == tomorrow:
            day_label = "Tomorrow"
        else:
            day_label = fire_dt.strftime("%d.%m")

        time_label = fire_dt.strftime("%H:%M")
        remaining = format_time_until(fire_timestamp)

        self._next_task_title.label = next_task.get("message", "")
        self._next_task_meta.label = f"{day_label} • {time_label} • {remaining}"
        self._next_task_meta.visible = True

    # ═══════════════════════════════════════════════════════════════
    # Task Operations - All use batch_update for single read/write
    # ═══════════════════════════════════════════════════════════════

    def _add_task(self, task: Dict):
        """Add task with single write operation"""
        if self._storage.batch_update(lambda tasks: tasks + [task]):
            self.reload()

    def _update_task(self, old_task: Dict, new_task: Dict):
        """Update task with single read/write"""

        def update_op(tasks):
            return [new_task if t == old_task else t for t in tasks]

        if self._storage.batch_update(update_op):
            self.reload()

    def _delete_task(self, task: Dict):
        """Delete task with single read/write"""

        def delete_op(tasks):
            return [t for t in tasks if t != task]

        if self._storage.batch_update(delete_op):
            self.reload()

    def _complete_task(self, task: Dict):
        """Mark task as complete"""
        self._delete_task(task)

    def _snooze_task(self, task: Dict, minutes: int = 5):
        """Snooze task with single read/write"""
        now = int(time.time())
        new_fire_time = now + (minutes * 60)

        def snooze_op(tasks):
            return [{**t, "fire_at": new_fire_time} if t == task else t for t in tasks]

        if self._storage.batch_update(snooze_op):
            self.reload()

    # Dialog management
    def _open_add_dialog(self):
        dialog = AddTaskDialog(
            on_add=lambda task: (self._add_task(task), self._on_show_dialog(None)),
            on_cancel=lambda *_: self._on_show_dialog(None),
        )
        self._on_show_dialog(dialog)

    def _open_edit_dialog(self, task):
        dialog = EditTaskDialog(
            task,
            on_save=lambda new: (
                self._update_task(task, new),
                self._on_show_dialog(None),
            ),
            on_cancel=lambda *_: self._on_show_dialog(None),
        )
        self._on_show_dialog(dialog)
