"""
Task popup
"""

import time
from datetime import datetime

from ignis import utils, widgets
from modules.utils.task_storage_manager import TaskStorageManager
from settings import config

_storage_manager = TaskStorageManager(config.paths.timer_queue)


class TaskPopup(widgets.Revealer):
    """Individual task notification popup"""

    def __init__(self, task, parent_window):
        self._task = task
        self._parent_window = parent_window

        icon = widgets.Icon(
            image="alarm-symbolic",
            pixel_size=48,
            halign="start",
            valign="start",
            css_classes=["task-popup-icon"],
        )

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

        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=20),
            css_classes=["close-btn"],
            valign="start",
            on_click=lambda x: self._dismiss(),
        )

        header = widgets.Box(
            spacing=12,
            child=[icon, text_box, close_btn],
        )

        complete_btn = widgets.Button(
            child=widgets.Label(label="Complete"),
            css_classes=["task-popup-action", "complete-btn"],
            on_click=lambda x: self._complete(),
        )

        action_box = widgets.Box(
            spacing=8,
            halign="end",
            css_classes=["task-popup-actions"],
            child=[complete_btn],
        )

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
        self._shown_tasks = set()

        super().__init__(
            anchor=["right", "top"],
            monitor=monitor,
            namespace=f"ignis_TASK_POPUP_{monitor}",
            layer="top",
            child=self._popup_box,
            visible=False,
            css_classes=["task-popup-window"],
        )

        self._check_tasks()
        self._check_poll = utils.Poll(60000, self._check_tasks)
        self.connect("destroy", self._cleanup)

    def _cleanup(self, *_):
        """Cancel poll on destroy"""
        if hasattr(self, "_check_poll") and self._check_poll:
            try:
                self._check_poll.cancel()
            except:
                pass
            self._check_poll = None

    def _check_tasks(self, *args):
        """Check for tasks that are due and show popups"""
        all_tasks = _storage_manager.load_tasks(force_refresh=True)
        now = int(time.time())

        for task in all_tasks:
            fire_at = task.get("fire_at", 0)
            task_id = (task.get("message", ""), fire_at)

            if fire_at <= now and fire_at > (now - 120):
                if task_id in self._shown_tasks:
                    continue

                self._show_popup(task)
                self._shown_tasks.add(task_id)

        cutoff = now - 300
        self._shown_tasks = {(msg, t) for msg, t in self._shown_tasks if t > cutoff}

        return True

    def _show_popup(self, task):
        """Show a popup for a due task"""
        self.visible = True

        popup = TaskPopup(task, self)
        self._popup_box.prepend(popup)

        utils.Timeout(10, popup.set_reveal_child, True)

    def _check_if_empty(self):
        """Hide window if no popups remain"""
        utils.Timeout(350, self._do_check)

    def _do_check(self):
        if len(self._popup_box.child) == 0:
            self.visible = False


_task_popup_window = None


def init_task_popup():
    global _task_popup_window
    if _task_popup_window is None:
        monitor = config.ui.notifications_monitor
        _task_popup_window = TaskPopupWindow(monitor)
