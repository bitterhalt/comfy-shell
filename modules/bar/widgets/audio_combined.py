from ignis import widgets

from .mic import mic_widget
from .volume import volume_widget


def audio_widgets():
    return widgets.Box(
        css_classes=["audio-container"],
        spacing=6,
        child=[volume_widget(), mic_widget()],
    )
