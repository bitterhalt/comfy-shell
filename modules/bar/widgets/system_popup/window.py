"""Main system popup window"""

import asyncio

from ignis import utils, widgets
from ignis.services.audio import AudioService
from ignis.window_manager import WindowManager
from modules.bar.widgets.bluetooth import BluetoothButton
from settings import config

from .audio_section import AudioSection
from .network_section import NetworkSection  # ✅ Changed import
from .system_info_section import SystemInfoWidget

wm = WindowManager.get_default()
audio = AudioService.get_default()


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


class SystemPopup(widgets.Window):
    """System menu popup with quick settings and network controls"""

    def __init__(self):
        # Top row buttons
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

        # Audio sliders
        speaker = AudioSection(stream=audio.speaker, device_type="speaker")
        mic = AudioSection(stream=audio.microphone, device_type="microphone")

        audio_content = widgets.Box(
            vertical=True,
            spacing=10,
            css_classes=["sys-audio-pill"],
            child=[speaker, mic],
        )

        # Network section
        network_section = NetworkSection()

        network_content = widgets.Box(
            vertical=True,
            spacing=10,
            css_classes=["sys-network-pill"],
            child=[network_section],
        )

        # System info
        system_info = SystemInfoWidget()

        # Main panel
        panel = widgets.Box(
            vertical=True,
            spacing=6,
            css_classes=["system-menu"],
            child=[
                top_row,
                audio_content,
                network_content,
                system_info,
            ],
        )

        # Revealer for slide animation
        self._revealer = widgets.Revealer(
            child=panel,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # Overlay click-to-close
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
        else:
            self._revealer.reveal_child = False

    def toggle(self):
        """Toggle system popup visibility"""
        self.visible = not self.visible
