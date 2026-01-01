import asyncio
from ignis import widgets
from ignis.services.network import NetworkService
from modules.bar.widgets.network_items import (
    EthernetItem,
    VpnNetworkItem,
    WifiNetworkItem,
)

net = NetworkService.get_default()
wifi = net.wifi
ethernet = net.ethernet
vpn = net.vpn


def _generic_net_label() -> str:
    """Short text for the main Wi-Fi pill"""
    if vpn.is_connected:
        return "VPN"
    if ethernet.is_connected:
        return "Ethernet"
    if wifi.is_connected and wifi.devices:
        try:
            ap = wifi.devices[0].ap
            if ap and ap.ssid:
                return ap.ssid
        except Exception:
            pass
        return "Wi-Fi"
    if not wifi.enabled:
        return "Airplane mode"
    return "Offline"


def _net_signal_percent() -> str:
    """Return signal/connection status string"""
    if wifi.is_connected and wifi.devices:
        try:
            ap = wifi.devices[0].ap
            if ap is not None and ap.strength is not None:
                return f"{ap.strength}%"
        except Exception:
            return "…"
    if vpn.is_connected:
        return "VPN"
    if ethernet.is_connected:
        return "LAN"
    return ""


def _primary_net_icon() -> str:
    """Get primary network icon"""
    if vpn.is_connected:
        return vpn.icon_name
    if ethernet.is_connected:
        return ethernet.icon_name
    if wifi.is_connected:
        return wifi.icon_name
    return "network-offline-symbolic"


class NetworkSection(widgets.Box):
    """Network section with pill and expandable network list"""

    def __init__(self):
        super().__init__(vertical=True, spacing=10)

        self._icon = widgets.Icon(image=_primary_net_icon(), pixel_size=22)
        self._label = widgets.Label(
            label=_generic_net_label(),
            ellipsize="end",
            max_width_chars=16,
        )
        self._percent = widgets.Label(
            label=_net_signal_percent(),
            halign="end",
            hexpand=True,
        )

        pill_content = widgets.Box(
            spacing=6,
            child=[self._icon, self._label, self._percent],
        )

        pill_button = widgets.Button(
            css_classes=["sys-pill", "sys-pill-primary", "unset"],
            child=pill_content,
            hexpand=True,
            on_click=lambda *_: self._toggle_list(),
            on_right_click=lambda *_: self._toggle_airplane(),
        )

        wifi_section = widgets.Box(
            vertical=True,
            spacing=4,
            child=wifi.bind(
                "devices",
                transform=lambda devs: (
                    [widgets.Label(label="No Wi-Fi device detected")]
                    if not devs
                    else devs[0].bind(
                        "access_points",
                        transform=lambda aps: [WifiNetworkItem(a) for a in aps],
                    )
                ),
            ),
        )

        ethernet_section = widgets.Box(
            vertical=True,
            spacing=4,
            child=ethernet.bind("devices", transform=lambda devs: [EthernetItem(d) for d in devs]),
        )

        vpn_section = widgets.Box(
            vertical=True,
            spacing=4,
            child=vpn.bind(
                "connections",
                transform=lambda conns: [VpnNetworkItem(c) for c in conns],
            ),
        )

        self._device_list = widgets.Box(
            vertical=True,
            spacing=6,
            visible=False,
            css_classes=["sys-net-details"],
            child=[wifi_section, ethernet_section, vpn_section],
        )

        self.child = [pill_button, self._device_list]

        for obj, prop in [
            (wifi, "is_connected"),
            (wifi, "strength"),
            (wifi, "enabled"),
            (ethernet, "is_connected"),
            (vpn, "is_connected"),
        ]:
            obj.connect(f"notify::{prop.replace('_', '-')}", lambda *_: self._refresh())

        self._refresh()

    def _refresh(self):
        """Update network pill display"""
        self._icon.image = _primary_net_icon()
        self._label.label = _generic_net_label()
        self._percent.label = _net_signal_percent()

    def _toggle_list(self):
        """Toggle network list visibility"""
        new_state = not self._device_list.visible
        self._device_list.visible = new_state

        if new_state and wifi.devices:
            asyncio.create_task(wifi.devices[0].scan())

    def _toggle_airplane(self):
        """Toggle airplane mode (WiFi enable/disable)"""
        wifi.enabled = not wifi.enabled
