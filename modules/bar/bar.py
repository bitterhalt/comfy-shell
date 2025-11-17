from ignis import utils, widgets
from modules.bar.widgets.audio_combined import audio_widgets
from modules.notifications.notification_button import notification_button

from .widgets.battery import battery_widget
from .widgets.clock import clock
from .widgets.network import network_widget
from .widgets.power import power_menu
from .widgets.recorder import recording_indicator
from .widgets.timer import timer_widget
from .widgets.title import window_title
from .widgets.workspaces import workspaces

# ───────────────────────────────────────────────
# LAYOUT
# ───────────────────────────────────────────────


def left_section(monitor_name: str):
    return widgets.Box(
        spacing=8,
        child=[
            workspaces(monitor_name),
            window_title(monitor_name),
        ],
    )


def center_section():
    return widgets.Box(child=[clock()])


def right_section():
    return widgets.Box(
        spacing=12,
        child=[
            notification_button(),
            timer_widget(),
            network_widget(),
            audio_widgets(),
            battery_widget(),
            recording_indicator(),
            power_menu(),
        ],
    )


# ───────────────────────────────────────────────
# BAR WINDOW
# ───────────────────────────────────────────────


def create_bar(monitor_id: int = 0):
    monitor_name = utils.get_monitor(monitor_id).get_connector()

    return widgets.Window(
        namespace=f"ignis_bar_{monitor_id}",
        monitor=monitor_id,
        anchor=["left", "top", "right"],
        exclusivity="exclusive",
        child=widgets.CenterBox(
            css_classes=["bar"],
            start_widget=left_section(monitor_name),
            center_widget=center_section(),
            end_widget=right_section(),
        ),
    )
