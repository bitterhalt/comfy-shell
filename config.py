import os

from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager
from modules.bar.bar import create_bar
from modules.bar.bar_toggle import register_bar
from modules.bar.widgets.setting_pill import SystemPopup
from modules.launcher.launcher import AppLauncher
from modules.launcher.window_switcher import WindowSwitcher
from modules.notifications.integrated_center import IntegratedCenter
from modules.notifications.popup import init_notifications
from modules.notifications.task_popup import init_task_popup
from modules.osd.media_osd import MediaOsdWindow
from modules.osd.time_osd import TimeOsdWindow
from modules.osd.workspace_osd import init_workspace_osd, set_bar_visibility
from modules.overlays.power_overlay import PowerOverlay
from modules.overlays.recording_overlay import RecordingOverlay
from modules.recorder.recorder import register_recorder_commands
from modules.weather.weather_window import WeatherPopup

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

# Initialize notifications (ADD ALWAYS BEFORE BARS)
init_notifications()

# Initialize task popup
init_task_popup()

# Initialize workspace OSD
init_workspace_osd()


# For bar and barless mod (pure cli)
def _attach_bar_visibility_listener(bar_window):
    # called whenever Ignis sets bar.visible = True/False
    def _on_visible_changed(window, *_):
        set_bar_visibility(window.visible)

        #  Shows workspace OSD when the bar hides
        from modules.osd.workspace_osd import _osd_window

        if not window.visible and _osd_window:
            _osd_window.show_osd()

    bar_window.connect("notify::visible", _on_visible_changed)


for i in range(utils.get_n_monitors()):
    bar = create_bar(i)
    register_bar(bar)
    _attach_bar_visibility_listener(bar)


# Register commands
command_manager = CommandManager.get_default()

register_recorder_commands()
WeatherPopup()
AppLauncher()
PowerOverlay()
RecordingOverlay()
SystemPopup()
IntegratedCenter()
WindowSwitcher()
TimeOsdWindow()
MediaOsdWindow()
