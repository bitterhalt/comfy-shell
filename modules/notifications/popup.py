from ignis import utils, widgets
from ignis.services.notifications import Notification, NotificationService
from settings import config

notifications = NotificationService.get_default()


class NotificationWidget(widgets.Box):
    """Individual notification widget with close button and actions"""

    def __init__(self, notification: Notification):
        urgency_class = "notif-box"
        title_class = "notif-title"
        body_class = "notif-body"

        if notification.urgency == 0:  # Low Urgency
            urgency_class = "notif-low"
        elif notification.urgency == 2:  # Critical Urgency
            urgency_class = "notif-critical"
            title_class = "notif-title-critical"
            body_class = "notif-body-critical"

        if notification.icon:
            icon_widget = widgets.Icon(
                image=notification.icon,
                pixel_size=32,
                halign="start",
                valign="start",
                css_classes=["notif-popup-icon"],
            )
        else:
            dot_color = "critical" if notification.urgency == 2 else "normal"
            icon_widget = widgets.Label(
                label="●",
                css_classes=["notif-popup-dot", dot_color],
                halign="start",
                valign="start",
            )

        summary = widgets.Label(
            ellipsize="end",
            label=notification.summary,
            halign="start",
            visible=notification.summary != "",
            css_classes=[title_class],
        )

        body = widgets.Label(
            label=notification.body,
            ellipsize="end",
            halign="start",
            css_classes=[body_class],
            visible=notification.body != "",
        )

        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=20),
            halign="end",
            valign="start",
            hexpand=True,
            css_classes=["notif-close", "unset"],
            on_click=lambda x: notification.close(),
        )

        text_box = widgets.Box(
            vertical=True,
            style="margin-left: 0.75rem;",
            child=[summary, body],
        )

        content = widgets.Box(
            child=[icon_widget, text_box, close_btn],
        )

        action_box = widgets.Box(
            child=[
                widgets.Button(
                    child=widgets.Label(label=action.label),
                    on_click=lambda x, action=action: action.invoke(),
                    css_classes=["notif-action"],
                )
                for action in notification.actions
            ],
            homogeneous=True,
            style="margin-top: 0.75rem;" if notification.actions else "",
            spacing=10,
        )

        super().__init__(
            vertical=True,
            css_classes=[urgency_class],
            child=[content, action_box] if notification.actions else [content],
        )


class Popup(widgets.Revealer):
    def __init__(self, parent_box: "PopupBox", notification: Notification):
        self._parent_box = parent_box
        self._notification = notification

        widget = NotificationWidget(notification)

        super().__init__(
            transition_type="slide_down",
            transition_duration=300,
            reveal_child=False,
            child=widget,
        )

        # Connect to notification signals
        notification.connect("dismissed", lambda x: self.destroy())
        notification.connect("closed", lambda x: self.destroy())

    def destroy(self):
        """Simple animated destruction with proper window management"""
        # Start close animation
        self.reveal_child = False

        # Wait for animation to complete, then cleanup
        utils.Timeout(self.transition_duration, self._cleanup)

    def _cleanup(self):
        """Remove popup and check if window should hide"""
        # Remove from parent
        self.unparent()

        # Auto-hide window when last popup is gone
        visible_popups = [
            child
            for child in self._parent_box.child
            if child.get_visible() and child.get_mapped()
        ]

        if len(visible_popups) == 0:
            self._parent_box._window.visible = False


class PopupBox(widgets.Box):
    """Container for notification popups"""

    def __init__(self, window: "NotificationPopup"):
        self._window = window

        super().__init__(
            vertical=True,
            valign="start",
            halign="end",
        )

        # Connect to new popup signal
        notifications.connect("new_popup", self._on_new_popup)

    def _on_new_popup(self, service, notification: Notification):
        """Add new notification popup"""
        # Create popup
        popup = Popup(parent_box=self, notification=notification)
        self.prepend(popup)

        # Show window if hidden
        if not self._window.visible:
            self._window.visible = True

        # Reveal with small delay to ensure window is visible
        utils.Timeout(10, popup.set_reveal_child, True)


class NotificationPopup(widgets.Window):
    """Main notification popup window"""

    def __init__(self, monitor: int = 0):
        self._popup_box = PopupBox(window=self)

        super().__init__(
            anchor=["right", "top"],
            monitor=monitor,
            namespace=f"ignis_NOTIFICATION_POPUP_{monitor}",
            layer="overlay",
            child=self._popup_box,
            visible=False,
            css_classes=["notification-window"],
        )


def init_notifications():
    """Initialize notification popup on configured monitor"""
    monitor = config.ui.notifications_monitor
    return NotificationPopup(monitor)
