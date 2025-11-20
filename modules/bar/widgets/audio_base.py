import time

from ignis import widgets
from ignis.services.audio import AudioService

audio = AudioService.get_default()


class AudioWidgetBase:
    """Base class for audio widgets (volume + mic)"""

    def __init__(
        self,
        device_getter,
        *,
        on_real_volume_change=None,
        on_click=None,
        on_right_click=None,
        hide_when_muted=False,
        pixel_size=20,
    ):
        """
        device_getter: function(audio_service) -> device (speaker or mic)
        on_real_volume_change: function(percent)
        on_click: function(device)
        on_right_click: function(device)
        hide_when_muted: bool — hide widget when muted
        pixel_size: icon size
        """

        self.device = device_getter(audio)
        self.on_real_volume_change = on_real_volume_change
        self.on_click = on_click or (lambda dev: None)
        self.on_right_click = on_right_click or (lambda dev: None)
        self.hide_when_muted = hide_when_muted
        self.pixel_size = pixel_size

        self._startup_time = time.time()  # Track startup time
        self._build_widget()
        self._connect_signals()
        self._update_icon_and_tooltip()

    # -----------------------------------------------------------
    # Widget creation
    # -----------------------------------------------------------
    def _build_widget(self):
        self.icon = widgets.Icon(
            image=self.device.icon_name,
            pixel_size=self.pixel_size,
        )

        # Outer widget — always a Button now
        self.widget = widgets.Button(
            css_classes=["audio-widget"],
            on_click=lambda *_: self.on_click(self.device),
            on_right_click=lambda *_: self.on_right_click(self.device),
            child=widgets.Box(child=[self.icon]),
            visible=True,
        )

    # -----------------------------------------------------------
    # Updates
    # -----------------------------------------------------------
    def _update_icon_and_tooltip(self):
        raw = self.device.volume or 0
        percent = int(max(0, min(raw, 100)))

        self.icon.set_property("image", self.device.icon_name)
        self.icon.set_tooltip_text(f"{self.device.description}\nvol: {percent}%")

        # Auto-hide if muted AND hide_when_muted=True
        if self.hide_when_muted:
            self.widget.visible = not self.device.is_muted

    # -----------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------
    def _handle_volume(self):
        raw = self.device.volume or 0
        percent = int(max(0, min(raw, 100)))

        # Ignore events within first 500ms of startup
        if time.time() - self._startup_time < 0.5:
            self._update_icon_and_tooltip()
            return

        # Real volume change
        if self.on_real_volume_change:
            self.on_real_volume_change(percent)

        self._update_icon_and_tooltip()

    def _handle_mute(self):
        self._update_icon_and_tooltip()

    def _handle_icon(self):
        self._update_icon_and_tooltip()

    def _handle_desc(self):
        self._update_icon_and_tooltip()

    # -----------------------------------------------------------
    # Wiring events
    # -----------------------------------------------------------
    def _connect_signals(self):
        self.device.connect("notify::volume", lambda *_: self._handle_volume())
        self.device.connect("notify::is-muted", lambda *_: self._handle_mute())
        self.device.connect("notify::icon-name", lambda *_: self._handle_icon())
        self.device.connect("notify::description", lambda *_: self._handle_desc())
