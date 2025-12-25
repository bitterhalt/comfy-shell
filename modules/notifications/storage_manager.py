"""
Efficient storage manager with caching to prevent rate limiting
"""

import fcntl
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional


class TaskStorageManager:
    """
    Manages task storage with caching to prevent excessive file I/O.
    Prevents rate limiting by keeping data in memory.
    """

    def __init__(self, storage_file: Path):
        self.storage_file = storage_file
        self._cache: Optional[List[Dict]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 10.0

        # Ensure file exists
        if not self.storage_file.exists():
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            self.storage_file.write_text("[]")

    @contextmanager
    def _locked_file(self, mode: str = "r"):
        """Context manager for file locking"""
        with open(self.storage_file, mode, encoding="utf-8") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                yield f
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def load_tasks(self) -> List[Dict]:
        """Load tasks with caching - uses cache if valid"""
        now = time.time()

        # Return cached data if still valid
        if self._cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cache.copy()

        # Read from disk
        try:
            with self._locked_file("r") as f:
                content = f.read()
                tasks = json.loads(content) if content.strip() else []

                # Update cache
                self._cache = tasks
                self._cache_time = now

                return tasks.copy()
        except:
            return []

    def save_tasks(self, tasks: List[Dict]) -> bool:
        """Save tasks and update cache"""
        try:
            with self._locked_file("w") as f:
                json.dump(tasks, f, indent=2)

            # Update cache
            self._cache = tasks.copy()
            self._cache_time = time.time()

            return True
        except:
            return False

    def batch_update(self, updater_fn) -> bool:
        """
        Perform batch update with single read/write.

        Usage:
            storage.batch_update(lambda tasks: [t for t in tasks if t['fire_at'] > now])
        """
        tasks = self.load_tasks()
        updated_tasks = updater_fn(tasks)
        return self.save_tasks(updated_tasks)
