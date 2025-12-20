from ignis import widgets
from ignis.services.audio import AudioService
from ignis.services.network import NetworkService
from ignis.window_manager import WindowManager

wm = WindowManager.get_default()
audio = AudioService.get_default()
net = NetworkService.get_default()
wifi = net.wifi
ethernet = net.ethernet
vpn = net.vpn


def _speaker_icon():
    if audio.speaker.is_muted:
        return "audio-volume-muted-symbolic"
    return audio.speaker.icon_name


def _mic_visible():
    return not audio.microphone.is_muted


def _mic_icon():
    return (
        "microphone-sensitivity-muted-symbolic"
        if audio.microphone.is_muted
        else "microphone-sensitivity-high-symbolic"
    )


def _network_icon():
    if vpn.is_connected:
        return vpn.icon_name
    if ethernet.is_connected:
        return ethernet.icon_name
    if wifi.is_connected:
        return wifi.icon_name
    return "network-offline-symbolic"


def system_indicator():
    """Cluster of volume + mic + network, whole thing clickable."""

    speaker_icon = widgets.Icon(
        image=_speaker_icon(),
        pixel_size=22,
        css_classes=["system-indicator-speaker"],
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

    inner = widgets.Box(
        css_classes=["system-indicator"],
        spacing=14,
        child=[speaker_icon, mic_icon, net_icon],
    )

    button = widgets.Button(
        css_classes=["system-indicator-button"],
        child=inner,
        on_click=lambda x: wm.open_window("ignis_SYSTEM_MENU"),
    )

    def refresh(*_):
        speaker_icon.image = _speaker_icon()
        mic_icon.image = _mic_icon()
        mic_icon.visible = _mic_visible()
        net_icon.image = _network_icon()

        if audio.speaker.is_muted:
            speaker_icon.add_css_class("muted")
        else:
            speaker_icon.remove_css_class("muted")

    # initial state
    refresh()

    # connects: minimal but enough
    audio.speaker.connect("notify::is-muted", refresh)
    audio.speaker.connect("notify::volume", refresh)
    audio.microphone.connect("notify::is-muted", refresh)
    wifi.connect("notify::is-connected", refresh)
    wifi.connect("notify::icon-name", refresh)
    ethernet.connect("notify::is-connected", refresh)
    vpn.connect("notify::is-connected", refresh)

    return button
