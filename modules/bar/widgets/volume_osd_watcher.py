import asyncio

from ignis.services.audio import AudioService
from modules.osd.volume_osd import show_volume_osd

audio = AudioService.get_default()

# --- STARTUP DELAY GUARD ---
_is_startup_done = False
_startup_task = None


async def _startup_delay():
    """Prevent OSD spam during initial volume-sync events."""
    global _is_startup_done
    await asyncio.sleep(0.5)
    _is_startup_done = True


def _show_osd_safe(*_):
    """Only show OSD if startup is finished."""
    if not _is_startup_done:
        return
    show_volume_osd()


def init_volume_osd_watcher():
    """
    Sets up the signal handlers so the OSD works again.
    Should be called once on startup (config.py or bar init).
    """
    global _startup_task

    if _startup_task is None:
        _startup_task = asyncio.create_task(_startup_delay())

    # react to real volume changes
    audio.speaker.connect("notify::volume", _show_osd_safe)
    audio.speaker.connect("notify::is-muted", _show_osd_safe)
