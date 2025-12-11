from ignis import utils
from ignis.services.hyprland import HyprlandService
from ignis.services.niri import NiriService
from ignis.window_manager import WindowManager

window_manager = WindowManager.get_default()
hypr = HyprlandService.get_default()
niri = NiriService.get_default()


# ═══════════════════════════════════════════════════════════════
# Focused monitor detection for Niri and Hyprland
# ═══════════════════════════════════════════════════════════════


def get_focused_monitor() -> int:
    # Try Hyprland first
    if hypr.is_available:
        try:
            active_ws = hypr.active_workspace
            monitor_name = active_ws.monitor

            # Find monitor ID by name
            for monitor_id in range(utils.get_n_monitors()):
                monitor = utils.get_monitor(monitor_id)
                if monitor.get_connector() == monitor_name:
                    return monitor_id
        except Exception:
            pass

    # Try Niri
    if niri.is_available:
        try:
            active_output = niri.active_output

            for monitor_id in range(utils.get_n_monitors()):
                monitor = utils.get_monitor(monitor_id)
                if monitor.get_connector() == active_output:
                    return monitor_id
        except Exception:
            pass
