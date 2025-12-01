#!/usr/bin/env python3
"""
Timer daemon for Ignis Task Menu.

- Reads timers from ~/.local/share/timers/queue.json
- Plays a sound when a task fires
- Cleans up tasks that are too old (expired)
- NO libnotify / notify-send usage anymore.
  Visual notifications are handled entirely by Ignis
  via modules.notifications.task_popup.
"""

import json
import os
import signal
import time
from pathlib import Path
from subprocess import DEVNULL, Popen

# === Configuration ===
QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()
LOCK_FILE = Path("/tmp/timer_daemon.lock")
EXPIRE_SECONDS = 4 * 60 * 60  # 4 hours
MIN_SLEEP = 5  # minimum sleep between checks
MAX_SLEEP = 60  # maximum sleep between checks
SOUND_FILE = Path("~/.local/share/Sounds/complete.oga").expanduser()


# === Small helpers ==========================================================


def load_queue() -> list[dict]:
    """Load timers from JSON queue; returns [] on error."""
    if not QUEUE_FILE.exists():
        return []

    try:
        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def save_queue(data: list[dict]) -> None:
    """Atomically save timers back to the queue file."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(QUEUE_FILE)


def play_sound() -> None:
    """Play completion sound (non-blocking); ignore failures."""
    if not SOUND_FILE.exists():
        return
    try:
        Popen(
            ["pw-play", str(SOUND_FILE)],
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
    except Exception:
        # Don't crash the daemon if sound fails
        pass


# === Locking ================================================================


def acquire_lock() -> bool:
    """Simple pid-file lock; returns True if we became the owner."""
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
        except Exception:
            old_pid = None

        if old_pid:
            # If the process is still alive, refuse to start
            try:
                os.kill(old_pid, 0)
                # No error -> still running
                return False
            except ProcessLookupError:
                # stale lock file
                pass

    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


# === Daemon core ============================================================


class TimerDaemon:
    def __init__(self) -> None:
        self._running = True

    # Signal handlers ---------------------------------------------------------
    def _handle_sigterm(self, *_args) -> None:
        self._running = False

    def _handle_sighup(self, *_args) -> None:
        # Just reload queue naturally on next loop
        pass

    # Main processing ---------------------------------------------------------
    def process_once(self) -> int:
        """
        Process timers once.

        Returns: suggested sleep time (in seconds) before next check.
        """
        now = int(time.time())
        queue = load_queue()

        # Drop very old tasks that were never handled
        fresh: list[dict] = []
        for t in queue:
            fire_at = int(t.get("fire_at", 0) or 0)
            if fire_at and (now - fire_at) > EXPIRE_SECONDS:
                # too old -> silently drop
                continue
            fresh.append(t)
        queue = fresh

        if not queue:
            save_queue(queue)
            return MAX_SLEEP

        # Find earliest fire_at
        fire_times = [int(t.get("fire_at", 0) or 0) for t in queue if t.get("fire_at")]
        fire_times = [ft for ft in fire_times if ft > 0]

        if not fire_times:
            save_queue(queue)
            return MAX_SLEEP

        next_fire = min(fire_times)

        # Are there any timers due *now* (but not too old)?
        due_timers = [
            t
            for t in queue
            if 0 < int(t.get("fire_at", 0) or 0) <= now
            and (now - int(t.get("fire_at", 0) or 0)) <= EXPIRE_SECONDS
        ]

        if due_timers:
            # At least one timer just fired: play the sound once.
            # Visual popup is handled in modules.notifications.task_popup.
            play_sound()

        # Save cleaned queue (we do *not* remove due entries here;
        # Ignis UI (task_popup + integrated_center) takes care of user actions)
        save_queue(queue)

        # Sleep until next timer, clamped to [MIN_SLEEP, MAX_SLEEP]
        delta = max(next_fire - now, MIN_SLEEP)
        delta = min(delta, MAX_SLEEP)
        return delta

    # Run loop ----------------------------------------------------------------
    def run(self) -> None:
        if not acquire_lock():
            print("[TimerDaemon] Another instance is already running, exiting.")
            return

        print("[TimerDaemon] Started.")

        # Install simple signal handlers
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_sighup)

        try:
            sleep_for = MIN_SLEEP
            while self._running:
                sleep_for = self.process_once()
                time.sleep(sleep_for)
        finally:
            release_lock()
            print("[TimerDaemon] Stopped.")


# === Entry ==================================================================

if __name__ == "__main__":
    TimerDaemon().run()
