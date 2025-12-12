import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from ignis import utils, widgets
from ignis.services.notifications import Notification

# ───────────────────────────────────────────────────────────────
# Screenshot preview cache
# ───────────────────────────────────────────────────────────────

CACHE_DIR = Path("~/.cache/ignis/screenshot_previews").expanduser()
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_preview(
    image_path: str,
    size: tuple[int, int],
    crop: bool = False,
) -> str:
    src = Path(image_path)

    # Cache key
    key = f"{src}:{size}:{crop}"
    digest = hashlib.sha1(key.encode()).hexdigest()
    cached = CACHE_DIR / f"{digest}.png"

    # Always prefer cached preview
    if cached.exists():
        return str(cached)

    # Cannot generate without source
    if not src.exists():
        return image_path

    try:
        img = Image.open(src)

        if crop:
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))

        img = img.resize(size, Image.LANCZOS)
        img.save(cached, "PNG")
        return str(cached)

    except Exception:
        return image_path


def delete_cached_preview(image_path: str):
    """Delete all cached previews for a given image."""
    try:
        # Remove all cache files that start with the image path hash
        src = Path(image_path)
        if not src.exists():
            return

        # Find and delete all cached versions
        for cached_file in CACHE_DIR.glob("*.png"):
            try:
                cached_file.unlink()
            except Exception:
                pass
    except Exception:
        pass


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────


def format_time_until(fire_at: int) -> str:
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


def format_time_ago(timestamp: int) -> str:
    now = int(time.time())
    diff = now - timestamp

    if diff < 0:
        return "just now"

    if diff < 60:
        return "just now"

    minutes = diff // 60
    if minutes < 60:
        if minutes == 1:
            return "1 minute ago"
        return f"{int(minutes)} minutes ago"

    hours = minutes // 60
    if hours < 24:
        if hours == 1:
            return "1 hour ago"
        return f"{int(hours)} hours ago"

    days = hours // 24
    if days < 7:
        if days == 1:
            return "yesterday"
        return f"{int(days)} days ago"

    weeks = days // 7
    if weeks < 4:
        if weeks == 1:
            return "1 week ago"
        return f"{int(weeks)} weeks ago"

    months = days // 30
    if months < 12:
        if months == 1:
            return "1 month ago"
        return f"{int(months)} months ago"

    years = days // 365
    if years == 1:
        return "1 year ago"
    return f"{int(years)} years ago"


def is_screenshot(notification: Notification) -> bool:
    SCREENSHOT_APPS = {
        "flameshot",
        "grim",
        "grimblast",
        "spectacle",
        "gnome-screenshot",
        "ksnip",
        "wl-shot",
    }

    return (
        (
            notification.app_name.lower() in SCREENSHOT_APPS
            or notification.summary.lower() == "screenshot"
        )
        and notification.icon
        and notification.icon.startswith("/")
        and notification.icon.endswith(".png")
    )


# ═══════════════════════════════════════════════════════════════
# SCREENSHOT HISTORY ITEM (CACHED PREVIEW)
# ═══════════════════════════════════════════════════════════════


