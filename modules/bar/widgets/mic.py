from modules.bar.widgets.audio_base import AudioWidgetBase


def mic_widget():
    return AudioWidgetBase(
        device_getter=lambda audio: audio.microphone,
        pixel_size=22,
        hide_when_muted=True,  # mic shows only when active
        on_click=lambda dev: setattr(dev, "is_muted", not dev.is_muted),
        on_right_click=None,  # no right-click by default
        on_real_volume_change=None,  # mic does NOT show OSD
    ).widget
