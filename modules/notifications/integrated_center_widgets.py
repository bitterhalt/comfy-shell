import time
from datetime import datetime, timedelta

from ignis import widgets
from ignis.services.notifications import Notification

# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────


def format_time_until(fire_at: int) -> str:
    """Human-friendly time delta stroot_overlaying for a future timestamp."""
    now = int(time.time())
    diff = fire_at - now
    if diff < 0:
        return "Overdue!"
    hours = diff // 3600
    minutes = (diff % 3600) // 60
    if hours >= 24:
        return f"{hours // 24}d {hours % 24}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION HISTORY ITEM
# ═══════════════════════════════════════════════════════════════


class NotificationHistoryItem(widgets.Box):
    """Item shown in the Integrated Center's notification list."""

    def __init__(self, notification: Notification):

        # --- ICON OR DOT -----------------------------------------------------
        if notification.icon:
            icon_widget = widgets.Icon(
                image=notification.icon,
                pixel_size=32,
                halign="start",
                valign="start",
                css_classes=["notif-history-icon"],
            )
        else:
            dot_color = "critical" if notification.urgency == 2 else "normal"
            icon_widget = widgets.Label(
                label="●",
                css_classes=["notif-popup-dot", dot_color],
                halign="start",
                valign="start",
            )

        # --- TITLE -----------------------------------------------------------
        title_css_classes = ["notif-history-title"]
        if notification.urgency == 2:
            title_css_classes.append("critical")

        summary = widgets.Label(
            label=notification.summary,
            halign="start",
            ellipsize="end",
            max_width_chars=35,
            css_classes=title_css_classes,
            wrap=True,
        )

        # --- BODY ------------------------------------------------------------
        body = widgets.Label(
            label=notification.body,
            halign="start",
            ellipsize="end",
            max_width_chars=40,
            css_classes=["notif-history-body"],
            visible=notification.body != "",
            wrap=True,
        )

        # --- CLOSE BUTTON ----------------------------------------------------
        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=18),
            css_classes=["notif-history-close"],
            valign="start",
            on_click=lambda *_: notification.close(),
        )

        # --- TEXT CONTAINER --------------------------------------------------
        text_box = widgets.Box(
            vertical=True,
            spacing=4,
            child=[summary, body],
            hexpand=True,
        )

        # --- MAIN ROW --------------------------------------------------------
        super().__init__(
            css_classes=["notif-history-item"],
            spacing=12,
            child=[icon_widget, text_box, close_btn],
        )

        # When closed → hide
        notification.connect("closed", lambda *_: setattr(self, "visible", False))


# ═══════════════════════════════════════════════════════════════
# TASK ITEM
# ═══════════════════════════════════════════════════════════════


class TaskItem(widgets.Box):
    """A single scheduled task item in the center list."""

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


# ═══════════════════════════════════════════════════════════════
# ADD TASK DIALOG
# ═══════════════════════════════════════════════════════════════


