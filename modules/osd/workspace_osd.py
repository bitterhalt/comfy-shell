"""
Workspace OSD - Shows workspace changes when bar is hidden
Monitors Hyprland workspace events and displays minimal OSD
"""

from ignis import utils, widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService

hypr = HyprlandService.get_default()
niri = NiriService.get_default()

# Global state
_bar_visible = True
_osd_window = None


class WorkspaceOSD(widgets.Window):
    """Minimal workspace indicator OSD"""

    def __init__(self):
        # Workspace label
        self._label = widgets.Label(
            css_classes=["workspace-osd-label"],
        )

        # Icon - Using standard icon that exists everywhere
        icon = widgets.Icon(
            image="view-grid-symbolic",  # Changed from "workspaces-symbolic"
            pixel_size=30,
            css_classes=["workspace-osd-icon"],
        )

        # Container
        content = widgets.Box(
            css_classes=["workspace-osd"],
            spacing=12,
            child=[icon, self._label],
        )

        super().__init__(
            layer="overlay",
            anchor=["top"],
            namespace="ignis_WORKSPACE_OSD",
            visible=False,
            css_classes=["workspace-osd-window"],
            child=content,
        )

        # Connect to workspace changes
        if hypr.is_available:
            hypr.connect("notify::active-workspace", self._on_workspace_change)
        elif niri.is_available:
            niri.connect("notify::active-workspace", self._on_workspace_change)

    def _on_workspace_change(self, *args):
        """Handle workspace change"""
        # Only show if bar is hidden
        if _bar_visible:
            return

        # Get workspace info
        if hypr.is_available:
            ws_name = hypr.active_workspace.name
            # Handle special workspaces
            if ws_name.startswith("special:"):
                ws_name = ws_name.split(":")[-1].capitalize()
        elif niri.is_available:
            ws_name = str(niri.active_workspace.idx)
        else:
            return

        # Update label and show
        self._label.set_label(f"Workspace: {ws_name}")
        self.show_osd()

    def show_osd(self):
        """Show the OSD temporarily"""
        self.visible = True
        self._hide_delayed()

    @utils.debounce(1500)
    def _hide_delayed(self):
        """Hide after delay"""
        self.visible = False


def init_workspace_osd():
    """Initialize workspace OSD (call once at startup)"""
    global _osd_window
    if _osd_window is None:
        _osd_window = WorkspaceOSD()


def set_bar_visibility(visible: bool):
    """
    Update bar visibility state
    Call this when toggling the bar

    Args:
        visible: True if bar is visible, False if hidden
    """
    global _bar_visible
    _bar_visible = visible


def get_bar_visibility() -> bool:
    """Get current bar visibility state"""
    return _bar_visible
