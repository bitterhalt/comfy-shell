import os

from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager

from modules.bar import Bar, register_bar, toggle_bars
from modules.bar.widgets import SystemPopup
from modules.notifications import IntegratedCenter, init_notifications, init_task_popup
from modules.osd import (
    MediaOsdWindow,
    TimeOsdWindow,
    VolumeOSD,
    init_workspace_osd,
    set_bar_visibility,
)
from modules.overlays import PowerOverlay, RecordingOverlay
from modules.recorder import register_recorder_commands
from modules.weather import WeatherPopup
from modules.windowlist import WindowSwitcher
from settings import config

css = CssManager.get_default()
command_manager = CommandManager.get_default()


# Custom compiler function that removes @charset
def compile_scss(path):
    compiled = utils.sass_compile(path=path)
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


# Use primary monitor from settings
PRIMARY_MONITOR = config.ui.primary_monitor

# Initialize notifications FIRST (must be before bars)
init_notifications()

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


# ═══════════════════════════════════════════════════════════════
# Handle initial bar state
# ═══════════════════════════════════════════════════════════════
def _handle_initial_bar_state():
    """Show workspace OSD on startup if bar starts hidden"""
    if not bar.visible:
        set_bar_visibility(False)
        from modules.osd.workspace_osd import _osd_window

        if _osd_window:
            utils.Timeout(500, lambda: _osd_window.show_osd())


utils.Timeout(100, _handle_initial_bar_state)

# Initialize components
TimeOsdWindow()
VolumeOSD()
MediaOsdWindow()
WeatherPopup()
PowerOverlay()
RecordingOverlay()
SystemPopup()
IntegratedCenter()
WindowSwitcher()

# Register commands
command_manager.add_command("toggle-bar", toggle_bars)
register_recorder_commands()
