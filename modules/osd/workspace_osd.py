from ignis import utils, widgets
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService
from settings import config

TIMEOUT = config.ui.workspace_osd_timeout
hypr = HyprlandService.get_default()
niri = NiriService.get_default()

# Global state
_bar_visible = True
_osd_window = None


class WorkspaceOSD(widgets.Window):
    def __init__(self):
        # Workspace label
        self._label = widgets.Label(
            css_classes=["workspace-osd-label"],
        )

        icon = widgets.Icon(
            image="view-grid-symbolic",
            pixel_size=22,
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

        if hypr.is_available:
            hypr.connect("notify::active-workspace", self._on_workspace_change)
        elif niri.is_available:
            niri.connect("notify::active-workspace", self._on_workspace_change)

    def _on_workspace_change(self, *args):
        """Handle workspace change"""
        if _bar_visible:
            return

        if hypr.is_available:
            ws_name = hypr.active_workspace.name
            # Handle special workspaces
            if ws_name.startswith("special:"):
                ws_name = ws_name.split(":")[-1].capitalize()
        elif niri.is_available:
            ws_name = str(niri.active_workspace.idx)
        else:
            return

        self._label.set_label(f"Workspace: {ws_name}")
        self.show_osd()

    def show_osd(self):
        """Show the OSD temporarily"""
        self.visible = True
        self._hide_delayed()

    @utils.debounce(TIMEOUT)
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
    Update bar visibility state.
    Called whenever bar is toggled.
    """
    global _bar_visible
    _bar_visible = visible

    if not visible and _osd_window:
        if hypr.is_available:
            ws_name = hypr.active_workspace.name
            if ws_name.startswith("special:"):
                ws_name = ws_name.split(":")[-1].capitalize()
        elif niri.is_available:
            ws_name = str(niri.active_workspace.idx)
        else:
            return

        _osd_window._label.set_label(f"Workspace: {ws_name}")
        _osd_window.show_osd()
