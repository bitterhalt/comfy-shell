#!/usr/bin/env python3

import asyncio
import json
import signal
import time
from pathlib import Path
from subprocess import DEVNULL, Popen

QUEUE_FILE = Path("~/.local/share/timers/queue.json").expanduser()
EXPIRE_SECONDS = 4 * 60 * 60  # auto-remove timers older than 4 hours

running = True


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def load_queue():
    if not QUEUE_FILE.exists():
        return []
    try:
        return json.loads(QUEUE_FILE.read_text())
    except Exception:
        return []


def save_queue(items):
    tmp = QUEUE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2))
    tmp.replace(QUEUE_FILE)


def notify(title, body):
    """Send a desktop notification."""
    Popen(
        ["notify-send", "-u", "normal", "-t", "10000", title, body],
        stdout=DEVNULL,
        stderr=DEVNULL,
    )


# ---------------------------------------------------------------------
# Async daemon loop
# ---------------------------------------------------------------------
async def timer_loop():
    global running

    while running:
        now = int(time.time())
        timers = load_queue()

        # Remove old expired timers
        cleaned = []
        for t in timers:
            if now - t["fire_at"] < EXPIRE_SECONDS:
                cleaned.append(t)

        if cleaned != timers:
            save_queue(cleaned)
            timers = cleaned

        # If no timers, sleep longer
        if not timers:
            try:
                await asyncio.wait_for(asyncio.sleep(60), timeout=60)
            except asyncio.TimeoutError:
                pass
            continue

        # Sort upcoming timers
        timers.sort(key=lambda x: x["fire_at"])
        nxt = timers[0]
        dt = nxt["fire_at"] - now

        if dt > 0:
            try:
                await asyncio.wait_for(asyncio.sleep(dt), timeout=dt)
                continue
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                return

        # -----------------------------------------------------------------
        # Timer fired
        # -----------------------------------------------------------------
        msg = nxt.get("message", "Timer done")
        notify("⏰ Timer Done", msg)

        # Remove fired timer
        timers.pop(0)
        save_queue(timers)


# ---------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------
async def main():
    global running

    def stop(*_):
        global running
        running = False

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, stop)
    loop.add_signal_handler(signal.SIGINT, stop)

    await timer_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
