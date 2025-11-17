import asyncio

from ignis import utils
from modules.bar.widgets.audio_base import AudioWidgetBase
from modules.osd.volume_osd import show_volume_osd


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


def volume_widget():
    return AudioWidgetBase(
        device_getter=lambda audio: audio.speaker,
        pixel_size=22,
        hide_when_muted=False,  # volume widget always visible
        on_real_volume_change=lambda percent: show_volume_osd(),
        on_click=lambda dev: setattr(dev, "is_muted", not dev.is_muted),
        on_right_click=lambda dev: asyncio.create_task(
            utils.exec_sh_async("pavucontrol")
        ),
    ).widget
