import asyncio
from ignis import utils, widgets
from ignis.services.notifications import Notification
from ignis.window_manager import WindowManager
from modules.notifications.widgets.time_utils import format_time_ago
from modules.utils.signal_manager import SignalManager

wm = WindowManager.get_default()


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
        (notification.app_name.lower() in SCREENSHOT_APPS or notification.summary.lower() == "screenshot")
        and notification.icon
        and notification.icon.startswith("/")
        and notification.icon.endswith(".png")
    )


class ScreenshotHistoryItem(widgets.Box):
    """Simplified screenshot notification with small preview and action buttons"""

    def __init__(self, notification: Notification):
        self._signals = SignalManager()
        self._poll = None
        self._expanded = False

        self._preview = widgets.Picture(
            image=notification.icon,
            content_fit="cover",
            width=96,
            height=54,
            css_classes=["screenshot-preview-small"],
        )

        self._large_preview = widgets.Picture(
            image=notification.icon,
            content_fit="cover",
            width=352,
            height=198,
            css_classes=["screenshot-preview-large"],
            visible=False,
        )

        self._timestamp = widgets.Label(
            label=format_time_ago(notification.time),
            halign="start",
            css_classes=["screenshot-timestamp"],
        )

        self._filename_label = widgets.Label(
            label="Screenshot",
            halign="start",
            css_classes=["screenshot-filename"],
        )

        expand_btn = widgets.Button(
            child=widgets.Icon(image="pan-down-symbolic", pixel_size=20),
            css_classes=["expand-btn"],
            tooltip_text="Expand preview",
            on_click=lambda *_: self._toggle_expand(),
        )

        view_btn = widgets.Button(
            child=widgets.Icon(image="document-open-symbolic", pixel_size=16),
            css_classes=["screenshot-action-btn", "unset"],
            tooltip_text="Open",
            on_click=lambda *_: self._open_screenshot(notification),
        )

        copy_btn = widgets.Button(
            child=widgets.Icon(image="edit-copy-symbolic", pixel_size=16),
            css_classes=["screenshot-action-btn", "unset"],
            tooltip_text="Copy to clipboard",
            on_click=lambda *_: self._copy_screenshot(notification),
        )

        delete_btn = widgets.Button(
            child=widgets.Icon(image="user-trash-symbolic", pixel_size=16),
            css_classes=["screenshot-action-btn", "screenshot-delete-btn", "unset"],
            tooltip_text="Delete",
            on_click=lambda *_: self._delete(notification),
        )

        actions = widgets.Box(
            spacing=4,
            halign="end",
            valign="start",
            child=[view_btn, copy_btn, delete_btn, expand_btn],
        )

        info_column = widgets.Box(
            vertical=True,
            spacing=4,
            hexpand=True,
            child=[
                widgets.Box(
                    child=[
                        widgets.Box(
                            vertical=True,
                            spacing=2,
                            hexpand=True,
                            child=[self._filename_label, self._timestamp],
                        ),
                        actions,
                    ]
                ),
            ],
        )

        self._compact_row = widgets.Box(
            spacing=12,
            child=[self._preview, info_column],
        )

        super().__init__(
            vertical=True,
            spacing=10,
            hexpand=True,
            css_classes=["screenshot-history-item"],
            child=[self._compact_row],
        )

        self._poll = utils.Poll(60000, lambda *_: self._update_timestamp(notification))
        self._signals.connect(notification, "closed", lambda *_: setattr(self, "visible", False))
        self._signals.connect(self, "destroy", lambda *_: self.destroy())

    def destroy(self):
        if self._poll:
            try:
                self._poll.cancel()
            except Exception:
                pass
            self._poll = None

        self._signals.disconnect_all()
        super().destroy()

    def _toggle_expand(self):
        """Toggle expanded preview"""
        self._expanded = not self._expanded
        self._large_preview.visible = self._expanded

        if self._expanded and self._large_preview not in self.child:
            self.append(self._large_preview)
        elif not self._expanded and self._large_preview in self.child:
            self._large_preview.unparent()

    def _update_timestamp(self, notification):
        self._timestamp.label = format_time_ago(notification.time)
        return True

    def _open_screenshot(self, notification):
        if notification.icon:
            asyncio.create_task(utils.exec_sh_async(f"xdg-open '{notification.icon}'"))
            wm.close_window("ignis_INTEGRATED_CENTER")

    def _copy_screenshot(self, notification):
        if notification.icon:
            asyncio.create_task(utils.exec_sh_async(f"wl-copy < '{notification.icon}'"))

    def _delete(self, notification):
        if notification.icon:
            asyncio.create_task(utils.exec_sh_async(f"rm '{notification.icon}'"))
            notification.close()


class NormalHistoryItem(widgets.Box):
    """Standard notification history item with expandable content"""

    def __init__(self, notification: Notification):
        self._signals = SignalManager()
        self._poll = None
        self._expanded = False
        self._notification = notification

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

        self._timestamp_label = widgets.Label(
            label=format_time_ago(notification.time),
            halign="start",
            css_classes=["notif-timestamp"],
        )

        # Collapsed body (ellipsized)
        self._body_collapsed = widgets.Label(
            label=notification.body,
            halign="start",
            ellipsize="end",
            max_width_chars=40,
            css_classes=["notif-history-body"],
            visible=notification.body != "",
            wrap=False,
        )

        # Expanded body (full text, wrapped)
        self._body_expanded = widgets.Label(
            label=notification.body,
            halign="start",
            css_classes=["notif-history-body-expanded"],
            visible=False,
            wrap=True,
            wrap_mode="word",
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=2,
            child=[
                summary,
                self._timestamp_label,
                self._body_collapsed,
                self._body_expanded,
            ],
            hexpand=True,
        )

        # Action buttons
        expand_btn = widgets.Button(
            child=widgets.Icon(image="pan-down-symbolic", pixel_size=20),
            css_classes=["expand-btn"],
            valign="start",
            tooltip_text="Expand",
            visible=len(notification.body) > 80 or len(notification.summary) > 70,
            on_click=lambda x: self._toggle_expand(),
        )

        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=20),
            css_classes=["close-btn"],
            valign="start",
            tooltip_text="Close",
            on_click=lambda x: notification.close(),
        )

        actions = widgets.Box(
            vertical=True,
            spacing=4,
            valign="start",
            child=[close_btn, expand_btn] if expand_btn.visible else [close_btn],
        )

        super().__init__(
            css_classes=["notif-history-item"],
            spacing=12,
            hexpand=True,
            child=[icon_widget, text_box, actions],
        )

        self._poll = utils.Poll(60000, lambda *_: self._update_timestamp(notification))
        self._signals.connect(notification, "closed", lambda *_: setattr(self, "visible", False))
        self._signals.connect(self, "destroy", lambda *_: self.destroy())

    def _toggle_expand(self):
        """Toggle between collapsed and expanded view"""
        self._expanded = not self._expanded
        self._body_collapsed.visible = not self._expanded
        self._body_expanded.visible = self._expanded

    def destroy(self):
        if self._poll:
            try:
                self._poll.cancel()
            except Exception:
                pass
            self._poll = None
        self._signals.disconnect_all()
        super().destroy()

    def _update_timestamp(self, notification):
        self._timestamp_label.label = format_time_ago(notification.time)
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
