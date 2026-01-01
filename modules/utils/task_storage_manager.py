"""
Storage manager for tasks
"""

import fcntl
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, List, Optional


class TaskStorageManager:
    def __init__(self, storage_file: Path):
        self.storage_file = storage_file
        self._cache: Optional[List[Dict]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 30.0
        self._dirty: bool = False

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

    def load_tasks(self, force_refresh: bool = False) -> List[Dict]:
        """
        Load tasks with smart caching
        Args_ force_refresh: If True, bypass cache and read from disk
        """
        now = time.time()

        if not force_refresh and self._cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cache.copy()

        try:
            with self._locked_file("r") as f:
                content = f.read()
                tasks = json.loads(content) if content.strip() else []

                self._cache = tasks
                self._cache_time = now
                self._dirty = False

                return tasks.copy()
        except:
            if self._cache is not None:
                return self._cache.copy()
            return []

    def save_tasks(self, tasks: List[Dict]) -> bool:
        """Save tasks and update cache"""
        try:
            with self._locked_file("w") as f:
                json.dump(tasks, f, indent=2)

            self._cache = tasks.copy()
            self._cache_time = time.time()
            self._dirty = False

            return True
        except:
            return False

    def batch_update(self, updater_fn: Callable[[List[Dict]], List[Dict]]) -> bool:
        tasks = self.load_tasks()
        updated_tasks = updater_fn(tasks)
        return self.save_tasks(updated_tasks)

    def invalidate_cache(self):
        """Force cache refresh on next load"""
        self._cache_time = 0

    def get_pending_count(self, current_time: int) -> int:
        """
        Get count of pending tasks without full load.
        Uses cache if available.
        """
        tasks = self.load_tasks()
        return sum(1 for t in tasks if t.get("fire_at", 0) > current_time)
