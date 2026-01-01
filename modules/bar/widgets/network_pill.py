from ignis import widgets
from ignis.services.network import NetworkService

net = NetworkService.get_default()
wifi = net.wifi
vpn = net.vpn
ethernet = net.ethernet


def _generic_net_label() -> str:
    """
    Short text for the main Wi‑Fi pill.
    Prefer SSID for wifi, otherwise show a compact label.
    """
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
        return "Wi‑Fi"

    if not wifi.enabled:
        return "Airplane mode"
    return "Offline"


def _net_signal_percent() -> str:
    """Return a short signal/connection status string for the pill."""
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
    """Get the primary network icon based on connection status"""
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
