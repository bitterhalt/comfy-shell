import datetime

from ignis import utils, widgets
from ignis.services.notifications import NotificationService
from ignis.window_manager import WindowManager
from modules.utils.signal_manager import SignalManager

wm = WindowManager.get_default()
notifications = NotificationService.get_default()


def clock():
    """Clock with notification indicator - with signal cleanup"""
    signals = SignalManager()

    # Visible clock text
    clock_label = widgets.Label(css_classes=["clock"])

    # Notification dot indicator
    notif_dot = widgets.Label(
        label="●",
        css_classes=["clock-notif-dot"],
        visible=False,
    )

    # Clock + dot container
    clock_content = widgets.Box(
        spacing=6,
        child=[clock_label, notif_dot],
    )

    # Clickable wrapper
    clock_button = widgets.Button(
        child=clock_content,
        css_classes=["clock-button"],
        on_click=lambda x: wm.open_window("ignis_INTEGRATED_CENTER"),
    )

    def update_time():
        """Update time display"""
        return datetime.datetime.now().strftime("%H:%M")

    def update_notifications(*args):
        """Update notification indicator"""
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %d.%m %Y")
        count = len(notifications.notifications)

        # Check for critical notifications
        has_critical = any(n.urgency == 2 for n in notifications.notifications)

        # Update tooltip
        tooltip = date_str
        if count > 0:
            tooltip += f"\n\n{count} notification(s)"

        clock_button.set_tooltip_text(tooltip)

        # Update dot visibility and color
        if count > 0:
            notif_dot.visible = True
            if has_critical:
                notif_dot.remove_css_class("normal")
                notif_dot.add_css_class("critical")
            else:
                notif_dot.remove_css_class("critical")
                notif_dot.add_css_class("normal")
        else:
            notif_dot.visible = False

    # Bind clock content to poll
    clock_label.set_property(
        "label",
        utils.Poll(60000, lambda *_: update_time()).bind("output"),
    )

    # Connect signals through manager
    signals.connect(notifications, "notified", update_notifications)
    signals.connect(notifications, "notify::notifications", update_notifications)

    # Initial update
    update_notifications()

    return clock_button
