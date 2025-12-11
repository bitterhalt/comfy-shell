import os

from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager
from modules.bar.bar import Bar
from modules.bar.bar_toggle import register_bar
from modules.bar.widgets.setting_pill import SystemPopup
from modules.launcher.launcher import AppLauncher
from modules.launcher.window_switcher import WindowSwitcher
from modules.notifications.integrated_center import IntegratedCenter
from modules.notifications.popup import NotificationPopup
from modules.notifications.task_popup import init_task_popup
from modules.osd.media_osd import MediaOsdWindow
from modules.osd.time_osd import TimeOsdWindow
from modules.osd.workspace_osd import init_workspace_osd, set_bar_visibility
from modules.overlays.power_overlay import PowerOverlay
from modules.overlays.recording_overlay import RecordingOverlay
from modules.recorder.recorder import register_recorder_commands
from modules.weather.weather_window import WeatherPopup
from settings import config

css = CssManager.get_default()


# Custom compiler function that removes @charset
def compile_scss(path):
    compiled = utils.sass_compile(path=path)
    # Remove @charset line that GTK doesn't support
    lines = compiled.split("\n")
    filtered_lines = [line for line in lines if not line.strip().startswith("@charset")]
    return "\n".join(filtered_lines)


css.apply_css(
    CssInfoPath(
        name="main",
        compiler_function=compile_scss,
        path=os.path.join(utils.get_current_dir(), "style.scss"),
    )
)

# ═══════════════════════════════════════════════════════════════
# MONITOR CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Use primary monitor from settings
PRIMARY_MONITOR = config.ui.primary_monitor

# ═══════════════════════════════════════════════════════════════
# INITIALIZATION ORDER
# ═══════════════════════════════════════════════════════════════

# Initialize notifications FIRST (must be before bars)
NotificationPopup(PRIMARY_MONITOR)

# Initialize task popup
init_task_popup()

# Initialize workspace OSD
init_workspace_osd()

# Initialize bar with visibility listener for barless mode
bar = Bar(PRIMARY_MONITOR)
register_bar(bar)


# Attach bar visibility listener
def _on_visible_changed(window, *_):
    set_bar_visibility(window.visible)

    # Shows workspace OSD when the bar hides
    from modules.osd.workspace_osd import _osd_window

    if not window.visible and _osd_window:
        _osd_window.show_osd()


bar.connect("notify::visible", _on_visible_changed)

# Initialize OSD windows (only on primary monitor)
TimeOsdWindow()
MediaOsdWindow()

# Initialize other windows (these are monitor-independent)
WeatherPopup()
AppLauncher()
PowerOverlay()
RecordingOverlay()
SystemPopup()
IntegratedCenter()
WindowSwitcher()

# Register commands
command_manager = CommandManager.get_default()
register_recorder_commands()
