import asyncio

from ignis import utils, widgets
from ignis.services.audio import AudioService
from ignis.services.network import (
    EthernetDevice,
    NetworkService,
    VpnConnection,
    WifiAccessPoint,
)
from ignis.window_manager import WindowManager
from modules.bar.widgets.audio_menu_window import AudioSection

wm = WindowManager.get_default()
audio = AudioService.get_default()
net = NetworkService.get_default()
wifi = net.wifi
vpn = net.vpn
ethernet = net.ethernet


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


# ───────────────────────────────────────────────
# NETWORK LIST ITEMS
# ───────────────────────────────────────────────


class WifiNetworkItem(widgets.Button):
    def __init__(self, ap: WifiAccessPoint):
        super().__init__(
            css_classes=["net-wifi-item"],
            on_click=lambda *_: asyncio.create_task(ap.connect_to_graphical()),
            child=widgets.Box(
                spacing=8,
                child=[
                    widgets.Icon(image=ap.bind("strength", lambda _v: ap.icon_name)),
                    widgets.Label(label=ap.ssid or "Unknown", ellipsize="end"),
                    widgets.Icon(
                        image="object-select-symbolic",
                        visible=ap.bind("is_connected"),
                        hexpand=True,
                        halign="end",
                    ),
                ],
            ),
        )


class VpnNetworkItem(widgets.Button):
    def __init__(self, conn: VpnConnection):
        super().__init__(
            css_classes=["net-vpn-item"],
            on_click=lambda *_: asyncio.create_task(conn.toggle_connection()),
            child=widgets.Box(
                spacing=8,
                child=[
                    widgets.Icon(image="network-vpn-symbolic", pixel_size=18),
                    widgets.Label(label=conn.name, ellipsize="end", max_width_chars=20),
                    widgets.Label(
                        label=conn.bind(
                            "is_connected", lambda c: "Disconnect" if c else "Connect"
                        ),
                        hexpand=True,
                        halign="end",
                    ),
                ],
            ),
        )


class EthernetItem(widgets.Button):
    def __init__(self, dev: EthernetDevice):
        super().__init__(
            css_classes=["net-ethernet-item"],
            on_click=lambda *_: (
                asyncio.create_task(dev.disconnect_from())
                if dev.is_connected
                else asyncio.create_task(dev.connect_to())
            ),
            child=widgets.Box(
                spacing=8,
                child=[
                    widgets.Icon(image="network-wired-symbolic"),
                    widgets.Label(label=dev.name or "Ethernet", ellipsize="end"),
                    widgets.Label(
                        label=dev.bind(
                            "is_connected", lambda c: "Disconnect" if c else "Connect"
                        ),
                        hexpand=True,
                        halign="end",
                    ),
                ],
            ),
        )


# ───────────────────────────────────────────────
# GENERIC NETWORK LABEL + TOOLTIP
# ───────────────────────────────────────────────


def _generic_net_label() -> str:
    if wifi.is_connected:
        return "wifi"
    if ethernet.is_connected:
        return "eth"
    if vpn.is_connected:
        return "vpn"
    return "offline"


def _net_tooltip() -> str:
    if wifi.is_connected and wifi.devices:
        try:
            ap = wifi.devices[0].ap
            return f"SSID: {ap.ssid}\nSignal: {ap.strength}%"
        except Exception:
            return "Wi-Fi connected"
    if ethernet.is_connected:
        return "Ethernet connected"
    if vpn.is_connected:
        return f"VPN: {vpn.active_vpn_id}"
    return "No network"


def _primary_net_icon() -> str:
    if vpn.is_connected:
        return vpn.icon_name
    if ethernet.is_connected:
        return ethernet.icon_name
    if wifi.is_connected:
        return wifi.icon_name
    return "network-offline-symbolic"


# ───────────────────────────────────────────────
# NETWORK PILL (SITS IN TOP ROW)
# ───────────────────────────────────────────────


class NetworkPill(widgets.Button):
    def __init__(self, revealer: widgets.Revealer):
        self._revealer = revealer

        self._icon = widgets.Icon(image=_primary_net_icon(), pixel_size=18)
        self._label = widgets.Label(
            label=_generic_net_label(), ellipsize="end", max_width_chars=12
        )
        self._arrow = widgets.Icon(image="go-next-symbolic", pixel_size=12)

        inner = widgets.Box(
            spacing=6,
            child=[self._icon, self._label, self._arrow],
        )

        super().__init__(
            css_classes=["sys-pill", "sys-pill-primary"],
            child=inner,
            on_click=lambda *_: self._toggle(),
        )

        # Tooltip
        self.set_tooltip_text(_net_tooltip())

        # Update on events
        for obj, prop in [
            (wifi, "is_connected"),
            (wifi, "strength"),
            (ethernet, "is_connected"),
            (vpn, "is_connected"),
        ]:
            obj.connect(f"notify::{prop.replace('_', '-')}", lambda *_: self._refresh())

        self._refresh()

    def _refresh(self):
        self._icon.image = _primary_net_icon()
        self._label.label = _generic_net_label()
        self.set_tooltip_text(_net_tooltip())

    def _toggle(self):
        self._revealer.reveal_child = not self._revealer.reveal_child


