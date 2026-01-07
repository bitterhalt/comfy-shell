from .battery import battery_widget
from .clock import clock
from .focused_window import window_title
from .network_items import EthernetItem, VpnNetworkItem, WifiNetworkItem
from .recorder import recording_indicator
from .system_indicator import system_indicator
from .system_popup import SystemPopup
from .workspaces import workspaces

__all__ = [
    "battery_widget",
    "clock",
    "EthernetItem",
    "recording_indicator",
    "system_indicator",
    "SystemPopup",
    "VpnNetworkItem",
    "WifiNetworkItem",
    "window_title",
    "workspaces",
]
