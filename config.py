import os

from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager

# Import the main bar creation function
from modules.bar.bar import create_bar

# Import bar toggle
from modules.bar.bar_toggle import register_bar

# Import launcher
from modules.launcher.launcher import toggle_launcher

# Import notification popup initialization
from modules.notifications.popup import init_notifications

# Import task popup initialization
from modules.notifications.task_popup import init_task_popup

# Import submap OSD (display only - controlled by bash watcher)
from modules.osd.submap_osd import hide_submap_osd, init_submap_osd, show_submap_osd

# Import workspace OSD
from modules.osd.workspace_osd import init_workspace_osd, set_bar_visibility

# Import recorder module
from modules.recorder.recorder import register_recorder_commands

# Import weather
from modules.weather.weather_window import toggle_weather_popup

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

# Initialize submap OSD
init_submap_osd()


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

command_manager.add_command("launcher-toggle", toggle_launcher)
command_manager.add_command("submap-show", show_submap_osd)
command_manager.add_command("submap-hide", hide_submap_osd)
command_manager.add_command("weather-popup-toggle", toggle_weather_popup)

# Register recorder commands
register_recorder_commands()
