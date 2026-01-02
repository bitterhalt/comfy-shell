import asyncio

from ignis import utils, widgets
from ignis.services.bluetooth import BluetoothService
from ignis.window_manager import WindowManager
from modules.utils.signal_manager import SignalManager

wm = WindowManager.get_default()


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


bluetooth = BluetoothService.get_default()


class BluetoothButton(widgets.Button):
    """Bluetooth toggle button with device connection status - always visible"""

    def __init__(self):
        self._signals = SignalManager()
        self._icon = widgets.Icon(
            image="bluetooth-symbolic",
            pixel_size=22,
        )

        super().__init__(
            css_classes=["sys-top-btn", "unset"],
            child=self._icon,
            on_click=lambda *_: self._open_blueman(),
            on_right_click=lambda *_: self._toggle(),
        )

        self._update()
        self._signals.connect(bluetooth, "notify::powered", lambda *_: self._update())
        self._signals.connect(bluetooth, "notify::connected-devices", lambda *_: self._update())
        self._signals.connect(self, "destroy", lambda *_: self._signals.disconnect_all())

    def _toggle(self):
        bluetooth.powered = not bluetooth.powered

    def _open_blueman(self):
        """Open blueman-manager and close system menu"""
        exec_async("blueman-manager")
        try:
            wm.close_window("ignis_SYSTEM_MENU")
        except:
            pass

    def _update(self):
        """Update icon and styling based on Bluetooth state"""
        try:
            powered = bool(bluetooth.powered)
        except Exception:
            powered = False

        # Always visible now - removed self.visible = powered

        if powered:
            # Bluetooth is ON
            self._icon.image = "bluetooth-symbolic"
            self.remove_css_class("sys-top-btn-inactive")

            try:
                devices = bluetooth.connected_devices
            except Exception:
                devices = None

            if devices:
                dev = devices[0]
                self.set_tooltip_text(
                    f"Bluetooth: ON\nConnected to: {dev.name}\n\nClick: Open Bluetooth Manager\nRight-click: Turn OFF"
                )
            else:
                self.set_tooltip_text(
                    "Bluetooth: ON\nNo devices connected\n\nClick: Open Bluetooth Manager\nRight-click: Turn OFF"
                )
        else:
            # Bluetooth is OFF
            self._icon.image = "bluetooth-disabled-symbolic"
            self.add_css_class("sys-top-btn-inactive")
            self.set_tooltip_text("Bluetooth: OFF\n\nClick: Open Bluetooth Manager\nRight-click: Turn ON")
