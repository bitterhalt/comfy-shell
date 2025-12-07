from ignis import utils, widgets
from ignis.services.mpris import MprisService

mpris = MprisService.get_default()
_media_osd_window = None


class MediaOsdWindow(widgets.Window):
    def __init__(self):
        self._timeout = None

        # Album art
        self._album_art = widgets.Icon(
            image="folder-music-symbolic",
            pixel_size=80,
            css_classes=["media-osd-art"],
        )

        # Title
        self._title_label = widgets.Label(
            label="No Title",
            css_classes=["media-osd-title"],
            ellipsize="end",
            max_width_chars=35,
        )

        # Artist
        self._artist_label = widgets.Label(
            label="No Artist",
            css_classes=["media-osd-artist"],
            ellipsize="end",
            max_width_chars=35,
        )

        # Status icon (play/pause)
        self._status_icon = widgets.Icon(
            image="media-playback-start-symbolic",
            pixel_size=18,
            css_classes=["media-osd-status-icon"],
        )

        # Text container
        text_box = widgets.Box(
            vertical=True,
            spacing=4,
            hexpand=True,
            child=[self._title_label, self._artist_label],
        )

        # Content row (art + text + status)
        content_row = widgets.Box(
            spacing=16,
            child=[self._album_art, text_box, self._status_icon],
        )

        # Pill
        pill = widgets.Box(
            css_classes=["media-osd"],
            child=[content_row],
        )

        # Center aligner
        center_align = widgets.Box(
            halign="center",
            valign="start",
            child=[pill],
        )

        # Root
        root = widgets.Box(
            halign="fill",
            valign="start",
            child=[center_align],
        )

        super().__init__(
            layer="overlay",
            anchor=["top"],
            namespace="ignis_MEDIA_OSD",
            visible=False,
            css_classes=["media-osd-window"],
            child=root,
        )

        self.connect("notify::visible", self._on_visible_changed)

    def _on_visible_changed(self, *_):
        if self.visible:
            self._update_content()

            if self._timeout:
                self._timeout.cancel()

            # Auto-hide
            self._timeout = utils.Timeout(5000, lambda: setattr(self, "visible", False))

        else:
            if self._timeout:
                self._timeout.cancel()
                self._timeout = None

    def _update_content(self):
        """Update OSD with current player info"""
        players = mpris.players

        if not players:
            # No active player
            self._title_label.label = "No media playing"
            self._artist_label.label = ""
            self._album_art.image = "folder-music-symbolic"
            self._status_icon.image = "media-playback-stop-symbolic"
            return

        player = players[0]

        self._title_label.label = player.title or "Unknown Title"
        self._artist_label.label = player.artist or "Unknown Artist"

        if player.art_url:
            self._album_art.image = player.art_url
        else:
            self._album_art.image = "folder-music-symbolic"

        if player.playback_status == "Playing":
            self._status_icon.image = "media-playback-start-symbolic"
        elif player.playback_status == "Paused":
            self._status_icon.image = "media-playback-pause-symbolic"
        else:
            self._status_icon.image = "media-playback-stop-symbolic"


def init_media_osd():
    """Initialize the media OSD window"""
    global _media_osd_window
    if _media_osd_window is None:
        _media_osd_window = MediaOsdWindow()


def show_media_osd():
    """Show the media OSD"""
    init_media_osd()
    _media_osd_window.visible = True
