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
from ignis.window_manager import WindowManager
from modules.notifications.integrated_center_widgets import (
    AddTaskDialog,
    EditTaskDialog,
    NotificationHistoryItem,
    TaskItem,
    format_time_until,
)
from modules.notifications.media import MediaCenterWidget

# ============================================================================
# globals
# ============================================================================

notifications = NotificationService.get_default()
queue_file = Path("~/.local/share/timers/queue.json").expanduser()
max_notifications = 10

wm = WindowManager.get_default()

# ============================================================================
# task storage (locking)
# ============================================================================


@contextmanager
def _locked_queue_file(mode: str = "r"):
    """File lock helper."""
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    if not queue_file.exists():
        queue_file.write_text("[]")

    with open(queue_file, mode, encoding="utf-8") as f:
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
# Integrated Center Window
# ============================================================================


class IntegratedCenter(widgets.Window):
    def __init__(self):
        # -------------------------------------------------------
        # LEFT: NOTIFICATIONS
        # -------------------------------------------------------
        self._notif_list = widgets.Box(vertical=True, css_classes=["content-list"])
        self._notif_empty = widgets.Label(
            label="No notifications",
            css_classes=["empty-state"],
            vexpand=True,
            valign="center",
        )

        notif_scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            child=widgets.Box(
                vertical=True,
                child=[self._notif_list, self._notif_empty],
            ),
        )

        # DND TOGGLE
        dnd_switch = widgets.Switch(
            active=options.notifications.bind("dnd"),
            on_change=lambda _, s: options.notifications.set_dnd(s),
        )

        dnd_box = widgets.Box(
            spacing=8,
            css_classes=["dnd-box"],
            hexpand=True,
            halign="start",
            child=[
                widgets.Label(label="Do Not Disturb", css_classes=["dnd-label"]),
                dnd_switch,
            ],
        )

        clear_btn = widgets.Button(
            child=widgets.Label(label="Clear All"),
            css_classes=["header-action-btn"],
            on_click=lambda *_: self._clear_notifications(),
        )

        left_column = widgets.Box(
            vertical=True,
            css_classes=["left-column"],
            child=[
                notif_scroll,
                widgets.Box(
                    spacing=8,
                    halign="fill",
                    valign="end",
                    css_classes=["left-bottom-bar"],
                    child=[dnd_box, clear_btn],
                ),
            ],
        )

        # -------------------------------------------------------
        # RIGHT: WEATHER + MEDIA + CALENDAR + TASKS
        # -------------------------------------------------------

        # weather
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

        # media pill
        self._media_pill = MediaCenterWidget()

        # calendar
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
            visible=False,
            css_classes=["calendar-box"],
            child=[self._calendar],
        )

        # next task pill
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

        next_task_box = widgets.Box(
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

        # full task list (hidden initially)
        self._task_list = widgets.Box(vertical=True, css_classes=["content-list"])
        self._task_empty = widgets.Label(
            label="No tasks",
            css_classes=["empty-state"],
            valign="center",
        )

        self._task_scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            visible=False,
            child=widgets.Box(
                vertical=True,
                child=[self._task_list, self._task_empty],
            ),
        )

        right_column = widgets.Box(
            vertical=True,
            css_classes=["right-column"],
            child=[
                weather_compact,
                self._media_pill,
                self._calendar_expander_button,
                self._calendar_box,
                next_task_box,
                self._task_scroll,
            ],
        )

        # -------------------------------------------------------
        # MAIN LAYOUT
        # -------------------------------------------------------

        two_columns = widgets.Box(
            css_classes=["integrated-center"],
            child=[left_column, right_column],
        )
        self._main_content = two_columns

        self._revealer = widgets.Revealer(
            child=two_columns,
            reveal_child=True,
            transition_type="none",
            transition_duration=0,
        )

        overlay_button = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["center-overlay"],
            on_click=lambda *_: wm.close_window("ignis_INTEGRATED_CENTER"),
        )

        root_overlay = widgets.Overlay(
            child=overlay_button,
            overlays=[
                widgets.Box(
                    valign="start",
                    halign="center",
                    css_classes=["center-container"],
                    child=[self._revealer],
                )
            ],
        )

        super().__init__(
            visible=False,
            popup=True,
            anchor=["top", "bottom", "left", "right"],
            layer="top",
            namespace="ignis_INTEGRATED_CENTER",
            css_classes=["center-window"],
            child=root_overlay,
            kb_mode="on_demand",
        )

        # initial loads
        self._load_notifications()
        self._reload_tasks()
        self._update_weather()

        notifications.connect("notified", self._on_notified)

        utils.Poll(30000, lambda *_: self._reload_tasks())
        utils.Poll(600000, lambda *_: self._update_weather())

    # =======================================================================
    # Calendar toggle
    # =======================================================================

    def _toggle_calendar(self):
        self._calendar_expanded = not self._calendar_expanded
        self._calendar_box.visible = self._calendar_expanded
        self._task_scroll.visible = self._calendar_expanded

        icon = "pan-up-symbolic" if self._calendar_expanded else "pan-down-symbolic"
        icon_widget = self._calendar_expander_button.child
        if isinstance(icon_widget, widgets.Icon):
            icon_widget.image = icon

    # =======================================================================
    # Weather popup
    # =======================================================================

    def _open_weather_popup(self):
        wm.close_window("ignis_INTEGRATED_CENTER")
        try:
            wm.toggle_window("ignis_WEATHER")
        except Exception:
            from modules.weather.weather_window import WeatherPopup

            WeatherPopup()
            wm.toggle_window("ignis_WEATHER")

    # =======================================================================
    # Notifications
    # =======================================================================

    def _clear_notifications(self):
        notifications.clear_all()
        self._notif_list.child = []
        self._notif_empty.visible = True

    def _load_notifications(self):
        items = notifications.notifications[:max_notifications]
        self._notif_list.child = [NotificationHistoryItem(n) for n in items]
        self._notif_empty.visible = len(items) == 0

    def _on_notified(self, _, nt):
        self._notif_list.prepend(NotificationHistoryItem(nt))
        if len(self._notif_list.child) > max_notifications:
            last = self._notif_list.child[-1]
            last.visible = False
            last.unparent()
        self._notif_empty.visible = len(self._notif_list.child) == 0

    # =======================================================================
    # Tasks
    # =======================================================================

    def _reload_tasks(self, *_):
        now = int(time.time())
        tasks = [t for t in load_tasks() if t.get("fire_at", 0) > now]
        tasks.sort(key=lambda t: t["fire_at"])

        # full list
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

        # next task
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

    def _add_task_and_refresh(self, task):
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        self._hide_dialog()
        self._reload_tasks()

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
        self._hide_dialog()
        self._reload_tasks()

    def _delete_task(self, task):
        tasks = load_tasks()
        save_tasks([t for t in tasks if t != task])
        self._reload_tasks()

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
        self._reload_tasks()

    # =======================================================================
    # Weather async updater
    # =======================================================================

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

        tooltip = (
            f"{data['city']}\n"
            f"Feels like {data['feels_like']}°C\n"
            f"Humidity: {data['humidity']}%\n"
            f"Wind: {data['wind']:.1f} m/s\n"
            "\nClick to open weather details"
        )
        self._weather_icon.set_tooltip_text(tooltip)

    # =======================================================================
    # Dialog handling
    # =======================================================================

    def _show_dialog(self, dialog):
        dialog.hexpand = True
        dialog.vexpand = False
        self._revealer.child = dialog

    def _hide_dialog(self):
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


# ============================================================================
# Global instance + helpers
# ============================================================================

integrated_center = IntegratedCenter()


def toggle_integrated_center():
    wm.toggle_window("ignis_INTEGRATED_CENTER")


def open_notifications():
    wm.open_window("ignis_INTEGRATED_CENTER")


def open_tasks():
    wm.open_window("ignis_INTEGRATED_CENTER")
