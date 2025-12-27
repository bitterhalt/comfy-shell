from ignis import widgets
from ignis.services.mpris import MprisPlayer, MprisService
from ignis.window_manager import WindowManager

mpris = MprisService.get_default()
wm = WindowManager.get_default()


PLAYER_ICONS = {
    "spotify": "spotify-symbolic",
    "firefox": "firefox",
    "zen": "zen-browser",
    "chromium": "chromium-browser-symbolic",
    "chrome": "chrome-symbolic",
    "vlc": "vlc-symbolic",
    "mpv": "mpv-symbolic",
    "rhythmbox": "rhythmbox-symbolic",
    None: "folder-music-symbolic",
}


def get_player_icon(player) -> str:
    """Get icon name for player (same logic as OSD)"""
    if not player:
        return PLAYER_ICONS[None]

    entry = player.desktop_entry

    if entry in PLAYER_ICONS:
        return PLAYER_ICONS[entry]

    if player.track_id:
        tid = player.track_id.lower()
        if "chromium" in tid:
            return PLAYER_ICONS["chromium"]
        if "chrome" in tid:
            return PLAYER_ICONS["chrome"]

    return PLAYER_ICONS[None]


class MediaPill(widgets.Box):
    def __init__(self, player: MprisPlayer):
        super().__init__(
            spacing=12,
            css_classes=["media-pill"],
            halign="fill",
            valign="center",
            hexpand=True,
        )

        self._icon = widgets.Icon(
            image=get_player_icon(player),
            pixel_size=28,
            css_classes=["media-pill-icon"],
        )

        player.connect("notify::desktop-entry", lambda *_: self._update_icon(player))
        player.connect("notify::track-id", lambda *_: self._update_icon(player))

        title = widgets.Label(
            label=player.bind("title", lambda t: t or "Unknown"),
            ellipsize="end",
            max_width_chars=30,
            css_classes=["media-pill-title"],
            halign="start",
        )

        artist = widgets.Label(
            label=player.bind("artist", lambda a: a or "Unknown Artist"),
            ellipsize="end",
            max_width_chars=30,
            css_classes=["media-pill-artist"],
            halign="start",
        )

        text_box = widgets.Box(
            vertical=True,
            spacing=2,
            child=[title, artist],
        )

        self.child = [self._icon, text_box]

    def _update_icon(self, player):
        """Update icon when player changes"""
        self._icon.image = get_player_icon(player)


class MediaCenterWidget(widgets.Button):
    """
    Clickable media widget wrapper - Click on text/icon area: Opens Media OSD
    """

    def __init__(self):
        self._current_player = None
        self._pill_content = widgets.Box()

        super().__init__(
            css_classes=["media-center-wrapper", "unset"],
            halign="fill",
            valign="center",
            on_click=lambda x: self._open_media_osd(),
            child=self._pill_content,
        )

        mpris.connect("player_added", self._on_player_added)
        mpris.connect("notify::players", lambda *_: self._refresh())

        self._refresh()

    def _on_player_added(self, service, player: MprisPlayer):
        """Handle new player added."""
        player.connect("closed", lambda *_: self._on_player_closed(player))
        self._refresh()

    def _on_player_closed(self, closed_player: MprisPlayer):
        """Handle player closed."""
        if self._current_player == closed_player:
            self._current_player = None
            self._refresh()

    def _refresh(self):
        """Refresh UI based on available players."""
        players = mpris.players

        if not players:
            self.visible = False
            self._pill_content.child = []
            self._current_player = None
            return

        player = players[0]

        if self._current_player == player:
            return

        self._current_player = player
        self.visible = True
        self._pill_content.child = [MediaPill(player)]

    def _open_media_osd(self):
        """Open media OSD and close integrated center"""
        wm.close_window("ignis_INTEGRATED_CENTER")
        wm.open_window("ignis_MEDIA_OSD")
