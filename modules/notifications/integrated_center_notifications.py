from ignis import widgets
from ignis.services.notifications import NotificationService

# Clean import from widgets package
from modules.notifications.widgets import NotificationHistoryItem

notifications = NotificationService.get_default()

MAX_NOTIFICATIONS = 10


class NotificationList:
    """Manages the notification list in the integrated center"""

    def __init__(self):
        self._notif_list = widgets.Box(vertical=True, css_classes=["content-list"])

        self._notif_empty = widgets.Label(
            label="No notifications",
            css_classes=["empty-state"],
            vexpand=True,
            valign="center",
            visible=False,
        )

        self.scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            child=widgets.Box(
                vertical=True,
                valign="start",
                child=[self._notif_list, self._notif_empty],
            ),
        )

        self._load_notifications()

        notifications.connect("notified", self._on_notified)

    def _load_notifications(self):
        """Load existing notifications"""
        items = notifications.notifications[:MAX_NOTIFICATIONS]
        self._notif_list.child = [NotificationHistoryItem(n) for n in items]

        for notif in items:
            notif.connect("closed", lambda *_: self._on_notification_closed())

        self._update_empty_state()

    def _on_notified(self, _, nt):
        """Handle new notification"""
        self._notif_list.prepend(NotificationHistoryItem(nt))

        nt.connect("closed", lambda *_: self._on_notification_closed())

        if len(self._notif_list.child) > MAX_NOTIFICATIONS:
            last = self._notif_list.child[-1]
            last.visible = False
            last.unparent()
        self._update_empty_state()

    def _on_notification_closed(self):
        """Handle when a notification is closed/dismissed"""
        self._load_notifications()

    def _update_empty_state(self):
        """Update visibility of empty state label"""
        has_notifications = len(notifications.notifications) > 0
        self._notif_empty.visible = not has_notifications

    def clear_all(self):
        """Clear all notifications"""
        notifications.clear_all()
        self._notif_list.child = []
        self._update_empty_state()
