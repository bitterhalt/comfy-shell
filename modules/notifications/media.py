import asyncio

from ignis import widgets
from ignis.services.mpris import MprisPlayer, MprisService

mpris = MprisService.get_default()


PLAYER_ICONS = {
    "spotify": "spotify-symbolic",
    "firefox": "firefox-browser-symbolic",
    "chrome": "chrome-symbolic",
    "chromium": "chromium-symbolic",
    "zen": "zen-browser-symbolic",
    None: "folder-music-symbolic",
}


def player_icon(player: MprisPlayer):
    """Return best-matching icon."""
    desktop = (player.desktop_entry or "").lower()

    for key in ["spotify", "firefox", "chrome", "chromium", "zen"]:
        if key in desktop:
            return PLAYER_ICONS[key]

    return PLAYER_ICONS[None]


class MediaPill(widgets.Box):
    """Tiny pill media controller for notification center."""

    def __init__(self, player: MprisPlayer):
        super().__init__(
            spacing=8,
            css_classes=["media-pill"],
            halign="fill",
            valign="center",
        )

        icon = widgets.Icon(
            image=player_icon(player),
            pixel_size=22,
            css_classes=["media-pill-icon"],
        )

        title = widgets.Label(
            label=player.bind("title", lambda t: t or "Unknown"),
            ellipsize="end",
            max_width_chars=22,
            css_classes=["media-pill-title"],
            halign="start",
        )

        play_btn = widgets.Button(
            child=widgets.Icon(
                image=player.bind(
                    "playback_status",
                    lambda s: (
                        "media-playback-pause-symbolic"
                        if s == "Playing"
                        else "media-playback-start-symbolic"
                    ),
                ),
                pixel_size=18,
            ),
            css_classes=["media-pill-button"],
            on_click=lambda *_: asyncio.create_task(player.play_pause_async()),
        )

        self.child = [icon, title, play_btn]


class MediaCenterWidget(widgets.Box):
    """Wrapper showing only the *active* player's pill."""

    def __init__(self):
        super().__init__(
            css_classes=["media-center-wrapper"],
            halign="fill",
            valign="center",
        )

        self._current_player = None

        # Connect to service signals
        mpris.connect("player_added", self._on_player_added)
        mpris.connect("notify::players", lambda *_: self._refresh())

        self._refresh()

    def _on_player_added(self, service, player: MprisPlayer):
        """Handle new player added."""
        # Connect to this player's closed signal
        player.connect("closed", lambda *_: self._on_player_closed(player))
        self._refresh()

    def _on_player_closed(self, closed_player: MprisPlayer):
        """Handle player closed."""
        # If the closed player was our current one, clear and refresh
        if self._current_player == closed_player:
            self._current_player = None
            self._refresh()

    def _refresh(self):
        """Refresh UI based on available players."""
        players = mpris.players

        if not players:
            self.visible = False
            self.child = []
            self._current_player = None
            return

        # Pick the first player
        player = players[0]

        # If already showing the correct pill, do nothing
        if self._current_player == player:
            return

        self._current_player = player
        self.visible = True
        self.child = [MediaPill(player)]
