from ignis import utils, widgets
from ignis.services.audio import AudioService

audio = AudioService.get_default()


class AudioDeviceItem(widgets.Button):
    """Individual audio device button"""

    def __init__(self, stream, device_type: str):
        super().__init__(
            css_classes=["audio-device-item"],
            on_click=lambda *_: setattr(audio, device_type, stream),
            child=widgets.Box(
                spacing=10,
                child=[
                    widgets.Icon(
                        image="object-select-symbolic",
                        pixel_size=16,
                        visible=stream.bind("is_default"),
                    ),
                    widgets.Icon(
                        image=stream.icon_name,
                        pixel_size=22,
                    ),
                    widgets.Label(
                        label=stream.description,
                        ellipsize="end",
                        max_width_chars=28,
                        hexpand=True,
                        halign="start",
                    ),
                ],
            ),
        )


class AudioSection(widgets.Box):
    """Audio section with slider and expandable device list"""

    def __init__(self, stream, device_type: str):
        super().__init__(vertical=True, spacing=10)

        self.stream = stream
        self.device_type = device_type

        # Mute button
        mute_btn = widgets.Button(
            css_classes=["audio-menu-mute-btn"],
            child=widgets.Icon(
                image=stream.bind(
                    "is_muted",
                    lambda m: (
                        (
                            "audio-input-microphone-muted-symbolic"
                            if device_type == "microphone"
                            else "audio-volume-muted-symbolic"
                        )
                        if m
                        else (
                            "audio-input-microphone-symbolic"
                            if device_type == "microphone"
                            else "audio-volume-high-symbolic"
                        )
                    ),
                ),
                pixel_size=22,
            ),
            on_click=lambda *_: setattr(stream, "is_muted", not stream.is_muted),
        )

        # Volume slider
        slider = widgets.Scale(
            min=0,
            max=100,
            value=stream.bind("volume", lambda v: int(v or 0)),
            on_change=lambda w: setattr(stream, "volume", w.value),
            sensitive=stream.bind("is_muted", lambda m: not m),
            hexpand=True,
            css_classes=["audio-menu-slider"],
        )

        # Arrow button for expanding device list
        self._arrow = widgets.Arrow(
            pixel_size=18,
            rotated=False,
            css_classes=["audio-menu-arrow-icon"],
        )

        arrow_btn = widgets.Button(
            css_classes=["audio-menu-expand-btn"],
            child=self._arrow,
            on_click=lambda *_: self._toggle_revealer(),
        )

        # Main row
        row = widgets.Box(
            spacing=2,
            child=[mute_btn, slider, arrow_btn],
        )

        # Device list revealer
        self._revealer = widgets.Revealer(
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        self._device_list = widgets.Box(
            vertical=True,
            spacing=4,
        )
        self._revealer.child = self._device_list

        # Build section
        self.child = [row, self._revealer]

        # Populate devices
        self._populate_devices()
        audio.connect(f"{device_type}-added", lambda *_: self._populate_devices())
        audio.connect(f"notify::{device_type}", lambda *_: self._populate_devices())

    def _toggle_revealer(self):
        """Toggle device list visibility"""
        new_state = not self._revealer.reveal_child
        self._arrow.rotated = new_state
        self._revealer.reveal_child = new_state

    def _populate_devices(self):
        """Populate device list"""
        self._device_list.child = []
        streams = getattr(audio, f"{self.device_type}s", [])
        for stream in streams:
            self._device_list.append(AudioDeviceItem(stream, self.device_type))


class AudioMenuWindow(widgets.Window):
    """Popup audio menu - click outside to close"""

    def __init__(self):
        speaker_section = AudioSection(
            stream=audio.speaker,
            device_type="speaker",
        )

        mic_section = AudioSection(
            stream=audio.microphone,
            device_type="microphone",
        )

        content = widgets.Box(
            vertical=True,
            spacing=4,
            css_classes=["audio-menu"],
            child=[
                speaker_section,
                mic_section,
            ],
        )

        # Revealer for animation
        self._revealer = widgets.Revealer(
            child=content,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # Centered container
        centered = widgets.Box(
            valign="start",
            halign="end",
            css_classes=["audio-menu-container"],
            child=[self._revealer],
        )

        # Click outside to close overlay
        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["audio-menu-overlay"],
            on_click=lambda *_: self.toggle(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_btn,
            overlays=[centered],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_AUDIO_MENU",
            layer="top",
            popup=True,
            css_classes=["audio-menu-window"],
            child=root_overlay,
            kb_mode="on_demand",
        )

    def toggle(self):
        """Toggle menu visibility"""
        if not self.visible:
            self.visible = True
            utils.Timeout(10, lambda: setattr(self._revealer, "reveal_child", True))
        else:
            self._revealer.reveal_child = False
            utils.Timeout(
                self._revealer.transition_duration,
                lambda: setattr(self, "visible", False),
            )


# Global instance
_audio_menu_window = None


def get_audio_menu_window():
    """Get or create audio menu window"""
    global _audio_menu_window
    if _audio_menu_window is None:
        _audio_menu_window = AudioMenuWindow()
    return _audio_menu_window


def toggle_audio_menu():
    """Toggle audio menu"""
    window = get_audio_menu_window()
    window.toggle()
