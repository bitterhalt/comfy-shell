import asyncio
import os
from datetime import datetime

from ignis import utils
from ignis.services.recorder import RecorderConfig, RecorderService

recorder = RecorderService.get_default()


async def _start_recording_task(source: str, file_path: str, **kwargs):
    rec_config = RecorderConfig(source=source, path=file_path, **kwargs)
    await recorder.start_recording(config=rec_config)


def record_screen():
    """Record entire screen"""
    if not recorder.is_available:
        return

    if recorder.active:
        stop_recording()
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.expanduser(f"~/Videos/Captures/recording_{timestamp}.mp4")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    asyncio.create_task(
        _start_recording_task(
            source="screen",
            file_path=file_path,
            audio_devices=["default_output"],
        )
    )


async def _record_region_async():
    """Record a selected region using RecorderService"""
    if not recorder.is_available:
        return

    if recorder.active:
        stop_recording()
        await asyncio.sleep(0.5)
        return

    result = await utils.exec_sh_async('slurp -f "%wx%h+%x+%y"')
    region = result.stdout.strip()

    if not region:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.expanduser(f"~/Videos/Captures/region_{timestamp}.mp4")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    await _start_recording_task(
        source="region",
        file_path=file_path,
        region=region,
        audio_devices=["default_output"],
    )


def record_region():
    """Record a selected region using slurp"""
    asyncio.create_task(_record_region_async())


def stop_recording():
    """Stop any active recording"""
    if recorder.active:
        recorder.stop_recording()


def is_recording():
    """Check if any recording is active"""
    return recorder.active


def register_recorder_commands():
    """Register recorder commands with CommandManager"""
    from ignis.command_manager import CommandManager

    command_manager = CommandManager.get_default()
    command_manager.add_command("recorder-stop", stop_recording)
    command_manager.add_command("recorder-record-screen", record_screen)
    command_manager.add_command("recorder-record-region", record_region)
