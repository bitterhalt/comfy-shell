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
            css_classes=["notif-close"],
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
    """Animated popup wrapper for notifications"""

    def __init__(self, notification: Notification):
        self._notification = notification

        widget = NotificationWidget(notification)

        super().__init__(
            transition_type="slide_down",
            transition_duration=300,
            reveal_child=False,
            child=widget,
        )

        notification.connect("dismissed", lambda x: self.destroy())
        notification.connect("closed", lambda x: self.destroy())

    def destroy(self):
        """Animated destruction of the popup"""
        self.reveal_child = False
        utils.Timeout(self.transition_duration, self.unparent)


class NotificationPopup(widgets.Window):
    """Main notification popup window"""

    def __init__(self, monitor: int = 0):
        self._notif_box = widgets.Box(
            vertical=True,
            valign="start",
            halign="end",
        )

        super().__init__(
            anchor=["right", "top"],
            monitor=monitor,
            namespace=f"ignis_NOTIFICATION_POPUP_{monitor}",
            layer="overlay",
            child=self._notif_box,
            visible=False,
            css_classes=["notification-window"],
        )

        # Connect to new notifications
        notifications.connect("new_popup", self._on_new_popup)

    def _on_new_popup(self, service, notification):
        """Add new notification popup"""
        popup = Popup(notification)
        self._notif_box.prepend(popup)

        if not self.visible:
            self.visible = True

        utils.Timeout(10, popup.set_reveal_child, True)

        notification.connect("closed", lambda x: self._check_if_empty())
        notification.connect("dismissed", lambda x: self._check_if_empty())

    def _check_if_empty(self):
        """Hide window if no popups remain"""
        utils.Timeout(400, self._do_check)

    def _do_check(self):
        """Actually check and hide window if empty"""
        visible_children = [
            c for c in self._notif_box.child if c.get_visible() and c.get_mapped()
        ]

        if len(visible_children) == 0:
            self.visible = False


def init_notifications():
    monitor = config.ui.bar_monitor
    return NotificationPopup(monitor)
