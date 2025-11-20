import asyncio

from ignis import utils
from modules.bar.widgets.audio_base import AudioWidgetBase
from modules.bar.widgets.audio_menu_window import toggle_audio_menu
from modules.osd.volume_osd import show_volume_osd


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


# --- NEW GLOBAL STATE ---
_is_startup_done = False


async def _set_startup_done():
    """Wait briefly (500ms) then enable OSD updates."""
    global _is_startup_done
    await asyncio.sleep(0.5)
    _is_startup_done = True


def _show_volume_osd_safe(percent):
    """
    Wrapper to only show OSD once the initial startup period is over.
    """
    if not _is_startup_done:
        return

    show_volume_osd()


def volume_widget():
    # Start the non-blocking timer as soon as the widget is created
    asyncio.create_task(_set_startup_done())

    return AudioWidgetBase(
        device_getter=lambda audio: audio.speaker,
        pixel_size=22,
        hide_when_muted=False,
        on_real_volume_change=_show_volume_osd_safe,
        on_click=lambda dev: toggle_audio_menu(),  # Open audio menu on click
        on_right_click=lambda dev: exec_async("pavucontrol"),
    ).widget
