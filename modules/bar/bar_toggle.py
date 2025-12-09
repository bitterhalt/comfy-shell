"""
Bar Toggle Module - Manages bar visibility and workspace OSD
Integrates with Hyprland keybinds
"""

from modules.osd.workspace_osd import set_bar_visibility

# Track all bar windows
_bar_windows = []


# modules/bar/bar_toggle.py
def register_bar(bar_window) -> None:
    """Register a bar window for toggling"""
    _bar_windows.append(bar_window)


def toggle_bars():
    """Toggle all registered bars"""
    if not _bar_windows:
        return

    # Check current state from first bar
    current_state = _bar_windows[0].visible

    # Toggle all bars
    for bar in _bar_windows:
        bar.set_visible(not current_state)

    # Update workspace OSD state
    set_bar_visibility(not current_state)

    print(f"Bars {'hidden' if current_state else 'shown'}")


def show_bars():
    """Show all bars"""
    for bar in _bar_windows:
        bar.set_visible(True)
    set_bar_visibility(True)


def hide_bars():
    """Hide all bars"""
    for bar in _bar_windows:
        bar.set_visible(False)
    set_bar_visibility(False)


def get_bar_state() -> bool:
    """Get current bar visibility state"""
    if not _bar_windows:
        return True
    return _bar_windows[0].visible
