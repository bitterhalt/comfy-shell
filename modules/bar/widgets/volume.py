import asyncio

from ignis import utils, widgets
from ignis.services.audio import AudioService
from modules.osd.volume_osd import show_volume_osd

audio = AudioService.get_default()

# Prevent OSD from showing on first notify event
FIRST_VOLUME_EVENT_SEEN = False


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


def volume_icon():
    speaker = audio.speaker

    icon = widgets.Icon(
        image=speaker.icon_name,
        pixel_size=22,
    )

    raw = speaker.volume or 0
    percent = int(max(0, min(raw, 100)))
    icon.set_tooltip_text(f"{speaker.description}\nvol: {percent}%")

    def update(reason):
        global FIRST_VOLUME_EVENT_SEEN  # <-- FIX: global instead of nonlocal

        raw = speaker.volume or 0
        percent = int(max(0, min(raw, 100)))

        # --------------------------------------------------------------------
        #  IGNORE FIRST VOLUME NOTIFICATION (Startup sync event)
        # --------------------------------------------------------------------
        if not FIRST_VOLUME_EVENT_SEEN:
            if reason == "volume":
                FIRST_VOLUME_EVENT_SEEN = True

            # Always update icon + tooltip
            icon.set_property("image", speaker.icon_name)
            icon.set_tooltip_text(f"{speaker.description}\nvol: {percent}%")
            return

        # Do not show OSD on mute toggles
        if reason == "mute":
            icon.set_property("image", speaker.icon_name)
            icon.set_tooltip_text(f"{speaker.description}\nvol: {percent}%")
            return

        # Real volume change → show OSD
        if reason == "volume":
            show_volume_osd()

        # Update icon + tooltip
        icon.set_property("image", speaker.icon_name)
        icon.set_tooltip_text(f"{speaker.description}\nvol: {percent}%")

    # Connect signals with labeled reasons
    speaker.connect("notify::volume", lambda *_: update("volume"))
    speaker.connect("notify::is-muted", lambda *_: update("mute"))
    speaker.connect("notify::icon-name", lambda *_: update("icon"))
    speaker.connect("notify::description", lambda *_: update("desc"))

    return widgets.Button(
        css_classes=["speaker-volume"],
        on_click=lambda *_: speaker.set_property("is-muted", not speaker.is_muted),
        on_right_click=lambda *_: exec_async("pavucontrol"),
        child=widgets.Box(child=[icon]),
    )