# ───────────────────────────────────────────────
# AIRPLANE BUTTON
# ───────────────────────────────────────────────


class AirplaneButton(widgets.Button):
    def __init__(self):
        super().__init__(
            css_classes=["sys-top-btn"],
            on_click=lambda *_: self._toggle(),
            child=widgets.Icon(image="airplane-mode-symbolic", pixel_size=22),
        )
        self._update()
        wifi.connect("notify::enabled", lambda *_: self._update())

    def _toggle(self):
        wifi.enabled = not wifi.enabled

    def _update(self):
        if wifi.enabled:
            self.remove_css_class("sys-top-btn-active")
        else:
            self.add_css_class("sys-top-btn-active")


# ───────────────────────────────────────────────
# SYSTEM POPUP
# ───────────────────────────────────────────────


class SystemPopup(widgets.Window):
    def __init__(self):

        record_btn = widgets.Button(
            css_classes=["sys-top-btn"],
            on_click=lambda x: (
                wm.open_window("ignis_RECORDING_OVERLAY"),
                self.set_visible(False),
            ),
            child=widgets.Icon(image="camera-photo-symbolic", pixel_size=22),
        )

        airplane_btn = AirplaneButton()

        lock_btn = widgets.Button(
            css_classes=["sys-top-btn"],
            on_click=lambda x: (exec_async("hyprlock"), self.set_visible(False)),
            child=widgets.Icon(image="system-lock-screen-symbolic", pixel_size=22),
        )

        power_btn = widgets.Button(
            css_classes=["sys-top-btn"],
            on_click=lambda x: (
                wm.open_window("ignis_POWER_OVERLAY"),
                self.set_visible(False),
            ),
            child=widgets.Icon(image="system-shutdown-symbolic", pixel_size=22),
        )

        # NETWORK REVEALER
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
            child=ethernet.bind(
                "devices", transform=lambda devs: [EthernetItem(d) for d in devs]
            ),
        )

        vpn_section = widgets.Box(
            vertical=True,
            spacing=4,
            child=vpn.bind(
                "connections",
                transform=lambda conns: [VpnNetworkItem(c) for c in conns],
            ),
        )

        net_details = widgets.Box(
            vertical=True,
            spacing=6,
            css_classes=["sys-net-details"],
            child=[wifi_section, ethernet_section, vpn_section],
        )

        self._net_revealer = widgets.Revealer(
            child=net_details,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # NETWORK PILL
        network_pill = NetworkPill(self._net_revealer)

        # TOP ROW WITH WIFI PILL IN CENTER
        top_row = widgets.Box(
            spacing=10,
            css_classes=["sys-top-row"],
            child=[
                record_btn,
                widgets.Box(
                    hexpand=True,
                    halign="center",
                    child=[network_pill],
                ),
                airplane_btn,
                lock_btn,
                power_btn,
            ],
        )

        # AUDIO SLIDERS
        speaker = AudioSection(stream=audio.speaker, device_type="speaker")
        mic = AudioSection(stream=audio.microphone, device_type="microphone")

        audio_content = widgets.Box(
            vertical=True,
            spacing=6,
            css_classes=["sys-audio-column"],
            child=[speaker, mic],
        )

        # MAIN PANEL
        panel = widgets.Box(
            vertical=True,
            spacing=12,
            css_classes=["system-menu"],
            child=[
                top_row,
                audio_content,
                self._net_revealer,
            ],
        )

        # OVERLAY CLICK-TO-CLOSE
        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["system-menu-overlay"],
            on_click=lambda *_: wm.close_window("ignis_SYSTEM_MENU"),
        )

        root = widgets.Overlay(
            child=overlay_btn,
            overlays=[
                widgets.Box(
                    valign="start",
                    halign="end",
                    css_classes=["system-menu-container"],
                    child=[panel],
                )
            ],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_SYSTEM_MENU",
            layer="top",
            popup=True,
            css_classes=["system-menu-window"],
            child=root,
            kb_mode="on_demand",
        )

    def toggle(self):
        self.visible = not self.visible
        if self.visible and wifi.devices:
            asyncio.create_task(self._scan_wifi())

    async def _scan_wifi(self):
        try:
            await wifi.devices[0].scan()
        except Exception:
            pass
