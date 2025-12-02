#!/usr/bin/env python3

import json
import os
import signal
import sys
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
    except (json.JSONDecodeError, OSError) as e:
        print(f"[TimerDaemon] Error loading queue: {e}", file=sys.stderr)
        return []


def save_queue(data: list[dict]) -> None:
    """Atomically save queue."""
    try:
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = QUEUE_FILE.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(QUEUE_FILE)
    except OSError as e:
        print(f"[TimerDaemon] Error saving queue: {e}", file=sys.stderr)


# === Locking ================================================================


def acquire_lock() -> bool:
    """Simple pid-file lock."""
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
        except (ValueError, OSError):
            old_pid = None

        if old_pid:
            try:
                os.kill(old_pid, 0)
                return False  # Still alive
            except ProcessLookupError:
                pass  # stale lock
            except OSError:
                pass  # Permission denied or other error

    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except OSError as e:
        print(f"[TimerDaemon] Error creating lock: {e}", file=sys.stderr)
        return False


def release_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# === Daemon core ============================================================


class TimerDaemon:
    def __init__(self) -> None:
        self._running = True

    def _handle_sigterm(self, *_args):
        print("[TimerDaemon] Received SIGTERM, shutting down...")
        self._running = False

    def _handle_sighup(self, *_args):
        print("[TimerDaemon] Received SIGHUP, reloading on next cycle...")

    def process_once(self) -> int:
        """Process tasks once and return sleep duration."""
        now = int(time.time())
        queue = load_queue()

        # Drop expired timers first
        fresh = []
        expired_count = 0
        for t in queue:
            fire_at = int(t.get("fire_at", 0) or 0)
            if fire_at and (now - fire_at) > EXPIRE_SECONDS:
                expired_count += 1
                continue
            fresh.append(t)

        if expired_count > 0:
            print(f"[TimerDaemon] Cleaned {expired_count} expired task(s)")

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
        time_until = next_fire - now

        # Log upcoming task (only if close)
        if 0 < time_until <= 60:
            next_task = next(t for t in queue if t.get("fire_at") == next_fire)
            msg = next_task.get("message", "Unknown")
            print(f"[TimerDaemon] Task due in {time_until}s: {msg}")

        save_queue(queue)

        # Calculate next sleep
        delta = max(time_until, MIN_SLEEP)
        delta = min(delta, MAX_SLEEP)
        return delta

    def run(self):
        if not acquire_lock():
            print("[TimerDaemon] Already running, exiting.", file=sys.stderr)
            sys.exit(1)

        print("[TimerDaemon] Started (PID: {})".format(os.getpid()))

        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_sighup)

        try:
            sleep_for = MIN_SLEEP
            while self._running:
                sleep_for = self.process_once()
                time.sleep(sleep_for)
        except Exception as e:
            print(f"[TimerDaemon] Fatal error: {e}", file=sys.stderr)
            raise
        finally:
            release_lock()
            print("[TimerDaemon] Stopped.")


if __name__ == "__main__":
    TimerDaemon().run()
