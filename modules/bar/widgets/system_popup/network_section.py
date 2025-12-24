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


class NetworkPill(widgets.Button):
    """Main network status pill with expandable network list"""

    def __init__(self, revealer: widgets.Revealer):
        self._revealer = revealer

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

        inner = widgets.Box(
            spacing=6,
            child=[self._icon, self._label, self._percent],
        )

        super().__init__(
            css_classes=["sys-pill", "sys-pill-primary", "unset"],
            child=inner,
            hexpand=True,
            on_click=lambda *_: self._toggle(),
            on_right_click=lambda *_: self._toggle_airplane(),
        )

        # Connect to network changes
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

    def _toggle(self):
        """Toggle network list visibility"""
        self._revealer.reveal_child = not self._revealer.reveal_child

    def _toggle_airplane(self):
        """Toggle airplane mode (WiFi enable/disable)"""
        wifi.enabled = not wifi.enabled


def create_network_section() -> tuple[widgets.Button, widgets.Revealer]:
    """
    Create network section with pill and details revealer

    Returns:
        tuple: (NetworkPill, Revealer with network details)
    """
    # WiFi section
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

    # Ethernet section
    ethernet_section = widgets.Box(
        vertical=True,
        spacing=4,
        child=ethernet.bind(
            "devices", transform=lambda devs: [EthernetItem(d) for d in devs]
        ),
    )

    # VPN section
    vpn_section = widgets.Box(
        vertical=True,
        spacing=4,
        child=vpn.bind(
            "connections",
            transform=lambda conns: [VpnNetworkItem(c) for c in conns],
        ),
    )

    # Network details container
    net_details = widgets.Box(
        vertical=True,
        spacing=6,
        css_classes=["sys-net-details"],
        child=[wifi_section, ethernet_section, vpn_section],
    )

    # Revealer for network list
    revealer = widgets.Revealer(
        child=net_details,
        reveal_child=False,
        transition_type="slide_down",
        transition_duration=180,
    )

    # Network pill
    pill = NetworkPill(revealer)

    return pill, revealer
