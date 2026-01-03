import asyncio

from ignis import utils, widgets
from ignis.services.bluetooth import BluetoothService
from ignis.window_manager import WindowManager
from modules.utils.signal_manager import SignalManager
from settings import config

wm = WindowManager.get_default()


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


bluetooth = BluetoothService.get_default()


class BluetoothButton(widgets.Button):
    """Bluetooth toggle button with device connection status and battery"""

    def __init__(self):
        self._signals = SignalManager()
        self._device_signals = SignalManager()

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
        self._signals.connect(bluetooth, "notify::connected-devices", lambda *_: self._on_devices_changed())
        self._signals.connect(self, "destroy", lambda *_: self._cleanup())
        self._on_devices_changed()

    def _cleanup(self):
        """Cleanup all signal connections"""
        self._signals.disconnect_all()
        self._device_signals.disconnect_all()

    def _toggle(self):
        bluetooth.powered = not bluetooth.powered

    def _open_blueman(self):
        """Open blueman-manager and close system menu"""
        exec_async(config.system.bluetooth_manager)
        try:
            wm.close_window("ignis_SYSTEM_MENU")
        except:
            pass

    def _on_devices_changed(self):
        """Handle connected devices list changing - set up battery monitoring"""
        self._device_signals.disconnect_all()

        try:
            devices = bluetooth.connected_devices
            if devices:
                for dev in devices:
                    self._device_signals.connect(dev, "notify::battery-percentage", lambda *_: self._update())
        except Exception:
            pass

        self._update()

    def _update(self):
        """Update icon and styling based on Bluetooth state"""
        try:
            powered = bool(bluetooth.powered)
        except Exception:
            powered = False

        if powered:
            self._icon.image = "bluetooth-symbolic"
            self.remove_css_class("sys-top-btn-inactive")

            try:
                devices = bluetooth.connected_devices
            except Exception:
                devices = None

            if devices:
                tooltip_parts = ["Bluetooth: ON"]

                for dev in devices:
                    device_info = f"\nConnected: {dev.name}"

                    try:
                        battery = dev.battery_percentage
                        if battery is not None and battery >= 0:
                            device_info += f" ({int(battery)}%)"
                    except:
                        pass

                    tooltip_parts.append(device_info)

                tooltip_parts.append("\n\nClick: Open Bluetooth Manager\nRight-click: Turn OFF")
                self.set_tooltip_text("".join(tooltip_parts))
            else:
                self.set_tooltip_text(
                    "Bluetooth: ON\nNo devices connected\n\nClick: Open Bluetooth Manager\nRight-click: Turn OFF"
                )
        else:
            self._icon.image = "bluetooth-disabled-symbolic"
            self.add_css_class("sys-top-btn-inactive")
            self.set_tooltip_text("Bluetooth: OFF\n\nClick: Open Bluetooth Manager\nRight-click: Turn ON")
