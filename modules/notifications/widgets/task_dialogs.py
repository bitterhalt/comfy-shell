"""
Task add/edit dialog widgets
"""

from datetime import datetime, timedelta

from ignis import widgets


class AddTaskDialog(widgets.Box):
    """Dialog for creating a new task"""

    def __init__(self, on_add, on_cancel):
        self._on_add = on_add
        self._on_cancel = on_cancel

        now = datetime.now()

        # Time input
        self._time = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input", "task-time-input"],
        )
        self._time.text = ""

        # Date input
        self._date = widgets.Entry(
            placeholder_text="DD-MM-YYYY",
            css_classes=["task-input", "task-date-input"],
        )
        self._date.text = now.strftime("%d-%m-%Y")

        # Quick date button
        tomorrow_btn = widgets.Button(
            child=widgets.Label(label="Tomorrow"),
            css_classes=["date-quick-btn"],
            on_click=lambda *_: self._set_date_offset(1),
        )

        time_row = widgets.Box(
            spacing=8,
            css_classes=["task-dialog-time-row"],
            child=[
                widgets.Label(label="⏰", css_classes=["task-emoji-label"]),
                self._time,
                self._date,
                tomorrow_btn,
            ],
        )

        # Message input
        self._message = widgets.Entry(
            placeholder_text="What do you need to do?",
            css_classes=["task-input", "task-message-input"],
            hexpand=True,
            on_accept=lambda *_: self._add(),
        )
        self._message.text = ""

        # Buttons
        cancel_btn = widgets.Button(
            child=widgets.Label(label="Cancel"),
            css_classes=["task-dialog-btn", "cancel-btn"],
            on_click=lambda *_: on_cancel(),
        )

        save_btn = widgets.Button(
            child=widgets.Label(label="Add Task"),
            css_classes=["task-dialog-btn", "add-btn"],
            on_click=lambda *_: self._add(),
        )

        button_row = widgets.Box(
            spacing=8,
            halign="end",
            css_classes=["task-dialog-buttons"],
            child=[cancel_btn, save_btn],
        )

        super().__init__(
            vertical=True,
            spacing=12,
            css_classes=["task-dialog-compact"],
            child=[
                widgets.Label(label="New Task", css_classes=["task-dialog-title"]),
                time_row,
                self._message,
                button_row,
            ],
        )

        self._time.grab_focus()

    def _set_date_offset(self, offset):
        """Set date to today + offset days"""
        date = datetime.now() + timedelta(days=offset)
        self._date.text = date.strftime("%d-%m-%Y")

    def _add(self):
        """Validate and add task"""
        msg = self._message.text.strip()
        time_str = self._time.text.strip()
        date_str = self._date.text.strip()

        if not msg or not time_str or not date_str:
            return

        try:
            hour, minute = map(int, time_str.split(":"))
            day, mon, year = map(int, date_str.split("-"))

            dt = datetime(year, mon, day, hour, minute)

            # If time is in the past, assume next occurrence
            if dt <= datetime.now():
                dt += timedelta(days=1)

            self._on_add({"message": msg, "fire_at": int(dt.timestamp())})
        except Exception:
            # Invalid input - silently ignore
            return


class EditTaskDialog(widgets.Box):
    """Dialog for editing an existing task"""

    def __init__(self, task, on_save, on_cancel):
        self._task = task
        self._on_save = on_save

        fire_dt = datetime.fromtimestamp(task["fire_at"])

        # Time input
        self._time = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input", "task-time-input"],
        )
        self._time.text = fire_dt.strftime("%H:%M")

        # Date input
        self._date = widgets.Entry(
            placeholder_text="DD-MM-YYYY",
            css_classes=["task-input", "task-date-input"],
        )
        self._date.text = fire_dt.strftime("%d-%m-%Y")

        time_row = widgets.Box(
            spacing=8,
            css_classes=["task-dialog-time-row"],
            child=[
                widgets.Label(label="⏰", css_classes=["task-emoji-label"]),
                self._time,
                self._date,
            ],
        )

        # Message input
        self._message = widgets.Entry(
            placeholder_text="What do you need to do?",
            css_classes=["task-input", "task-message-input"],
            hexpand=True,
            on_accept=lambda *_: self._save(),
        )
        self._message.text = task.get("message", "")

        # Buttons
        cancel_btn = widgets.Button(
            child=widgets.Label(label="Cancel"),
            css_classes=["task-dialog-btn", "cancel-btn"],
            on_click=lambda *_: on_cancel(),
        )

        save_btn = widgets.Button(
            child=widgets.Label(label="Save"),
            css_classes=["task-dialog-btn", "add-btn"],
            on_click=lambda *_: self._save(),
        )

        button_row = widgets.Box(
            spacing=8,
            halign="end",
            css_classes=["task-dialog-buttons"],
            child=[cancel_btn, save_btn],
        )

        super().__init__(
            vertical=True,
            spacing=12,
            css_classes=["task-dialog-compact"],
            child=[
                widgets.Label(label="Edit Task", css_classes=["task-dialog-title"]),
                time_row,
                self._message,
                button_row,
            ],
        )

        self._message.grab_focus()

    def _save(self):
        """Validate and save changes"""
        msg = self._message.text.strip()
        time_str = self._time.text.strip()
        date_str = self._date.text.strip()

        if not msg or not time_str or not date_str:
            return

        try:
            hour, minute = map(int, time_str.split(":"))
            day, mon, year = map(int, date_str.split("-"))

            dt = datetime(year, mon, day, hour, minute)

            # Don't allow setting task in the past
            if dt <= datetime.now():
                return

            new_task = dict(self._task)
            new_task["message"] = msg
            new_task["fire_at"] = int(dt.timestamp())

            self._on_save(new_task)
        except Exception:
            return
