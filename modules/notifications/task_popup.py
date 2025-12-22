"""
Task popup - Fixed to use storage manager
"""

import time
from datetime import datetime

from ignis import utils, widgets
from modules.notifications.storage_manager import TaskStorageManager
from settings import config

# Use shared storage manager
_storage_manager = TaskStorageManager(config.paths.timer_queue)


class TaskPopup(widgets.Revealer):
    """Individual task notification popup"""

    def __init__(self, task, parent_window):
        self._task = task
        self._parent_window = parent_window

        # Task icon
        icon = widgets.Icon(
            image="alarm-symbolic",
            pixel_size=48,
            halign="start",
            valign="start",
            css_classes=["task-popup-icon"],
        )

        # Task message
        title = widgets.Label(
            label="Task Reminder",
            halign="start",
            css_classes=["task-popup-title"],
        )

        message = widgets.Label(
            label=task.get("message", "Task is due!"),
            halign="start",
            wrap=True,
            max_width_chars=30,
            css_classes=["task-popup-message"],
        )

        # Time info
        fire_dt = datetime.fromtimestamp(task.get("fire_at", time.time()))
        time_str = fire_dt.strftime("%H:%M")

        time_label = widgets.Label(
            label=f"Scheduled: {time_str}",
            halign="start",
            css_classes=["task-popup-time"],
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=4,
            hexpand=True,
            child=[title, message, time_label],
        )

        # Close button
        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=20),
            css_classes=["task-popup-close"],
            valign="start",
            on_click=lambda x: self._dismiss(),
        )

        # Content header
        header = widgets.Box(
            spacing=12,
            child=[icon, text_box, close_btn],
        )

        # Action buttons
        snooze_5_btn = widgets.Button(
            child=widgets.Label(label="5 min"),
            css_classes=["task-popup-action", "snooze-btn"],
            on_click=lambda x: self._snooze(5),
        )

        snooze_15_btn = widgets.Button(
            child=widgets.Label(label="15 min"),
            css_classes=["task-popup-action", "snooze-btn"],
            on_click=lambda x: self._snooze(15),
        )

        snooze_60_btn = widgets.Button(
            child=widgets.Label(label="1 hour"),
            css_classes=["task-popup-action", "snooze-btn"],
            on_click=lambda x: self._snooze(60),
        )

        complete_btn = widgets.Button(
            child=widgets.Label(label="Complete"),
            css_classes=["task-popup-action", "complete-btn"],
            on_click=lambda x: self._complete(),
        )

        action_box = widgets.Box(
            spacing=8,
            homogeneous=True,
            css_classes=["task-popup-actions"],
            child=[snooze_5_btn, snooze_15_btn, snooze_60_btn, complete_btn],
        )

        # Main container
        container = widgets.Box(
            vertical=True,
            spacing=12,
            css_classes=["task-popup-box"],
            child=[header, action_box],
        )

        super().__init__(
            transition_type="slide_down",
            transition_duration=300,
            reveal_child=False,
            child=container,
        )

    def _snooze(self, minutes):
        """Snooze task for specified minutes"""
        now = int(time.time())
        new_fire_at = now + (minutes * 60)

        # Update task using batch operation
        def snooze_op(tasks):
            return [
                {**t, "fire_at": new_fire_at} if t == self._task else t for t in tasks
            ]

        _storage_manager.batch_update(snooze_op)
        self._dismiss()

    def _complete(self):
        """Mark task as complete and remove it"""

        def delete_op(tasks):
            return [t for t in tasks if t != self._task]

        _storage_manager.batch_update(delete_op)
        self._dismiss()

    def _dismiss(self):
        """Dismiss the popup"""
        self.reveal_child = False
        utils.Timeout(self.transition_duration, self._cleanup)

    def _cleanup(self):
        """Remove popup and hide window if empty"""
        self.unparent()
        self._parent_window._check_if_empty()


class TaskPopupWindow(widgets.Window):
    """Window to display task notification popups"""

    def __init__(self, monitor: int = 0):
        self._popup_box = widgets.Box(
            vertical=True,
            valign="start",
            halign="end",
        )

        super().__init__(
            anchor=["right", "top"],
            monitor=monitor,
            namespace=f"ignis_TASK_POPUP_{monitor}",
            layer="top",
            child=self._popup_box,
            visible=False,
            css_classes=["task-popup-window"],
        )

        # Start checking for due tasks
        self._check_tasks()
        utils.Poll(30000, self._check_tasks)  # Check every 30 seconds

    def _check_tasks(self, *args):
        """Check for tasks that are due and show popups"""
        all_tasks = _storage_manager.load_tasks()
        now = int(time.time())

        for task in all_tasks:
            fire_at = task.get("fire_at", 0)

            # Check if task is due (within 1 minute window to avoid duplicates)
            if fire_at <= now and fire_at > (now - 60):
                # Check if popup already exists for this task
                already_shown = False
                for child in self._popup_box.child:
                    if hasattr(child, "_task") and child._task == task:
                        already_shown = True
                        break

                if not already_shown:
                    self._show_popup(task)

        return True

    def _show_popup(self, task):
        """Show a popup for a due task"""
        self.visible = True

        popup = TaskPopup(task, self)
        self._popup_box.prepend(popup)

        # Reveal after adding to DOM
        utils.Timeout(10, popup.set_reveal_child, True)

    def _check_if_empty(self):
        """Hide window if no popups remain"""
        utils.Timeout(350, self._do_check)

    def _do_check(self):
        if len(self._popup_box.child) == 0:
            self.visible = False


# Global instance
_task_popup_window = None


def init_task_popup():
    """Initialize task popup window (call once at startup)"""
    global _task_popup_window

    if _task_popup_window is None:
        monitor = config.ui.notifications_monitor
        _task_popup_window = TaskPopupWindow(monitor)
