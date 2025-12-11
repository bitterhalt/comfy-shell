import asyncio

from ignis import widgets
from ignis.services.mpris import MprisPlayer, MprisService

mpris = MprisService.get_default()

# ────────────────────────────────────────────────────────────────
# PLAYER ICON + NAME MAPPING
# ────────────────────────────────────────────────────────────────

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

    # Direct match
    if entry in PLAYER_ICONS:
        return PLAYER_ICONS[entry]

    # Detect chrome/chromium via track_id
    if player.track_id:
        tid = player.track_id.lower()
        if "chromium" in tid:
            return PLAYER_ICONS["chromium"]
        if "chrome" in tid:
            return PLAYER_ICONS["chrome"]

    return PLAYER_ICONS[None]


# ────────────────────────────────────────────────────────────────
# MEDIA PILL
# ────────────────────────────────────────────────────────────────


class MediaPill(widgets.Box):
    def __init__(self, player: MprisPlayer):
        super().__init__(
            spacing=12,
            css_classes=["media-pill"],
            halign="fill",
            valign="center",
        )

        # ── ICON ──
        self._icon = widgets.Icon(
            image=get_player_icon(player),
            pixel_size=28,
            css_classes=["media-pill-icon"],
        )

        player.connect("notify::desktop-entry", lambda *_: self._update_icon(player))
        player.connect("notify::track-id", lambda *_: self._update_icon(player))

        # ── TITLE & ARTIST ──
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

        # ── PLAY/PAUSE BUTTON ──
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

        self.child = [self._icon, text_box, play_btn]

    def _update_icon(self, player):
        """Update icon when player changes"""
        self._icon.image = get_player_icon(player)


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
