import asyncio

from ignis import utils, widgets
from ignis.options import options
from ignis.services.notifications import Notification, NotificationService

notifications = NotificationService.get_default()

MAX_NOTIFICATIONS = 10  # Show only 10 latest notifications


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


class PowerButton(widgets.Button):
    """Individual power action button"""

    def __init__(self, icon: str, tooltip: str, command: str):
        super().__init__(
            child=widgets.Icon(image=icon, pixel_size=20),
            css_classes=["power-button"],
            tooltip_text=tooltip,
            on_click=lambda x: exec_async(command),
        )


class NotificationHistoryItem(widgets.Box):
    """Individual notification in history list"""

    def __init__(self, notification: Notification):
        # Icon
        icon = widgets.Icon(
            image=(
                notification.icon
                if notification.icon
                else "dialog-information-symbolic"
            ),
            pixel_size=32,
            halign="start",
            valign="start",
        )

        # Summary and body
        summary = widgets.Label(
            label=notification.summary,
            halign="start",
            ellipsize="end",
            max_width_chars=30,
            css_classes=["notif-history-title"],
        )

        body = widgets.Label(
            label=notification.body,
            halign="start",
            ellipsize="end",
            max_width_chars=40,
            css_classes=["notif-history-body"],
            visible=notification.body != "",
        )

        # Close button
        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=16),
            css_classes=["notif-history-close"],
            on_click=lambda x: notification.close(),
        )

        # Text box
        text_box = widgets.Box(
            vertical=True,
            child=[summary, body],
            hexpand=True,
        )

        super().__init__(
            css_classes=["notif-history-item"],
            child=[icon, text_box, close_btn],
            spacing=8,
        )

        # Remove from list when closed
        notification.connect("closed", lambda x: self.unparent())


class NotificationCenter(widgets.Window):
    """Notification history center"""

    def __init__(self):
        # Header with DND toggle
        header = widgets.Box(
            css_classes=["notif-center-header"],
            child=[
                widgets.Label(
                    label="Do Not Disturb",
                    css_classes=["notif-center-title"],
                    halign="start",
                    hexpand=True,
                ),
                widgets.Switch(
                    active=options.notifications.bind("dnd"),
                    on_change=lambda x, state: options.notifications.set_dnd(state),
                    halign="end",
                ),
            ],
        )

        # Clear all button
        clear_button = widgets.Button(
            child=widgets.Label(label="Clear All"),
            css_classes=["notif-clear-all"],
            on_click=lambda x: notifications.clear_all(),
        )

        # Notification list container
        self._notif_list = widgets.Box(
            vertical=True,
            css_classes=["notif-center-list"],
        )

        # Empty state label
        self._empty_label = widgets.Label(
            label="No notifications",
            css_classes=["notif-center-empty"],
            vexpand=True,
            valign="center",
        )

        # Scrollable area
        scroll = widgets.Scroll(
            vexpand=True,
            child=widgets.Box(
                vertical=True,
                child=[self._notif_list, self._empty_label],
            ),
        )

        # Power menu at bottom
        power_menu = widgets.Box(
            css_classes=["notif-power-menu"],
            homogeneous=True,
            child=[
                PowerButton("system-lock-screen-symbolic", "Lock", "hyprlock"),
                PowerButton(
                    "system-log-out-symbolic", "Log Out", "hyprctl dispatch exit"
                ),
                PowerButton("system-reboot-symbolic", "Reboot", "systemctl reboot"),
                PowerButton(
                    "system-shutdown-symbolic", "Shutdown", "systemctl poweroff"
                ),
            ],
        )

        # Main container
        main_box = widgets.Box(
            vertical=True,
            css_classes=["notif-center"],
            child=[header, clear_button, scroll, power_menu],
        )

        # Clickable overlay to close
        overlay_button = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["notif-center-overlay"],
            on_click=lambda x: toggle_notification_center(),
        )

        super().__init__(
            visible=False,
            anchor=["right", "top", "bottom", "left"],
            namespace="ignis_NOTIFICATION_CENTER",
            layer="top",
            css_classes=["notif-center-window"],
            child=widgets.Box(
                child=[
                    overlay_button,
                    main_box,
                ]
            ),
            kb_mode="on_demand",
        )

        # Load existing notifications
        self._load_notifications()

        # Connect to new notifications
        notifications.connect("notified", self._on_notified)

    def _load_notifications(self):
        """Load latest notifications (max 10)"""
        recent_notifs = notifications.notifications[:MAX_NOTIFICATIONS]
        for notif in recent_notifs:
            self._notif_list.append(NotificationHistoryItem(notif))
        self._update_empty_state()

    def _on_notified(self, service, notification):
        """Add new notification to list"""
        self._notif_list.prepend(NotificationHistoryItem(notification))

        # Remove oldest if exceeds limit
        if len(self._notif_list.child) > MAX_NOTIFICATIONS:
            oldest = self._notif_list.child[-1]
            oldest.unparent()

        self._update_empty_state()

    def _update_empty_state(self, *args):
        """Show/hide empty state label"""
        has_notifs = len(self._notif_list.child) > 0
        self._empty_label.visible = not has_notifs


# Create the notification center window
notification_center = NotificationCenter()


def toggle_notification_center():
    """Toggle notification center visibility"""
    notification_center.visible = not notification_center.visible
