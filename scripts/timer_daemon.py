#!/usr/bin/env python3
"""
Timer daemon for Ignis Task Menu.

- Reads timers from ~/.local/share/timers/queue.json
- NO sound playing
- NO notify-send
- Cleans up tasks that are too old (expired)
- Visual notifications handled entirely by Ignis task_popup
"""

import json
import os
import signal
import time
from pathlib import Path

# === Configuration ===
QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()
LOCK_FILE = Path("/tmp/timer_daemon.lock")
EXPIRE_SECONDS = 4 * 60 * 60  # 4 hours
MIN_SLEEP = 5
MAX_SLEEP = 60


# === Small helpers ==========================================================


def load_queue() -> list[dict]:
    """Load timers from the queue."""
    if not QUEUE_FILE.exists():
        return []

    try:
        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_queue(data: list[dict]) -> None:
    """Atomically save queue."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(QUEUE_FILE)


# === Locking ================================================================


def acquire_lock() -> bool:
    """Simple pid-file lock."""
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
        except Exception:
            old_pid = None

        if old_pid:
            try:
                os.kill(old_pid, 0)
                return False  # Still alive → exits here
            except ProcessLookupError:
                pass  # stale lock

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

    def _handle_sigterm(self, *_args):
        self._running = False

    def _handle_sighup(self, *_args):
        pass  # queue reloads next loop

    def process_once(self) -> int:
        now = int(time.time())
        queue = load_queue()

        # drop expired timers first
        fresh = []
        for t in queue:
            fire_at = int(t.get("fire_at", 0) or 0)
            if fire_at and (now - fire_at) > EXPIRE_SECONDS:
                continue
            fresh.append(t)

        queue = fresh

        if not queue:
            save_queue(queue)
            return MAX_SLEEP

        fire_times = [
            int(t.get("fire_at") or 0) for t in queue if int(t.get("fire_at") or 0) > 0
        ]

        if not fire_times:
            save_queue(queue)
            return MAX_SLEEP

        next_fire = min(fire_times)

        save_queue(queue)

        # Next sleep time:
        delta = max(next_fire - now, MIN_SLEEP)
        delta = min(delta, MAX_SLEEP)
        return delta

    def run(self):
        if not acquire_lock():
            print("[TimerDaemon] Already running, exiting.")
            return

        print("[TimerDaemon] Started.")

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


if __name__ == "__main__":
    TimerDaemon().run()
