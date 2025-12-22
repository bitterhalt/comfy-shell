import datetime

from ignis import utils, widgets
from ignis.services.notifications import NotificationService
from ignis.window_manager import WindowManager
from modules.utils.signal_manager import SignalManager

wm = WindowManager.get_default()
notifications = NotificationService.get_default()


def clock():
    """Clock with notification indicator (fully correct & leak-safe)"""

    signals = SignalManager()

    # ──────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────

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
        on_click=lambda *_: wm.open_window("ignis_INTEGRATED_CENTER"),
    )

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def update_time():
        return datetime.datetime.now().strftime("%H:%M")

    def update_notifications(*_):
        notifs = notifications.notifications
        count = len(notifs)
        has_critical = any(n.urgency == 2 for n in notifs)

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
        # Update dot when notification is removed
        signals.connect(nt, "closed", update_notifications)
        try:
            signals.connect(nt, "dismissed", update_notifications)
        except Exception:
            pass

    def on_new_notification(_, nt):
        watch_notification(nt)
        update_notifications()

    # ──────────────────────────────────────────────
    # Clock update (safe Poll binding)
    # ──────────────────────────────────────────────

    clock_label.set_property(
        "label",
        utils.Poll(60000, lambda *_: update_time()).bind("output"),
    )

    # ──────────────────────────────────────────────
    # Notification wiring (ADD + REMOVE)
    # ──────────────────────────────────────────────

    signals.connect(notifications, "notified", on_new_notification)
    signals.connect(notifications, "new_popup", on_new_notification)

    # Track existing notifications (important on reload)
    for nt in notifications.notifications:
        watch_notification(nt)

    # Cleanup when widget dies (reload-safe)
    signals.connect(
        clock_button,
        "destroy",
        lambda *_: signals.disconnect_all(),
    )

    # Initial state
    update_notifications()

    return clock_button
