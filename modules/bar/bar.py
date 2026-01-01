from ignis import utils, widgets
from modules.utils import load_bar_state
from settings import config
from .widgets.battery import battery_widget
from .widgets.caffeine import caffeine_widget
from .widgets.clock import clock
from .widgets.focused_window import window_title
from .widgets.recorder import recording_indicator
from .widgets.system_indicator import system_indicator
from .widgets.workspaces import workspaces

# ───────────────────────────────────────────────
# LAYOUT
# ───────────────────────────────────────────────


def left_section(monitor_name: str):
    return widgets.Box(
        spacing=18,
        child=[
            workspaces(monitor_name),
            window_title(monitor_name),
        ],
    )


def center_section():
    return widgets.Box(
        spacing=12,
        child=[clock()],
    )


def right_section():
    return widgets.Box(
        child=[
            recording_indicator(),
            system_indicator(),
            battery_widget(),
            caffeine_widget(),
        ],
    )


# ───────────────────────────────────────────────
# BAR WINDOW CLASS
# ───────────────────────────────────────────────


class Bar(widgets.Window):
    """Bar window for a specific monitor"""

    def __init__(self, monitor_id: int = 0):
        monitor_name = utils.get_monitor(monitor_id).get_connector()
        initial_visible = load_bar_state()

        super().__init__(
            namespace=f"ignis_bar_{monitor_id}",
            monitor=monitor_id,
            anchor=["left", "top", "right"],
            exclusivity="exclusive",
            visible=initial_visible,
            child=widgets.CenterBox(
                css_classes=["bar"],
                start_widget=left_section(monitor_name),
                center_widget=center_section(),
                end_widget=right_section(),
            ),
        )


# ───────────────────────────────────────────────
# INITIALIZATION FUNCTION
# ───────────────────────────────────────────────


def init_bars():
    primary_monitor = config.ui.bar_monitor
    bar = Bar(primary_monitor)

    # Attach visibility listener for barless mode
    def _on_visible_changed(window, *_):
        from modules.osd.workspace_osd import _osd_window, set_bar_visibility

        set_bar_visibility(window.visible)

        # Show workspace OSD when bar hides
        if not window.visible and _osd_window:
            _osd_window.show_osd()

    bar.connect("notify::visible", _on_visible_changed)

    return bar
