import datetime

from ignis import utils, widgets
from ignis.services.notifications import NotificationService
from ignis.window_manager import WindowManager
from modules.utils.signal_manager import SignalManager
from settings import config

wm = WindowManager.get_default()
notifications = NotificationService.get_default()


def clock():
    """Clock with notification indicator (fully correct & leak-safe)"""

    signals = SignalManager()
    clock_poll = None

    clock_label = widgets.Label(css_classes=["clock"])

    notif_dot = widgets.Label(
        label="●",
        css_classes=["clock-notif-dot"],
        visible=False,
    )

    clock_content = widgets.Box(
        spacing=6,
        child=[clock_label, notif_dot],
    )

    clock_button = widgets.Button(
        child=clock_content,
        css_classes=["clock-button"],
        on_click=lambda x: wm.open_window("ignis_INTEGRATED_CENTER"),
    )

    def update_time():
        return datetime.datetime.now().strftime("%H:%M")

    def _should_show_notification(notif) -> bool:
        """Check if notification should be shown (not filtered)"""
        return not config.ui.notifications.should_filter(notif)

    def update_notifications(*_):
        # Filter out notifications that match keywords
        all_notifs = notifications.notifications
        visible_notifs = [n for n in all_notifs if _should_show_notification(n)]
        count = len(visible_notifs)
        has_critical = any(n.urgency == 2 for n in visible_notifs)

        tooltip = datetime.datetime.now().strftime("%A, %d.%m %Y")
        if count > 0:
            tooltip += f"\n\n{count} notification(s)"

        clock_button.set_tooltip_text(tooltip)

        if count > 0:
            notif_dot.visible = True
            notif_dot.remove_css_class("normal")
            notif_dot.remove_css_class("critical")
            notif_dot.add_css_class("critical" if has_critical else "normal")
        else:
            notif_dot.visible = False

    def watch_notification(nt):
        signals.connect(nt, "closed", update_notifications)
        try:
            signals.connect(nt, "dismissed", update_notifications)
        except Exception:
            pass

    def on_new_notification(_, nt):
        watch_notification(nt)
        update_notifications()

    clock_poll = utils.Poll(60000, lambda *_: update_time())
    clock_label.set_property("label", clock_poll.bind("output"))

    signals.connect(notifications, "notified", on_new_notification)
    signals.connect(notifications, "new_popup", on_new_notification)

    for nt in notifications.notifications:
        watch_notification(nt)

    def cleanup(*_):
        signals.disconnect_all()
        if clock_poll:
            try:
                clock_poll.cancel()
            except:
                pass

    signals.connect(clock_button, "destroy", cleanup)

    update_notifications()

    return clock_button
