import asyncio

from ignis import utils, widgets
from ignis.services.audio import AudioService
from ignis.services.network import NetworkService
from ignis.window_manager import WindowManager
from modules.bar.widgets.audio_menu_window import AudioSection
from modules.bar.widgets.bluetooth import BluetoothButton
from modules.bar.widgets.network_items import (
    EthernetItem,
    VpnNetworkItem,
    WifiNetworkItem,
)
from modules.bar.widgets.network_pill import NetworkPill
from modules.bar.widgets.system_info import SystemInfoWidget
from settings import config

wm = WindowManager.get_default()
audio = AudioService.get_default()
net = NetworkService.get_default()
wifi = net.wifi
vpn = net.vpn
ethernet = net.ethernet


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


class SystemPopup(widgets.Window):
    """System menu popup with quick settings and network controls"""

    def __init__(self):

        record_btn = widgets.Button(
            css_classes=["sys-top-btn", "unset"],
            on_click=lambda x: (
                wm.open_window("ignis_RECORDING_OVERLAY"),
                self.set_visible(False),
            ),
            child=widgets.Icon(image="camera-photo-symbolic", pixel_size=22),
        )

        bluetooth_btn = BluetoothButton()

        lock_btn = widgets.Button(
            css_classes=["sys-top-btn", "unset"],
            on_click=lambda x: (exec_async("hyprlock"), self.set_visible(False)),
            child=widgets.Icon(image="system-lock-screen-symbolic", pixel_size=22),
        )

        power_btn = widgets.Button(
            css_classes=["sys-top-btn", "unset"],
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

        # NETWORK PILL (WIDE, BETWEEN AUDIO AND CPU/RAM)
        network_pill = NetworkPill(self._net_revealer)

        # TOP ROW – LEFT (record+bt) and RIGHT (lock+power)
        top_row = widgets.Box(
            spacing=8,
            css_classes=["sys-top-row"],
            hexpand=True,
            child=[
                widgets.Box(
                    spacing=8,
                    child=[record_btn, bluetooth_btn],
                ),
                widgets.Box(
                    spacing=8,
                    hexpand=True,
                    halign="end",
                    child=[lock_btn, power_btn],
                ),
            ],
        )

        # AUDIO SLIDERS
        speaker = AudioSection(stream=audio.speaker, device_type="speaker")
        mic = AudioSection(stream=audio.microphone, device_type="microphone")

        audio_content = widgets.Box(
            vertical=True,
            spacing=10,
            css_classes=["sys-audio-pill"],
            child=[speaker, mic],
        )

        # MIDDLE WIFI PILL ROW (WIDE)
        middle_row = widgets.Box(
            css_classes=["sys-middle-row"],
            child=[network_pill],
        )

        system_info = SystemInfoWidget()

        # MAIN PANEL
        panel = widgets.Box(
            vertical=True,
            spacing=6,
            css_classes=["system-menu"],
            child=[
                top_row,
                audio_content,
                middle_row,
                self._net_revealer,
                system_info,
            ],
        )

        # Revealer
        self._revealer = widgets.Revealer(
            child=panel,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # OVERLAY CLICK-TO-CLOSE
        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["system-menu-overlay", "unset"],
            on_click=lambda x: wm.close_window("ignis_SYSTEM_MENU"),
        )

        root = widgets.Overlay(
            child=overlay_btn,
            overlays=[
                widgets.Box(
                    valign="start",
                    halign="end",
                    css_classes=["system-menu-container"],
                    child=[self._revealer],
                )
            ],
        )

        super().__init__(
            monitor=config.ui.primary_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_SYSTEM_MENU",
            layer="top",
            popup=True,
            css_classes=["system-menu-window", "unset"],
            child=root,
            kb_mode="on_demand",
        )

        self.connect("notify::visible", self._on_visible_change)

    def _on_visible_change(self, *_):
        """Handle reveal animation when window opens/closes"""
        if self.visible:
            self._revealer.reveal_child = True

            if wifi.devices:
                asyncio.create_task(self._scan_wifi())
        else:
            self._revealer.reveal_child = False

    def toggle(self):
        """Toggle system popup visibility"""
        self.visible = not self.visible

    async def _scan_wifi(self):
        """Scan for available WiFi networks"""
        try:
            await wifi.devices[0].scan()
        except Exception:
            pass
