from __future__ import annotations

import time
from threading import Lock


class ReplayCache:
    def __init__(self) -> None:
        self._entries: dict[str, float] = {}
        self._lock = Lock()

    def _purge(self, now: float) -> None:
        expired = [key for key, expires_at in self._entries.items() if expires_at <= now]
        for key in expired:
            self._entries.pop(key, None)

    def check_and_store(self, token: str, ttl_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            self._purge(now)
            expires_at = self._entries.get(token)
            if expires_at and expires_at > now:
                return True
            self._entries[token] = now + ttl_seconds
            return False

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


replay_cache = ReplayCache()
