import asyncio
import os
import signal
from datetime import datetime

from ignis import utils
from ignis.command_manager import CommandManager
from ignis.services.recorder import RecorderConfig, RecorderService

recorder = RecorderService.get_default()
command_manager = CommandManager.get_default()

# Track region recording process
_region_recording_process = None
_region_recording_file = None


async def _start_recording_task(source: str, file_path: str, **kwargs):
    rec_config = RecorderConfig(source=source, path=file_path, **kwargs)
    try:
        await recorder.start_recording(config=rec_config)
    except Exception as e:
        print(f"Recording error: {e}")


def record_screen():
    """Record entire screen"""
    if not recorder.is_available:
        print("gpu-screen-recorder not found")
        return

    if recorder.active or _region_recording_process is not None:
        stop_recording()
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


async def _record_region_async():
    """Helper function to record a selected region"""
    global _region_recording_process, _region_recording_file

    # Check if gpu-screen-recorder is available
    gsr_check = await utils.exec_sh_async("which gpu-screen-recorder")
    if gsr_check.returncode != 0:
        print("gpu-screen-recorder not found")
        return

    # Stop any existing recording
    if recorder.active or _region_recording_process is not None:
        stop_recording()
        await asyncio.sleep(0.5)  # Wait for cleanup
        return

    try:
        # Use slurp to select region
        result = await utils.exec_sh_async('slurp -f "%wx%h+%x+%y"')
        region = result.stdout.strip()

        if not region:
            print("Region selection cancelled")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.expanduser(f"~/Videos/Captures/region_{timestamp}.mp4")

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Build the command directly
        cmd = [
            "gpu-screen-recorder",
            "-w",
            "region",
            "-region",
            region,
            "-f",
            "60",
            "-a",
            "default_output",
            "-o",
            file_path,
        ]

        print(f"Starting region recording: {region}")
        print(f"Output: {file_path}")

        # Start the process
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        _region_recording_process = process
        _region_recording_file = file_path

        # Emit recording started signal to update UI
        recorder.emit("recording_started")

        # Wait for process to complete in background
        asyncio.create_task(_monitor_region_recording(process))

    except Exception as e:
        print(f"Region recording error: {e}")
        _region_recording_process = None
        _region_recording_file = None


async def _monitor_region_recording(process):
    """Monitor the region recording process"""
    global _region_recording_process, _region_recording_file

    try:
        await process.wait()
        print(f"Region recording stopped. Saved to: {_region_recording_file}")
    except Exception as e:
        print(f"Region recording monitoring error: {e}")
    finally:
        _region_recording_process = None
        _region_recording_file = None
        # Emit recording stopped signal to update UI
        recorder.emit("recording_stopped")


def record_region():
    """Record a selected region using slurp"""
    asyncio.create_task(_record_region_async())


def stop_recording():
    """Stop any active recording"""
    global _region_recording_process, _region_recording_file

    # Stop RecorderService recording
    if recorder.active:
        recorder.stop_recording()

    # Stop region recording if active
    if _region_recording_process is not None:
        try:
            print(f"Stopping region recording. Saved to: {_region_recording_file}")
            _region_recording_process.send_signal(signal.SIGINT)
            _region_recording_process = None
            _region_recording_file = None
            # Emit stopped signal
            recorder.emit("recording_stopped")
        except Exception as e:
            print(f"Error stopping region recording: {e}")


def is_recording():
    """Check if any recording is active"""
    return recorder.active or _region_recording_process is not None


# Register commands
command_manager.add_command("recorder-stop", stop_recording)
command_manager.add_command("recorder-record-screen", record_screen)
command_manager.add_command("recorder-record-region", record_region)
