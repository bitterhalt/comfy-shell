from ignis import widgets
from ignis.services.audio import AudioService
from ignis.services.network import NetworkService
from ignis.services.bluetooth import BluetoothService
from ignis.window_manager import WindowManager
from modules.utils.signal_manager import SignalManager

wm = WindowManager.get_default()
audio = AudioService.get_default()
net = NetworkService.get_default()
wifi = net.wifi
ethernet = net.ethernet
vpn = net.vpn
bluetooth = BluetoothService.get_default()


def _speaker_icon():
    if audio.speaker.is_muted:
        return "audio-volume-muted-symbolic"
    return audio.speaker.icon_name


def _mic_visible():
    return not audio.microphone.is_muted


def _mic_icon():
    return (
        "microphone-sensitivity-muted-symbolic" if audio.microphone.is_muted else "microphone-sensitivity-high-symbolic"
    )


def _network_icon():
    if vpn.is_connected:
        return vpn.icon_name
    if ethernet.is_connected:
        return ethernet.icon_name
    if wifi.is_connected:
        return wifi.icon_name
    return "network-offline-symbolic"


def _bluetooth_icon():
    """Always return a generic bluetooth icon when visible."""
    return "bluetooth-symbolic"


def _bluetooth_visible():
    """Visible when bluetooth is powered on and service is available."""
    try:
        if not bluetooth.powered:
            return False
        devices = getattr(bluetooth, "connected_devices", None)
        return bool(devices)
    except Exception:
        return False


def system_indicator():
    """Cluster of volume + mic + network + bluetooth, whole thing clickable."""

    signals = SignalManager()

    speaker_icon = widgets.Icon(
        image=_speaker_icon(),
        pixel_size=22,
    )

    mic_icon = widgets.Icon(
        image=_mic_icon(),
        pixel_size=22,
        visible=_mic_visible(),
    )

    net_icon = widgets.Icon(
        image=_network_icon(),
        pixel_size=22,
    )

    bt_icon = widgets.Icon(
        image=_bluetooth_icon(),
        pixel_size=22,
        visible=_bluetooth_visible(),
    )

    inner = widgets.Box(
        css_classes=["system-indicator"],
        spacing=14,
        child=[speaker_icon, mic_icon, net_icon, bt_icon],
    )

    button = widgets.Button(
        css_classes=["system-indicator-button"],
        child=inner,
        on_click=lambda *_: wm.open_window("ignis_SYSTEM_MENU"),
    )

    def refresh(*_):
        speaker_icon.image = _speaker_icon()
        mic_icon.image = _mic_icon()
        mic_icon.visible = _mic_visible()
        net_icon.image = _network_icon()

        bt_icon.image = _bluetooth_icon()
        bt_icon.visible = _bluetooth_visible()

        if audio.speaker.is_muted:
            speaker_icon.add_css_class("muted")
        else:
            speaker_icon.remove_css_class("muted")

    refresh()

    # audio signals
    signals.connect(audio.speaker, "notify::is-muted", refresh)
    signals.connect(audio.speaker, "notify::volume", refresh)
    signals.connect(audio.microphone, "notify::is-muted", refresh)

    # network signals
    signals.connect(wifi, "notify::is-connected", refresh)
    signals.connect(wifi, "notify::icon-name", refresh)
    signals.connect(ethernet, "notify::is-connected", refresh)
    signals.connect(vpn, "notify::is-connected", refresh)

    # bluetooth signals (power + connected devices) — keep these so visibility updates
    signals.connect(bluetooth, "notify::powered", refresh)
    signals.connect(bluetooth, "notify::connected-devices", refresh)

    signals.connect(
        button,
        "destroy",
        lambda *_: signals.disconnect_all(),
    )

    return button
