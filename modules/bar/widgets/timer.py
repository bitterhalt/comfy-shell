import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path

from ignis import utils, widgets

# Configuration (matching your fuzzel_task.py)
QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()
DEFAULT_ICON = "󰂚"
TODAY_ICON = "󰋼"


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


def get_timer_data():
    """Parse timer queue and return display info"""
    now_ts = int(time.time())
    now_dt = datetime.fromtimestamp(now_ts)
    today_date_str = now_dt.strftime("%Y-%m-%d")

    # Default state
    result = {
        "text": DEFAULT_ICON,
        "tooltip": "No active timers.",
        "css_class": "idle",
    }

    try:
        if not QUEUE_FILE.exists() or os.path.getsize(QUEUE_FILE) == 0:
            return result

        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            queue = json.load(f)

    except (FileNotFoundError, json.JSONDecodeError):
        result["text"] = "ERR"
        result["tooltip"] = "Error reading queue file."
        result["css_class"] = "error"
        return result

    # Filter and sort active timers
    active_timers = sorted(
        [t for t in queue if t.get("fire_at", 0) > now_ts],
        key=lambda t: t["fire_at"],
    )

    if not active_timers:
        return result

    # Get next timer
    next_timer = active_timers[0]
    fire_at = next_timer["fire_at"]
    message = next_timer["message"]
    fire_dt = datetime.fromtimestamp(fire_at)
    fire_date_str = fire_dt.strftime("%Y-%m-%d")

    time_label = fire_dt.strftime("%H:%M")

    # Determine urgency
    if fire_date_str == today_date_str:
        result["css_class"] = "today"
        result["text"] = f"{TODAY_ICON} {message}"
        date_label = "Today"
    else:
        result["css_class"] = "future"
        result["text"] = DEFAULT_ICON
        date_label = fire_dt.strftime("%d.%m")

    result["tooltip"] = f"{date_label} @ {time_label}\n\nTask: {message}"

    return result


def timer_widget():
    """Timer indicator that shows next upcoming timer"""

    # Create label
    label = widgets.Label(
        label=DEFAULT_ICON,
        css_classes=["custom-timer"],
    )

    # Create button
    button = widgets.Button(
        css_classes=["timer-button"],
        on_click=lambda *_: exec_async(
            os.path.expanduser("~/.local/bin/menu_scripts/fuzzel_task.py")
        ),
        child=label,
    )

    def update_timer(*args):
        """Update timer display"""
        data = get_timer_data()

        # Update label text
        label.set_label(data["text"])
        button.set_tooltip_text(data["tooltip"])

        # Update CSS class
        label.remove_css_class("idle")
        label.remove_css_class("today")
        label.remove_css_class("future")
        label.remove_css_class("error")
        label.add_css_class(data["css_class"])

        return True  # Keep polling

    # Initial update
    update_timer()

    # Poll every 30 seconds
    utils.Poll(30000, update_timer)

    # Also watch file changes for instant updates
    def on_file_change(*_):
        update_timer()

    try:
        from gi.repository import Gio

        file_monitor = Gio.File.new_for_path(str(QUEUE_FILE))
        monitor = file_monitor.monitor_file(Gio.FileMonitorFlags.NONE, None)
        monitor.connect("changed", on_file_change)
    except Exception:
        pass  # File monitoring is optional

    return button
