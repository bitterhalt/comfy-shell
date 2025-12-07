import asyncio

from ignis import widgets
from ignis.services.mpris import MprisPlayer, MprisService

mpris = MprisService.get_default()


class MediaPill(widgets.Box):
    """Media controller pill for notification center - now with album art."""

    def __init__(self, player: MprisPlayer):
        super().__init__(
            spacing=12,
            css_classes=["media-pill"],
            halign="fill",
            valign="center",
        )

        album_art = widgets.Icon(
            image=player.bind(
                "art_url",
                lambda url: url if url else "folder-music-symbolic",
            ),
            pixel_size=56,
            css_classes=["media-pill-art"],
        )

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
            hexpand=True,
            child=[title, artist],
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

        self.child = [album_art, text_box, play_btn]


class MediaCenterWidget(widgets.Box):
    """Wrapper showing only the *active* player's pill."""

    def __init__(self):
        super().__init__(
            css_classes=["media-center-wrapper"],
            halign="fill",
            valign="center",
        )

        self._current_player = None

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
            self.child = []
            self._current_player = None
            return

        player = players[0]

        if self._current_player == player:
            return

        self._current_player = player
        self.visible = True
        self.child = [MediaPill(player)]
