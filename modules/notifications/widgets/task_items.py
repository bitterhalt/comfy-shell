"""
Task item widgets for the integrated center
"""

from datetime import datetime

from ignis import widgets
from modules.notifications.widgets.time_utils import format_time_until


class TaskItem(widgets.Box):
    """A single scheduled task item"""

    def __init__(self, task, on_delete, on_complete, on_edit, on_snooze):
        self._task = task

        fire_dt = datetime.fromtimestamp(task["fire_at"])
        time_str = fire_dt.strftime("%H:%M")
        date_str = fire_dt.strftime("%d.%m")

        text_box = widgets.Box(
            vertical=True,
            spacing=4,
            hexpand=True,
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

        actions = widgets.Box(
            halign="center",
            spacing=6,
            css_classes=["task-actions-row"],
            child=[
                widgets.Button(
                    child=widgets.Icon(image="document-edit-symbolic", pixel_size=16),
                    css_classes=["task-action-btn", "task-edit"],
                    tooltip_text="Edit Task",
                    on_click=lambda *_: on_edit(task),
                ),
                widgets.Button(
                    child=widgets.Icon(image="emblem-ok-symbolic", pixel_size=16),
                    css_classes=["task-action-btn", "task-complete"],
                    tooltip_text="Complete",
                    on_click=lambda *_: on_complete(task),
                ),
                widgets.Button(
                    child=widgets.Icon(image="user-trash-symbolic", pixel_size=16),
                    css_classes=["task-action-btn", "task-delete"],
                    tooltip_text="Delete",
                    on_click=lambda *_: on_delete(task),
                ),
            ],
        )

        super().__init__(
            css_classes=["task-item"],
            spacing=12,
            child=[
                widgets.Box(vertical=True, spacing=6, child=[text_box, actions]),
            ],
        )
