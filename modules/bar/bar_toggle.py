"""
Bar Toggle Module - Manages bar visibility and workspace OSD
"""

from modules.osd.workspace_osd import set_bar_visibility
from modules.utils import save_bar_state

# Track all bar windows
_bar_windows = []


def register_bar(bar_window) -> None:
    """Register a bar window for toggling"""
    _bar_windows.append(bar_window)


def toggle_bars():
    """Toggle all registered bars"""

    if not _bar_windows:
        return

    # Check current state from first bar
    current_state = _bar_windows[0].visible
    new_state = not current_state

    # Toggle all bars
    for bar in _bar_windows:
        bar.set_visible(new_state)

    # Update workspace OSD state
    set_bar_visibility(new_state)

    # Save state for next restart
    save_bar_state(new_state)


def show_bars():
    """Show all bars"""

    for bar in _bar_windows:
        bar.set_visible(True)

    set_bar_visibility(True)
    save_bar_state(True)


def hide_bars():
    """Hide all bars"""

    for bar in _bar_windows:
        bar.set_visible(False)

    set_bar_visibility(False)
    save_bar_state(False)


def get_bar_state() -> bool:
    """Get current bar visibility state"""
    if not _bar_windows:
        return True
    state = _bar_windows[0].visible
    return state
