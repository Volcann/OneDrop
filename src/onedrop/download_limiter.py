from __future__ import annotations

import threading

MAX_ALLOWED_DOWNLOADS = 25


class DownloadLimiter:
    def __init__(self, max_downloads: int = 1) -> None:
        if max_downloads < 1:
            raise ValueError("Max downloads must be at least 1")

        if max_downloads > MAX_ALLOWED_DOWNLOADS:
            raise ValueError(
                f"Max downloads cannot exceed {MAX_ALLOWED_DOWNLOADS}; "
                "this tool is for small known groups, not broad distribution"
            )

        self._max = max_downloads
        self._count = 0
        self._lock = threading.Lock()

    @property
    def max_downloads(self) -> int:
        return self._max

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(self._max - self._count, 0)

    def try_consume(self) -> bool:
        with self._lock:
            if self._count >= self._max:
                return False
            self._count += 1
            return True


class PageViewLimiter:
    def __init__(self, max_views: int = 2) -> None:
        if max_views < 1:
            raise ValueError("Max views must be at least 1")

        self._max = max_views
        self._count = 0
        self._lock = threading.Lock()

    @property
    def max_views(self) -> int:
        return self._max

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(self._max - self._count, 0)

    def try_consume(self) -> bool:
        with self._lock:
            if self._count >= self._max:
                return False
            self._count += 1
            return True
