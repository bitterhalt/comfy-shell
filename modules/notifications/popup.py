from ignis import utils, widgets
from ignis.services.notifications import Notification, NotificationService

notifications = NotificationService.get_default()


# =====================================================================
#  NOTIFICATION WIDGET (single cards)
# =====================================================================


class NotificationWidget(widgets.Box):
    """Single popup notification card."""

    def __init__(self, notification: Notification):
        urgency_class = "notif-box"
        title_class = "notif-title"
        body_class = "notif-body"

        if notification.urgency == 0:
            urgency_class = "notif-low"
        elif notification.urgency == 2:
            urgency_class = "notif-critical"
            title_class = "notif-title-critical"
            body_class = "notif-body-critical"

        # ─────────────────────────────────────────────
        # ICON or colored dot
        # ─────────────────────────────────────────────
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

        # Text
        summary = widgets.Label(
            label=notification.summary,
            visible=notification.summary != "",
            ellipsize="end",
            halign="start",
            css_classes=[title_class],
        )

        body = widgets.Label(
            label=notification.body,
            visible=notification.body != "",
            ellipsize="end",
            halign="start",
            css_classes=[body_class],
        )

        # Close button
        close_btn = widgets.Button(
            child=widgets.Icon(image="window-close-symbolic", pixel_size=20),
            css_classes=["notif-close"],
            halign="end",
            valign="start",
            hexpand=True,
            on_click=lambda *_: notification.close(),
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=4,
            style="margin-left: 0.75rem;",
            child=[summary, body],
        )

        main_row = widgets.Box(
            spacing=8,
            child=[icon_widget, text_box, close_btn],
        )

        # Actions (optional)
        if notification.actions:
            action_row = widgets.Box(
                spacing=10,
                homogeneous=True,
                style="margin-top: 0.75rem;",
                child=[
                    widgets.Button(
                        child=widgets.Label(label=action.label),
                        css_classes=["notif-action"],
                        on_click=lambda *_a, action=action: action.invoke(),
                    )
                    for action in notification.actions
                ],
            )
            children = [main_row, action_row]
        else:
            children = [main_row]

        super().__init__(
            vertical=True,
            spacing=6,
            css_classes=[urgency_class],
            child=children,
        )


# =====================================================================
#  ANIMATION-FREE POPUP WRAPPER
# =====================================================================


class Popup(widgets.Box):
    """
    A notification entry in the popup stack.
    """

    def __init__(self, notification: Notification):
        super().__init__(
            vertical=True,
            child=[NotificationWidget(notification)],
        )

        self._notification = notification

        notification.connect("closed", lambda *_: self.destroy())
        notification.connect("dismissed", lambda *_: self.destroy())

    def destroy(self):
        """Remove popup instantly"""
        self.visible = False
        utils.Timeout(1, self.unparent)


# =====================================================================
#  CONTAINER WINDOW
# =====================================================================


class NotificationPopup(widgets.Window):
    """
    Notification popup window on each monitor.
    No animations → Hyprland handles fade/slide.
    """

    def __init__(self, monitor: int):
        self._notif_box = widgets.Box(
            vertical=True,
            spacing=8,
            valign="start",
            halign="end",
        )

        super().__init__(
            anchor=["top", "right"],
            monitor=monitor,
            namespace=f"ignis_NOTIFICATION_POPUP_{monitor}",
            layer="overlay",
            css_classes=["notification-window"],
            visible=False,
            child=self._notif_box,
        )

        notifications.connect("new_popup", self._on_new_popup)

    # ────────────────────────────────────────────────
    # When a new notification arrives
    # ────────────────────────────────────────────────
    def _on_new_popup(self, service, notification):
        popup = Popup(notification)
        self._notif_box.prepend(popup)

        if not self.visible:
            self.visible = True

        # When notification closes → possibly hide window
        notification.connect("closed", lambda *_: self._check_if_empty())
        notification.connect("dismissed", lambda *_: self._check_if_empty())

    def _check_if_empty(self):
        utils.Timeout(50, self._do_check)

    def _do_check(self):
        """Hide window if no popups remain."""
        remaining = [c for c in self._notif_box.child if c.visible]

        if not remaining:
            self.visible = False


# =====================================================================
#  INITIALIZER
# =====================================================================


def init_notifications():
    import ignis.utils as _utils

    for i in range(_utils.get_n_monitors()):
        NotificationPopup(i)
