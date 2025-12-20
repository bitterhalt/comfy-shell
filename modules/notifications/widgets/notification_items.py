"""
Notification history item widgets
"""

import asyncio

from ignis import utils, widgets
from ignis.services.notifications import Notification
from ignis.window_manager import WindowManager
from modules.notifications.widgets.cache import (
    delete_cached_preview,
    get_cached_preview,
)
from modules.notifications.widgets.time_utils import format_time_ago

wm = WindowManager.get_default()


def is_screenshot(notification: Notification) -> bool:
    """Check if notification is a screenshot notification"""
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


class ScreenshotHistoryItem(widgets.Box):
    """Screenshot notification with cached preview and action buttons"""

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
            css_classes=["pill-btn", "unset"],
            on_click=lambda *_: self._open_screenshot(notification),
        )

        copy_btn = widgets.Button(
            child=widgets.Label(label="Copy"),
            css_classes=["pill-btn", "unset"],
            on_click=lambda *_: self._copy_screenshot(notification),
        )

        delete_btn = widgets.Button(
            child=widgets.Label(label="Delete"),
            css_classes=["pill-btn", "pill-btn-danger", "unset"],
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
            wm.close_window("ignis_INTEGRATED_CENTER")

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


class NormalHistoryItem(widgets.Box):
    """Standard notification history item"""

    def __init__(self, notification: Notification):
        # Icon or dot indicator
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

        # Title styling
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
            css_classes=["notif-history-close", "unset"],
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


class NotificationHistoryItem(widgets.Box):
    """Smart notification item - auto-selects screenshot or normal layout"""

    def __init__(self, notification: Notification):
        super().__init__(
            child=[
                (
                    ScreenshotHistoryItem(notification)
                    if is_screenshot(notification)
                    else NormalHistoryItem(notification)
                )
            ]
        )
