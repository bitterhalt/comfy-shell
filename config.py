import os

# Import the script to register commands
import scripts.recorder
from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager

# Import the main bar creation function
from modules.bar.bar import create_bar

# Import bar toggle
from modules.bar.bar_toggle import register_bar, toggle_bars

# Import launcher
from modules.launcher.launcher import toggle_launcher

# Import integrated center
from modules.notifications.integrated_center import toggle_integrated_center

# Import notification popup initialization
from modules.notifications.popup import init_notifications

# Import submap OSD
from modules.osd.submap_osd import init_submap_osd

# Import workspace OSD
from modules.osd.workspace_osd import init_workspace_osd

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

# Initialize notifications (before bars)
init_notifications()

# Initialize workspace OSD
init_workspace_osd()

# Initialize submap OSD
init_submap_osd()

# Initialize the bars for all monitors
for i in range(utils.get_n_monitors()):
    bar = create_bar(i)
    register_bar(bar)  # Register for toggling

# Register commands
command_manager = CommandManager.get_default()
command_manager.add_command("launcher-toggle", toggle_launcher)
command_manager.add_command("bar-toggle", toggle_bars)
command_manager.add_command("center-toggle", toggle_integrated_center)
