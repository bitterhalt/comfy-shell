"""
Notification list management for integrated center
"""

from ignis import widgets
from ignis.services.notifications import NotificationService
from modules.notifications.integrated_center_widgets import NotificationHistoryItem

notifications = NotificationService.get_default()

MAX_NOTIFICATIONS = 10


class NotificationList:
    """Manages the notification list in the integrated center"""

    def __init__(self):
        # Notification list container
        self._notif_list = widgets.Box(vertical=True, css_classes=["content-list"])

        # Empty state label
        self._notif_empty = widgets.Label(
            label="No notifications",
            css_classes=["empty-state"],
            vexpand=True,
            valign="center",
        )

        # Scrollable container
        self.scroll = widgets.Scroll(
            vexpand=True,
            vscrollbar_policy="automatic",
            child=widgets.Box(
                vertical=True,
                valign="start",
                child=[self._notif_list, self._notif_empty],
            ),
        )

        # Load initial notifications
        self._load_notifications()

        # Connect to signals
        notifications.connect("notified", self._on_notified)

    def _load_notifications(self):
        """Load existing notifications"""
        items = notifications.notifications[:MAX_NOTIFICATIONS]
        self._notif_list.child = [NotificationHistoryItem(n) for n in items]
        self._notif_empty.visible = len(items) == 0

    def _on_notified(self, _, nt):
        """Handle new notification"""
        self._notif_list.prepend(NotificationHistoryItem(nt))
        if len(self._notif_list.child) > MAX_NOTIFICATIONS:
            last = self._notif_list.child[-1]
            last.visible = False
            last.unparent()
        self._notif_empty.visible = len(self._notif_list.child) == 0

    def clear_all(self):
        """Clear all notifications"""
        notifications.clear_all()
        self._notif_list.child = []
        self._notif_empty.visible = True
