import asyncio
import fcntl
import json
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from ignis import utils, widgets
from ignis.options import options
from ignis.services.notifications import NotificationService
from modules.notifications.integrated_center_widgets import (
    AddTaskDialog,
    EditTaskDialog,
    NotificationHistoryItem,
    TaskItem,
    format_time_until,
)
from modules.notifications.media import MediaCenterWidget

notifications = NotificationService.get_default()
queue_file = Path("~/.local/share/timers/queue.json").expanduser()
max_notifications = 10


# ═══════════════════════════════════════════════════════════════
# task storage with file locking
# ═══════════════════════════════════════════════════════════════


@contextmanager
def _locked_queue_file(mode: str = "r"):
    """Thread-safe file locking for queue operations."""
    queue_file.parent.mkdir(parents=True, exist_ok=True)

    # ensure file exists
    if not queue_file.exists():
        queue_file.write_text("[]")

    with open(queue_file, mode, encoding="utf-8") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_tasks():
    """Load tasks with file locking."""
    try:
        with _locked_queue_file("r") as f:
            content = f.read()
            return json.loads(content) if content.strip() else []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[integrated_center] error loading tasks: {e}")
        return []


def save_tasks(tasks):
    """Save tasks with file locking."""
    try:
        with _locked_queue_file("w") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print(f"[integrated_center] error saving tasks: {e}")


# ═══════════════════════════════════════════════════════════════
# integrated center window
# ═══════════════════════════════════════════════════════════════