class ScreenshotHistoryItem(widgets.Box):
    """Screenshot entry with cached preview + pill buttons."""

    def __init__(self, notification: Notification):
        # Get cached preview
        preview_path = get_cached_preview(
            notification.icon,
            size=(340, 191),  # 16:9 ratio
            crop=True,
        )

        preview = widgets.Picture(
            image=preview_path,
            content_fit="cover",
            width=340,
            height=191,
            css_classes=["screenshot-preview"],
        )

        timestamp = widgets.Label(
            label=format_time_ago(notification.time),
            halign="center",
            css_classes=["screenshot-timestamp"],
        )

        path_label = widgets.Label(
            label=f"Saved to {notification.icon}",
            halign="center",
            ellipsize="middle",
            css_classes=["screenshot-path"],
        )

        # Action buttons
        view_btn = widgets.Button(
            child=widgets.Label(label="View"),
            css_classes=["pill-btn"],
            on_click=lambda *_: self._open_screenshot(notification),
        )

        copy_btn = widgets.Button(
            child=widgets.Label(label="Copy"),
            css_classes=["pill-btn"],
            on_click=lambda *_: self._copy_screenshot(notification),
        )

        delete_btn = widgets.Button(
            child=widgets.Label(label="Delete"),
            css_classes=["pill-btn", "pill-btn-danger"],  # Add both classes
            on_click=lambda *_: self._delete(notification),
        )

        actions = widgets.Box(
            spacing=10,
            halign="center",
            hexpand=True,
            child=[view_btn, copy_btn, delete_btn],
        )

        super().__init__(
            vertical=True,
            spacing=14,
            hexpand=True,
            css_classes=["screenshot-history-item"],
            child=[preview, timestamp, path_label, actions],
        )

        # Update timestamp periodically
        utils.Poll(60000, lambda *_: self._update_timestamp(timestamp, notification))

        # Hide when closed
        notification.connect("closed", lambda *_: setattr(self, "visible", False))

    def _update_timestamp(self, label, notification):
        label.label = format_time_ago(notification.time)
        return True

    def _open_screenshot(self, notification):
        """Open screenshot in image viewer"""
        if notification.icon:
            asyncio.create_task(utils.exec_sh_async(f"xdg-open '{notification.icon}'"))

    def _copy_screenshot(self, notification):
        """Copy screenshot to clipboard"""
        if notification.icon:
            asyncio.create_task(utils.exec_sh_async(f"wl-copy < '{notification.icon}'"))

    def _delete(self, notification):
        """Delete screenshot file and cached preview"""
        if notification.icon:
            # Delete the original file
            asyncio.create_task(utils.exec_sh_async(f"rm '{notification.icon}'"))

            # Delete cached preview
            delete_cached_preview(notification.icon)

            # Close notification
            notification.close()


# ═══════════════════════════════════════════════════════════════
# SMART HISTORY ITEM
# ═══════════════════════════════════════════════════════════════


class NotificationHistoryItem(widgets.Box):
    """Auto-select screenshot or normal history layout."""

    def __init__(self, notification: Notification):
        super().__init__(
            child=[
                (
                    ScreenshotHistoryItem(notification)
                    if is_screenshot(notification)
                    else _NormalHistoryItem(notification)
                )
            ]
        )


# ═══════════════════════════════════════════════════════════════
# NORMAL NOTIFICATION HISTORY ITEM
# ═══════════════════════════════════════════════════════════════


class _NormalHistoryItem(widgets.Box):
    def __init__(self, notification: Notification):

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

        timestamp_label = widgets.Label(
            label=format_time_ago(notification.time),
            halign="start",
            css_classes=["notif-timestamp"],
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
            on_click=lambda *_: notification.close(),
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=2,
            child=[summary, timestamp_label, body],
            hexpand=True,
        )

        super().__init__(
            css_classes=["notif-history-item"],
            spacing=12,
            hexpand=True,
            child=[icon_widget, text_box, close_btn],
        )

        notification.connect("closed", lambda *_: setattr(self, "visible", False))
        utils.Poll(
            60000, lambda *_: self._update_timestamp(timestamp_label, notification)
        )

    def _update_timestamp(self, label, notification):
        label.label = format_time_ago(notification.time)
        return True


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
    """Compact dialog for creating a new task."""

    def __init__(self, on_add, on_cancel):
        self._on_add = on_add
        self._on_cancel = on_cancel

        now = datetime.now()

        self._time = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input", "task-time-input"],
        )
        self._time.text = ""

        self._date = widgets.Entry(
            placeholder_text="DD-MM-YYYY",
            css_classes=["task-input", "task-date-input"],
        )
        self._date.text = now.strftime("%d-%m-%Y")

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

        self._message = widgets.Entry(
            placeholder_text="What do you need to do?",
            css_classes=["task-input", "task-message-input"],
            hexpand=True,
            on_accept=lambda *_: self._add(),
        )
        self._message.text = ""

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
    """Compact dialog for editing an existing task."""

    def __init__(self, task, on_save, on_cancel):
        self._task = task
        self._on_save = on_save

        fire_dt = datetime.fromtimestamp(task["fire_at"])

        self._time = widgets.Entry(
            placeholder_text="HH:MM",
            css_classes=["task-input", "task-time-input"],
        )
        self._time.text = fire_dt.strftime("%H:%M")

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

        self._message = widgets.Entry(
            placeholder_text="What do you need to do?",
            css_classes=["task-input", "task-message-input"],
            hexpand=True,
            on_accept=lambda *_: self._save(),
        )
        self._message.text = task.get("message", "")

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