class AddTaskDialog(widgets.Box):
    """Dialog for creating a new task."""

    def __init__(self, on_add, on_cancel):
        self._on_add = on_add
        self._on_cancel = on_cancel

        now = datetime.now()

        # Message - FIXED: Initialize text properly
        self._message = widgets.Entry(
            placeholder_text="Task description...",
            css_classes=["task-input"],
            hexpand=True,
        )
        self._message.text = ""

        # Time - FIXED: Initialize text properly
        self._time = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input"],
            width_request=100,
        )
        self._time.text = ""  # Empty initially, user will fill

        # Date
        self._date = widgets.Entry(
            placeholder_text="DD-MM-YYYY",
            css_classes=["task-input"],
            width_request=140,
        )
        self._date.text = now.strftime("%d-%m-%Y")

        # Quick date buttons
        today_btn = widgets.Button(
            child=widgets.Label(label="Today"),
            css_classes=["date-btn"],
            on_click=lambda *_: self._set_date_offset(0),
        )

        tomorrow_btn = widgets.Button(
            child=widgets.Label(label="Tomorrow"),
            css_classes=["date-btn"],
            on_click=lambda *_: self._set_date_offset(1),
        )

        # Footer buttons
        cancel_btn = widgets.Button(
            child=widgets.Label(label="Cancel"),
            css_classes=["dialog-btn", "cancel-btn"],
            on_click=lambda *_: on_cancel(),
        )

        save_btn = widgets.Button(
            child=widgets.Label(label="Add Task"),
            css_classes=["dialog-btn", "add-btn"],
            on_click=lambda *_: self._add(),
        )

        super().__init__(
            vertical=True,
            spacing=18,
            css_classes=["add-task-dialog"],
            child=[
                widgets.Label(label="Add New Task", css_classes=["dialog-title"]),
                widgets.Box(spacing=12, child=[self._message]),
                widgets.Box(
                    spacing=12,
                    child=[
                        widgets.Label(label="Time:", css_classes=["input-label"]),
                        self._time,
                    ],
                ),
                widgets.Box(
                    spacing=12,
                    child=[
                        widgets.Label(label="Date:", css_classes=["input-label"]),
                        self._date,
                        today_btn,
                        tomorrow_btn,
                    ],
                ),
                widgets.Box(
                    css_classes=["dialog-footer"], child=[cancel_btn, save_btn]
                ),
            ],
        )

    def _set_date_offset(self, offset):
        date = datetime.now() + timedelta(days=offset)
        self._date.text = date.strftime("%d-%m-%Y")

    def _add(self):
        msg = self._message.text.strip()
        time_str = self._time.text.strip()
        date_str = self._date.text.strip()

        if not msg or not time_str or not date_str:
            return

        try:
            hour, minute = map(int, time_str.split(":"))
            day, mon, year = map(int, date_str.split("-"))

            dt = datetime(year, mon, day, hour, minute)

            if dt <= datetime.now():
                dt += timedelta(days=1)

            self._on_add({"message": msg, "fire_at": int(dt.timestamp())})
        except Exception:
            return


# ═══════════════════════════════════════════════════════════════
# EDIT TASK DIALOG
# ═══════════════════════════════════════════════════════════════


class EditTaskDialog(widgets.Box):
    """Dialog for editing an existing task."""

    def __init__(self, task, on_save, on_cancel):
        self._task = task
        self._on_save = on_save

        fire_dt = datetime.fromtimestamp(task["fire_at"])

        self._message = widgets.Entry(
            placeholder_text="Task description...",
            css_classes=["task-input"],
            hexpand=True,
        )
        self._message.text = task.get("message", "")

        self._time = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input"],
            width_request=100,
        )
        self._time.text = fire_dt.strftime("%H:%M")

        self._date = widgets.Entry(
            placeholder_text="DD-MM-YYYY",
            css_classes=["task-input"],
            width_request=140,
        )
        self._date.text = fire_dt.strftime("%d-%m-%Y")

        cancel_btn = widgets.Button(
            child=widgets.Label(label="Cancel"),
            css_classes=["dialog-btn", "cancel-btn"],
            on_click=lambda *_: on_cancel(),
        )

        save_btn = widgets.Button(
            child=widgets.Label(label="Save"),
            css_classes=["dialog-btn", "add-btn"],
            on_click=lambda *_: self._save(),
        )

        super().__init__(
            vertical=True,
            spacing=18,
            css_classes=["add-task-dialog"],
            child=[
                widgets.Label(label="Edit Task", css_classes=["dialog-title"]),
                widgets.Box(spacing=12, child=[self._message]),
                widgets.Box(
                    spacing=12,
                    child=[
                        widgets.Label(label="Time:", css_classes=["input-label"]),
                        self._time,
                    ],
                ),
                widgets.Box(
                    spacing=12,
                    child=[
                        widgets.Label(label="Date:", css_classes=["input-label"]),
                        self._date,
                    ],
                ),
                widgets.Box(
                    css_classes=["dialog-footer"], child=[cancel_btn, save_btn]
                ),
            ],
        )

    def _save(self):
        msg = self._message.text.strip()
        time_str = self._time.text.strip()
        date_str = self._date.text.strip()

        if not msg or not time_str or not date_str:
            return

        try:
            hour, minute = map(int, time_str.split(":"))
            day, mon, year = map(int, date_str.split("-"))

            dt = datetime(year, mon, day, hour, minute)

            if dt <= datetime.now():
                return

            new_task = dict(self._task)
            new_task["message"] = msg
            new_task["fire_at"] = int(dt.timestamp())

            self._on_save(new_task)
        except Exception:
            return