class IntegratedCenter(widgets.Window):
    def __init__(self):
        # ────────────────────────────────────────────────────────
        # LEFT COLUMN – NOTIFICATIONS
        # ────────────────────────────────────────────────────────
        self._notif_list = widgets.Box(vertical=True, css_classes=["content-list"])
        self._notif_empty = widgets.Label(
            label="No notifications",
            css_classes=["empty-state"],
            vexpand=True,
            valign="center",
        )

        notif_content = widgets.Box(
            vertical=True,
            child=[self._notif_list, self._notif_empty],
        )

        notif_scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            child=notif_content,
        )

        # DND toggle
        dnd_switch = widgets.Switch(
            active=options.notifications.bind("dnd"),
            on_change=lambda _, state: options.notifications.set_dnd(state),
        )

        dnd_box = widgets.Box(
            spacing=8,
            css_classes=["dnd-box"],
            hexpand=True,
            halign="start",
            child=[
                widgets.Label(css_classes=["dnd-label"]),
                dnd_switch,
            ],
        )

        clear_btn = widgets.Button(
            child=widgets.Label(label="Clear All"),
            css_classes=["header-action-btn"],
            on_click=lambda *_: self._clear_notifications(),
            halign="center",
        )

        bottom_bar = widgets.Box(
            spacing=8,
            css_classes=["left-bottom-bar"],
            halign="fill",
            valign="end",
            child=[
                dnd_box,
                clear_btn,
            ],
        )

        left_column = widgets.Box(
            vertical=True,
            css_classes=["left-column"],
            child=[
                notif_scroll,
                bottom_bar,
            ],
        )

        # ────────────────────────────────────────────────────────
        # RIGHT COLUMN – WEATHER + MEDIA + CALENDAR + TASKS
        # ────────────────────────────────────────────────────────

        # Weather (compact pill at top)
        self._weather_icon = widgets.Icon(
            image="weather-clouds-symbolic",
            pixel_size=32,
        )
        self._weather_temp = widgets.Label(
            label="--°",
            css_classes=["weather-temp-compact"],
        )
        self._weather_desc = widgets.Label(
            label="…",
            css_classes=["weather-desc-compact"],
            ellipsize="end",
            max_width_chars=20,
        )

        weather_compact = widgets.Button(
            css_classes=["weather-compact"],
            on_click=lambda *_: self._open_weather_popup(),
            child=widgets.Box(
                spacing=10,
                child=[self._weather_icon, self._weather_temp, self._weather_desc],
            ),
        )

        # MPRIS media pill
        self._media_pill = MediaCenterWidget()

        # Calendar
        self._calendar = widgets.Calendar(
            css_classes=["center-calendar"],
            show_day_names=True,
            show_heading=False,
        )

        self._calendar_expanded = False

        self._calendar_expander_button = widgets.Button(
            css_classes=["calendar-expander"],
            on_click=lambda *_: self._toggle_calendar(),
            child=widgets.Icon(
                image="pan-down-symbolic",
                pixel_size=16,
                css_classes=["calendar-expander-icon"],
            ),
        )

        self._calendar_box = widgets.Box(
            vertical=True,
            css_classes=["calendar-box"],
            visible=False,
            child=[self._calendar],
        )

        # NEXT UPCOMING TASK PILL
        self._next_task_title = widgets.Label(
            label="No tasks for today",
            halign="start",
            ellipsize="end",
            max_width_chars=30,
            css_classes=["next-task-title"],
        )

        self._next_task_meta = widgets.Label(
            label="",
            halign="start",
            css_classes=["next-task-meta"],
            visible=False,
        )

        next_task_text_column = widgets.Box(
            vertical=True,
            hexpand=True,
            css_classes=["next-task-text-column"],
            child=[self._next_task_title, self._next_task_meta],
        )

        next_task_add_btn = widgets.Button(
            child=widgets.Label(label="Add Task"),
            css_classes=["add-task-btn"],
            on_click=lambda *_: self._open_add_dialog(),
            halign="end",
        )

        self._next_task_box = widgets.Box(
            spacing=8,
            css_classes=["next-task-box"],
            child=[next_task_text_column, next_task_add_btn],
        )

        # TASK LIST (full list, only visible when calendar expanded)
        self._task_list = widgets.Box(vertical=True, css_classes=["content-list"])
        self._task_empty = widgets.Label(
            label="No tasks",
            css_classes=["empty-state"],
            valign="center",
        )

        task_content = widgets.Box(
            vertical=True,
            child=[self._task_list, self._task_empty],
        )

        task_scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            child=task_content,
        )
        task_scroll.visible = False
        self._task_scroll = task_scroll

        right_column = widgets.Box(
            vertical=True,
            css_classes=["right-column"],
            child=[
                weather_compact,
                self._media_pill,
                self._calendar_expander_button,
                self._calendar_box,
                self._next_task_box,
                self._task_scroll,
            ],
        )

        # ────────────────────────────────────────────────────────
        # MAIN LAYOUT + WINDOW
        # ────────────────────────────────────────────────────────

        two_columns = widgets.Box(
            css_classes=["integrated-center"],
            child=[left_column, right_column],
        )
        self._main_content = two_columns

        # Revealer with NO animation (instant reveal)
        self._revealer = widgets.Revealer(
            child=two_columns,
            reveal_child=True,  # Always revealed
            transition_type="none",  # No animation
            transition_duration=0,
        )

        centered = widgets.Box(
            valign="start",
            halign="center",
            css_classes=["center-container"],
            child=[self._revealer],
        )

        overlay_button = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["center-overlay"],
            on_click=lambda *_: toggle_integrated_center(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_button,
            overlays=[centered],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_INTEGRATED_CENTER",
            layer="top",
            popup=True,
            css_classes=["center-window"],
            child=root_overlay,
            kb_mode="on_demand",
        )

        # initial load
        self._load_notifications()
        self._reload_tasks()
        self._update_weather()

        notifications.connect("notified", self._on_notified)
        utils.Poll(30000, lambda *_: self._reload_tasks())
        utils.Poll(600000, lambda *_: self._update_weather())

    # ───────────────────────────────────────────────────────────
    # calendar / tasks toggle
    # ───────────────────────────────────────────────────────────

    def _toggle_calendar(self):
        self._calendar_expanded = not self._calendar_expanded
        self._calendar_box.visible = self._calendar_expanded
        self._task_scroll.visible = self._calendar_expanded

        icon_name = (
            "pan-up-symbolic" if self._calendar_expanded else "pan-down-symbolic"
        )
        # Button child is [Icon]; update it

        child = self._calendar_expander_button.child
        if isinstance(child, widgets.Icon):
            child.image = icon_name

    # ───────────────────────────────────────────────────────────
    # weather popup opening
    # ───────────────────────────────────────────────────────────

    def _open_weather_popup(self):
        """Open the weather popup window"""
        from modules.weather.weather_window import (
            reset_weather_popup,
            toggle_weather_popup,
        )

        # Close the integrated center FIRST
        toggle_integrated_center()

        # Reset any existing weather popup to ensure clean state
        reset_weather_popup()

        # Open weather popup after a small delay
        utils.Timeout(200, toggle_weather_popup)

    # ───────────────────────────────────────────────────────────
    # notifications
    # ───────────────────────────────────────────────────────────

    def _clear_notifications(self):
        notifications.clear_all()
        self._notif_list.child = []
        self._notif_empty.visible = True

    def _load_notifications(self):
        recent = notifications.notifications[:max_notifications]
        self._notif_list.child = [NotificationHistoryItem(n) for n in recent]
        self._notif_empty.visible = len(self._notif_list.child) == 0

    def _on_notified(self, _, nt):
        self._notif_list.prepend(NotificationHistoryItem(nt))
        if len(self._notif_list.child) > max_notifications:
            oldest = self._notif_list.child[-1]
            oldest.visible = False
            oldest.unparent()
        self._notif_empty.visible = len(self._notif_list.child) == 0

    # ───────────────────────────────────────────────────────────
    # tasks
    # ───────────────────────────────────────────────────────────

    def _reload_tasks(self, *_):
        now = int(time.time())
        tasks = [t for t in load_tasks() if t.get("fire_at", 0) > now]
        tasks.sort(key=lambda t: t["fire_at"])

        # full list (used when calendar expanded)
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

        # next upcoming pill
        if tasks:
            next_task = tasks[0]
            fire_at = next_task["fire_at"]
            fire_dt = datetime.fromtimestamp(fire_at)
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            if fire_dt.date() == today:
                day_label = "Today"
            elif fire_dt.date() == tomorrow:
                day_label = "Tomorrow"
            else:
                day_label = fire_dt.strftime("%d.%m")

            time_label = fire_dt.strftime("%H:%M")
            remaining = format_time_until(fire_at)

            self._next_task_title.label = next_task.get("message", "")
            self._next_task_meta.label = f"{day_label} • {time_label} • {remaining}"
            self._next_task_meta.visible = True
        else:
            self._next_task_title.label = "No tasks for today"
            self._next_task_meta.visible = False

        return True

    def _add_task_and_refresh(self, task):
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        self._hide_dialog()
        self._reload_tasks()

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
        self._hide_dialog()
        self._reload_tasks()

    def _delete_task(self, task):
        tasks = [t for t in load_tasks() if t != task]
        save_tasks(tasks)
        self._reload_tasks()

    def _complete_task(self, task):
        self._delete_task(task)

    def _snooze_task(self, task, minutes=5):
        now = int(time.time())
        tasks = load_tasks()
        updated = []
        used = False
        for t in tasks:
            if not used and t == task:
                nt = dict(t)
                nt["fire_at"] = now + minutes * 60
                updated.append(nt)
                used = True
            else:
                updated.append(t)
        save_tasks(updated)
        self._reload_tasks()

    # ───────────────────────────────────────────────────────────
    # weather (mini, using async API)
    # ───────────────────────────────────────────────────────────

    def _update_weather(self, *_):
        asyncio.create_task(self._update_weather_async())
        return True

    async def _update_weather_async(self):
        from modules.weather.weather_data import fetch_weather_async

        data = await fetch_weather_async()
        if not data:
            return

        self._weather_icon.image = data["icon"]
        self._weather_temp.label = f"{data['temp']}°"
        self._weather_desc.label = data["desc"]

        tooltip = f"{data['city']}\n"
        tooltip += f"Feels like {data['feels_like']}°C\n"
        tooltip += f"Humidity: {data['humidity']}%\n"
        tooltip += f"Wind: {data['wind']:.1f} m/s\n"
        tooltip += "\nClick to open weather details"
        self._weather_icon.set_tooltip_text(tooltip)

    # ───────────────────────────────────────────────────────────
    # dialog handling
    # ───────────────────────────────────────────────────────────

    def _show_dialog(self, dialog):
        """
        Show Add/Edit dialog as a centered card inside the center.
        """
        dialog.hexpand = True
        dialog.vexpand = False
        self._revealer.child = dialog

    def _hide_dialog(self):
        """Return to main two-column layout."""
        self._revealer.child = self._main_content

    def _open_add_dialog(self):
        dlg = AddTaskDialog(
            on_add=self._add_task_and_refresh,
            on_cancel=lambda *_: self._hide_dialog(),
        )
        self._show_dialog(dlg)

    def _open_edit_dialog(self, task):
        dlg = EditTaskDialog(
            task,
            on_save=lambda new: self._update_task(task, new),
            on_cancel=lambda *_: self._hide_dialog(),
        )
        self._show_dialog(dlg)


# ═══════════════════════════════════════════════════════════════
# global instance + toggle helpers
# ═══════════════════════════════════════════════════════════════

integrated_center = IntegratedCenter()


def toggle_integrated_center():
    integrated_center.visible = not integrated_center.visible


def open_notifications():
    if not integrated_center.visible:
        toggle_integrated_center()


def open_tasks():
    if not integrated_center.visible:
        toggle_integrated_center()
