import asyncio
import os
from datetime import datetime

from ignis.command_manager import CommandManager
from ignis.services.recorder import RecorderConfig, RecorderService

recorder = RecorderService.get_default()
command_manager = CommandManager.get_default()


async def _start_recording_task(source: str, file_path: str, **kwargs):
    rec_config = RecorderConfig(source=source, path=file_path, **kwargs)
    try:
        await recorder.start_recording(config=rec_config)
    except Exception as e:
        print(f"Recording error: {e}")


def record_screen():
    if not recorder.is_available:
        print("gpu-screen-recorder not found")
        return

    if recorder.active:
        recorder.stop_recording()
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.expanduser(f"~/Videos/Captures/recording_{timestamp}.mp4")

    asyncio.create_task(
        _start_recording_task(
            source="screen",
            file_path=file_path,
            audio_devices=["default_output"],
        )
    )

def stop_recording():
    if recorder.active:
        recorder.stop_recording()


command_manager.add_command("recorder-stop", stop_recording)
command_manager.add_command("recorder-record-screen", record_screen)
