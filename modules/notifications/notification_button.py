from ignis import widgets
from ignis.options import options
from ignis.services.notifications import NotificationService
from modules.notifications.notification_center import toggle_notification_center

notifications = NotificationService.get_default()


def notification_button():
    """Button to toggle notification center with unread count"""

    # Icon that changes based on DND state
    icon = widgets.Icon(
        image=options.notifications.bind(
            "dnd",
            lambda dnd: (
                "notification-disabled-symbolic"
                if dnd
                else "preferences-system-notifications-symbolic"
            ),
        ),
        pixel_size=22,
    )

    # Count badge (shows number of notifications)
    count_label = widgets.Label(
        label=notifications.bind(
            "notifications", lambda notifs: str(len(notifs)) if len(notifs) > 0 else ""
        ),
        css_classes=["notif-count-badge"],
        visible=notifications.bind("notifications", lambda notifs: len(notifs) > 0),
    )

    # Button with icon and badge
    return widgets.Button(
        css_classes=options.notifications.bind(
            "dnd",
            lambda dnd: (
                ["notification-button", "dnd-active"]
                if dnd
                else ["notification-button"]
            ),
        ),
        on_click=lambda *_: toggle_notification_center(),
        on_right_click=lambda *_: options.notifications.set_dnd(
            not options.notifications.dnd
        ),  # <-- Added right-click!
        tooltip_text=notifications.bind(
            "notifications",
            lambda notifs: f"{len(notifs)} notification(s)"
            + (" (DND)" if options.notifications.dnd else ""),
        ),
        child=widgets.Overlay(
            child=icon,
            overlays=[
                widgets.Box(
                    halign="end",
                    valign="start",
                    child=[count_label],
                )
            ],
        ),
    )
