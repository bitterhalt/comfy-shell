import os

import scripts.recorder

# Load SCSS
from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager

# Import bar
from modules.bar.bar import create_bar

# Import launcher
from modules.launcher.launcher import toggle_launcher

# Import integrated center (replaces old notification_center)
from modules.notifications.integrated_center import toggle_integrated_center

# Import notification popup initialization
from modules.notifications.popup import init_notifications

css = CssManager.get_default()


def compile_scss(path):
    compiled = utils.sass_compile(path=path)
    filtered = [
        line for line in compiled.split("\n") if not line.startswith("@charset")
    ]
    return "\n".join(filtered)


css.apply_css(
    CssInfoPath(
        name="main",
        compiler_function=compile_scss,
        path=os.path.join(utils.get_current_dir(), "style.scss"),
    )
)

# Initialize notifications
init_notifications()

# Initialize bar(s)
for i in range(utils.get_n_monitors()):
    create_bar(i)

# Register commands
command_manager = CommandManager.get_default()
command_manager.add_command("launcher-toggle", toggle_launcher)
command_manager.add_command("center-toggle", toggle_integrated_center)
