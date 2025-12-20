import asyncio

from ignis import utils, widgets
from ignis.services.bluetooth import BluetoothService


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


bluetooth = BluetoothService.get_default()


class BluetoothButton(widgets.Button):
    """Bluetooth toggle button with device connection status"""

    def __init__(self):
        self._icon = widgets.Icon(
            image="bluetooth-symbolic",
            pixel_size=22,
        )

        super().__init__(
            css_classes=["sys-top-btn", "unset"],
            child=self._icon,
            on_click=lambda *_: exec_async("blueman-manager"),
            on_right_click=lambda *_: self._toggle(),
        )

        self._update()
        bluetooth.connect("notify:: powered", lambda *_: self._update())
        bluetooth.connect("notify::connected-devices", lambda *_: self._update())

    def _toggle(self):
        bluetooth.powered = not bluetooth.powered

    def _update(self):
        powered = bluetooth.powered
        devices = bluetooth.connected_devices

        if powered:
            self.remove_css_class("sys-top-btn-active")

            if devices:
                dev = devices[0]
                self._icon.image = dev.icon_name or "bluetooth-symbolic"
                self.set_tooltip_text(f"Bluetooth:  ON\nConnected to: {dev.name}")
            else:
                self._icon.image = "bluetooth-symbolic"
                self.set_tooltip_text("Bluetooth: ON\nNo devices connected")
        else:
            self.add_css_class("sys-top-btn-active")
            self._icon.image = "bluetooth-disabled-symbolic"
            self.set_tooltip_text(
                "Bluetooth: OFF\n"
                "Click to open Blueman Manager\n"
                "Right-click to enable"
            )

