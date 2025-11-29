from ignis import utils, widgets
from modules.bar.widgets.audio_combined import audio_widgets

from .widgets.battery import battery_widget
from .widgets.clock import clock
from .widgets.network import network_widget
from .widgets.power_overlay import toggle_power_overlay
from .widgets.recorder import recording_indicator
from .widgets.title import window_title
from .widgets.workspaces import workspaces

# ───────────────────────────────────────────────
# LAYOUT
# ───────────────────────────────────────────────


def left_section(monitor_name: str):
    return widgets.Box(
        spacing=12,
        child=[
            workspaces(monitor_name),
            window_title(monitor_name),
        ],
    )


def center_section():
    return widgets.Box(
        spacing=2,
        child=[clock()],
    )


def right_section():
    return widgets.Box(
        spacing=12,
        child=[
            recording_indicator(),
            network_widget(),
            audio_widgets(),
            battery_widget(),
            widgets.Button(
                css_classes=["power-menu-button"],
                on_click=lambda *_: toggle_power_overlay(),
                child=widgets.Icon(
                    image="system-shutdown-symbolic",
                    pixel_size=22,
                ),
            ),
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
