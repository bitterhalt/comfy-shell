from ignis import utils, widgets
from ignis.services.audio import AudioService

audio = AudioService.get_default()

# Global OSD window instance
_osd_window = None


class VolumeOSD(widgets.Window):
    """On-screen display for volume changes"""

    def __init__(self):
        speaker = audio.speaker

        # Icon that updates with volume state
        icon = widgets.Icon(
            pixel_size=26,
            style="margin-right: 0.5rem;",
            image=speaker.bind("icon_name"),
        )

        # Volume slider (read-only display)
        slider = widgets.Scale(
            min=0,
            max=100,
            value=speaker.bind(
                "volume", lambda v: 0 if speaker.is_muted else int(v or 0)
            ),
            sensitive=False,  # Read-only
            hexpand=True,
            css_classes=["vol-track"],
        )

        # Container box
        content = widgets.Box(
            css_classes=["vol-container"],
            child=[icon, slider],
        )

        super().__init__(
            layer="overlay",
            anchor=["top"],
            namespace="ignis_OSD",
            visible=False,
            css_classes=["vol-window"],
            child=content,
        )

    def show_osd(self):
        """Show the OSD temporarily"""
        self.visible = True
        self._hide_delayed()

    @utils.debounce(2000)
    def _hide_delayed(self):
        """Hide after delay"""
        self.visible = False


def show_volume_osd():
    """Show the volume OSD (creates window on first call)"""
    global _osd_window

    if _osd_window is None:
        _osd_window = VolumeOSD()

    _osd_window.show_osd()
