from ignis import utils, widgets
from ignis.services.mpris import MprisService

mpris = MprisService.get_default()
_media_osd_window = None

# --------------------------------------------------------------------
# PLAYER ICON + NAME MAPPING (merged from your preferred snippet)
# --------------------------------------------------------------------

PLAYER_ICONS = {
    "spotify": "spotify-symbolic",
    "firefox": "firefox-browser-symbolic",
    "zen": "zen-browser",
    "chromium": "chromium-browser-symbolic",
    "chrome": "chrome-symbolic",
    "vlc": "vlc-symbolic",
    "mpv": "mpv-symbolic",
    "rhythmbox": "rhythmbox-symbolic",
    None: "folder-music-symbolic",
}

PLAYER_NAMES = {
    "spotify": "Spotify",
    "firefox": "Firefox",
    "zen": "zen-browser",
    "chromium": "Chromium",
    "chrome": "Google Chrome",
    "vlc": "VLC",
    "mpv": "MPV",
    "rhythmbox": "Rhythmbox",
    None: "Media Player",
}


def get_player_icon(player) -> str:
    if not player:
        return PLAYER_ICONS[None]

    entry = player.desktop_entry

    # direct match
    if entry in PLAYER_ICONS:
        return PLAYER_ICONS[entry]

    # detect chrome/chromium via track_id
    if player.track_id:
        tid = player.track_id.lower()
        if "chromium" in tid:
            return PLAYER_ICONS["chromium"]
        if "chrome" in tid:
            return PLAYER_ICONS["chrome"]

    return PLAYER_ICONS[None]


def get_player_name(player) -> str:
    if not player:
        return PLAYER_NAMES[None]

    entry = player.desktop_entry

    if entry in PLAYER_NAMES:
        return PLAYER_NAMES[entry]

    if player.track_id:
        tid = player.track_id.lower()
        if "chromium" in tid:
            return PLAYER_NAMES["chromium"]
        if "chrome" in tid:
            return PLAYER_NAMES["chrome"]

    if entry:
        return entry.replace("-", " ").title()

    return PLAYER_NAMES[None]


# --------------------------------------------------------------------
# GNOME-STYLE MEDIA OSD (same layout you liked)
# --------------------------------------------------------------------


class MediaOsdWindow(widgets.Window):
    def __init__(self):
        self._timeout = None

        # App icon + name (header)
        self._app_icon = widgets.Icon(
            image=PLAYER_ICONS[None],
            pixel_size=20,
            css_classes=["media-osd-app-icon"],
        )

        self._app_name = widgets.Label(
            label="Media Player",
            css_classes=["media-osd-app-name"],
            ellipsize="end",
            max_width_chars=30,
        )

        header = widgets.Box(
            spacing=8,
            css_classes=["media-osd-header"],
            child=[self._app_icon, self._app_name],
        )

        # Album art
        self._album_art = widgets.Icon(
            image="folder-music-symbolic",
            pixel_size=64,
            css_classes=["media-osd-art"],
        )

        # Title & artist
        self._title_label = widgets.Label(
            label="No Title",
            css_classes=["media-osd-title"],
            ellipsize="end",
            max_width_chars=35,
        )

        self._artist_label = widgets.Label(
            label="No Artist",
            css_classes=["media-osd-artist"],
            ellipsize="end",
            max_width_chars=35,
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=2,
            hexpand=True,
            child=[self._title_label, self._artist_label],
        )

        # Playback status icon (play/pause)
        self._status_icon = widgets.Icon(
            image="media-playback-start-symbolic",
            pixel_size=22,
            css_classes=["media-osd-status-icon"],
        )

        main_row = widgets.Box(
            spacing=16,
            child=[self._album_art, text_box, self._status_icon],
        )

        pill = widgets.Box(
            vertical=True,
            spacing=10,
            css_classes=["media-osd"],
            child=[header, main_row],
        )

        center_align = widgets.Box(
            halign="center",
            valign="start",
            child=[pill],
        )

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

    # ----------------------------------------------------------------

    def _on_visible_changed(self, *_):
        if self.visible:
            self._update_content()

            if self._timeout:
                self._timeout.cancel()

            self._timeout = utils.Timeout(5000, lambda: setattr(self, "visible", False))
        else:
            if self._timeout:
                self._timeout.cancel()
                self._timeout = None

    # ----------------------------------------------------------------

    def _update_content(self):
        players = mpris.players

        if not players:
            self._app_icon.image = PLAYER_ICONS[None]
            self._app_name.label = "No Media"
            self._title_label.label = "No media playing"
            self._artist_label.label = ""
            self._album_art.image = "folder-music-symbolic"
            self._status_icon.image = "media-playback-stop-symbolic"
            return

        player = players[0]

        # App icon + name
        self._app_icon.image = get_player_icon(player)
        self._app_name.label = get_player_name(player)

        # Song info
        self._title_label.label = player.title or "Unknown Title"
        self._artist_label.label = player.artist or "Unknown Artist"

        # Album art
        if player.art_url:
            self._album_art.image = player.art_url
        else:
            self._album_art.image = "folder-music-symbolic"

        # Play/pause
        if player.playback_status == "Playing":
            self._status_icon.image = "media-playback-start-symbolic"
        elif player.playback_status == "Paused":
            self._status_icon.image = "media-playback-pause-symbolic"
        else:
            self._status_icon.image = "media-playback-stop-symbolic"
