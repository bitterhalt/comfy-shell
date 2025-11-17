import os

# Import the script to register commands
import scripts.recorder
from ignis import utils
from ignis.command_manager import CommandManager
from ignis.css_manager import CssInfoPath, CssManager

# Import the main bar creation function
from modules.bar.bar import create_bar

# Import launcher
from modules.launcher.launcher import toggle_launcher

# Import notification center (creates the window as side effect)
from modules.notifications import notification_center  # noqa: F401

# Import notification popup initialization
from modules.notifications.popup import init_notifications

# # Import task menu
from modules.tasks.task_menu import toggle_task_menu

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

# Initialize the bars for all monitors
for i in range(utils.get_n_monitors()):
    create_bar(i)

# Register launcher command
command_manager = CommandManager.get_default()
command_manager.add_command("launcher-toggle", toggle_launcher)
command_manager.add_command("task-menu-toggle", toggle_task_menu)  # <-- A
