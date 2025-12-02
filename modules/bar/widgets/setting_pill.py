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
from modules.bar.widgets.audio_menu_window import (
    AudioSection,
)  # reuse your existing audio UI

wm = WindowManager.get_default()
audio = AudioService.get_default()
net = NetworkService.get_default()
wifi = net.wifi
vpn = net.vpn
ethernet = net.ethernet


# ───────────────────────────────────────────────
# NETWORK ITEM WIDGETS
# ───────────────────────────────────────────────


class WifiNetworkItem(widgets.Button):
    def __init__(self, ap: WifiAccessPoint):
        super().__init__(
            css_classes=["net-wifi-item"],
            on_click=lambda *_: asyncio.create_task(ap.connect_to_graphical()),
            child=widgets.Box(
                spacing=8,
                child=[
                    widgets.Icon(
                        image=ap.bind(
                            "strength",
                            transform=lambda _v: ap.icon_name,
                        )
                    ),
                    widgets.Label(
                        label=ap.ssid or "Unknown",
                        halign="start",
                        ellipsize="end",
                    ),
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
                    widgets.Icon(
                        image="network-vpn-symbolic",
                        pixel_size=18,
                    ),
                    widgets.Label(
                        label=conn.name,
                        ellipsize="end",
                        max_width_chars=20,
                    ),
                    widgets.Label(
                        label=conn.bind(
                            "is_connected",
                            lambda c: "Disconnect" if c else "Connect",
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
                    widgets.Label(
                        label=dev.name or "Ethernet",
                        ellipsize="end",
                        max_width_chars=20,
                    ),
                    widgets.Label(
                        label=dev.bind(
                            "is_connected",
                            lambda c: "Disconnect" if c else "Connect",
                        ),
                        hexpand=True,
                        halign="end",
                    ),
                ],
            ),
        )


# ───────────────────────────────────────────────
# NETWORK + AIRPLANE PILLS
# ───────────────────────────────────────────────


def _safe_ssid() -> str:
    if wifi.is_connected and wifi.devices:
        try:
            ap = wifi.devices[0].ap
            if ap and ap.ssid:
                return ap.ssid
        except Exception:
            pass
    return "Wi-Fi"


def _primary_net_icon() -> str:
    if vpn.is_connected:
        return vpn.icon_name
    if ethernet.is_connected:
        return ethernet.icon_name
    if wifi.is_connected:
        return wifi.icon_name
    return "network-offline-symbolic"


class NetworkPill(widgets.Button):
    def __init__(self, revealer: widgets.Revealer):
        self._revealer = revealer

        self._icon = widgets.Icon(
            image=_primary_net_icon(),
            pixel_size=18,
        )
        self._label = widgets.Label(
            label=_safe_ssid(),
            ellipsize="end",
            max_width_chars=18,
        )
        self._arrow = widgets.Icon(
            image="go-next-symbolic",
            pixel_size=12,
        )

        inner = widgets.Box(
            spacing=6,
            child=[self._icon, self._label, self._arrow],
        )

        super().__init__(
            css_classes=["sys-pill", "sys-pill-primary"],
            child=inner,
            on_click=lambda *_: self._toggle(),
        )

        # Watch relevant properties
        watch_props = [
            (vpn, "is_connected"),
            (vpn, "active_vpn_id"),
            (ethernet, "is_connected"),
            (wifi, "is_connected"),
            (wifi, "icon_name"),
        ]
        for obj, prop in watch_props:
            sig = f"notify::{prop.replace('_', '-')}"
            obj.connect(sig, lambda *_: self._refresh())

        self._refresh()

    def _refresh(self):
        self._icon.image = _primary_net_icon()
        self._label.label = _safe_ssid()

    def _toggle(self):
        self._revealer.reveal_child = not self._revealer.reveal_child


class AirplanePill(widgets.Button):
    """Airplane = toggle wifi.enabled (Ethernet untouched)."""

    def __init__(self):
        self._icon = widgets.Icon(
            image="airplane-mode-symbolic",
            pixel_size=16,
        )
        self._label = widgets.Label(label=self._text())

        inner = widgets.Box(
            spacing=6,
            child=[self._icon, self._label],
        )

        super().__init__(
            css_classes=["sys-pill", "sys-pill-secondary"],
            child=inner,
            on_click=lambda *_: self._toggle(),
        )

        wifi.connect("notify::enabled", lambda *_: self._sync())

    def _text(self) -> str:
        return "Airplane Off" if wifi.enabled else "Airplane On"

    def _sync(self):
        self._label.label = self._text()

    def _toggle(self):
        wifi.enabled = not wifi.enabled
        self._sync()


# ───────────────────────────────────────────────
# MAIN SYSTEM POPUP
# ───────────────────────────────────────────────


class SystemPopup(widgets.Window):
    def __init__(self):

        record_btn = widgets.Button(
            css_classes=["sys-top-btn"],
            on_click=lambda x: wm.open_window("ignis_RECORDING_OVERLAY"),
            child=widgets.Icon(
                image="camera-photo-symbolic",
                pixel_size=22,
            ),
        )

        lock_btn = widgets.Button(
            css_classes=["sys-top-btn"],
            on_click=lambda x: utils.exec_sh("hyprlock"),
            child=widgets.Icon(
                image="system-lock-screen-symbolic",
                pixel_size=22,
            ),
        )

        power_btn = widgets.Button(
            css_classes=["sys-top-btn"],
            on_click=lambda x: wm.open_window("ignis_POWER_OVERLAY"),
            child=widgets.Icon(
                image="system-shutdown-symbolic",
                pixel_size=22,
            ),
        )

        top_row = widgets.Box(
            spacing=10,
            css_classes=["sys-top-row"],
            child=[
                record_btn,
                widgets.Box(hexpand=True),  # flexible spacer
                lock_btn,
                power_btn,
            ],
        )
        # ── Audio: speaker + mic, stacked ─────────────────────────
        speaker = AudioSection(
            stream=audio.speaker,
            device_type="speaker",
        )
        mic = AudioSection(
            stream=audio.microphone,
            device_type="microphone",
        )

        audio_column = widgets.Box(
            vertical=True,
            spacing=6,
            css_classes=["sys-audio-column"],
            child=[speaker, mic],
        )

        # ── Network details lists ─────────────────────────────────
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
                "devices",
                transform=lambda devs: [EthernetItem(d) for d in devs],
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

        # Collapsed by default
        self._net_revealer = widgets.Revealer(
            child=net_details,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # ── Second row pills ──────────────────────────────────────
        network_pill = NetworkPill(self._net_revealer)
        airplane_pill = AirplanePill()

        pills_row = widgets.Box(
            spacing=8,
            css_classes=["sys-pills-row"],
            child=[network_pill, airplane_pill],
        )

        # ── Panel content ─────────────────────────────────────────
        panel = widgets.Box(
            vertical=True,
            spacing=12,
            css_classes=["system-menu"],
            child=[
                top_row,
                audio_column,
                pills_row,
                self._net_revealer,
            ],
        )

        # GNOME-like popup: top-right, click-outside-to-close
        container = widgets.Box(
            valign="start",
            halign="end",
            css_classes=["system-menu-container"],
            child=[panel],
        )

        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["system-menu-overlay"],
            on_click=lambda *_: toggle_system_popup(),
        )

        root = widgets.Overlay(
            child=overlay_btn,
            overlays=[container],
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


# ───────────────────────────────────────────────
# SINGLETON HELPERS
# ───────────────────────────────────────────────


def toggle_system_popup() -> None:
    try:
        wm.toggle_window("ignis_SYSTEM_MENU")
    except:
        # Window doesn't exist yet, create it
        SystemPopup()
        wm.toggle_window("ignis_SYSTEM_MENU")
