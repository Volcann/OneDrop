from __future__ import annotations

import threading

import pytest

from onedrop.download_limiter import MAX_ALLOWED_DOWNLOADS, DownloadLimiter


def test_default_limit_is_one():
    limiter = DownloadLimiter()
    assert limiter.try_consume() is True
    assert limiter.try_consume() is False


def test_allows_exactly_n_downloads():
    limiter = DownloadLimiter(max_downloads=3)
    results = [limiter.try_consume() for _ in range(5)]
    assert results == [True, True, True, False, False]


def test_remaining_counts_down():
    limiter = DownloadLimiter(max_downloads=2)
    assert limiter.remaining == 2
    limiter.try_consume()
    assert limiter.remaining == 1
    limiter.try_consume()
    assert limiter.remaining == 0


def test_rejects_zero_or_negative_max_downloads():
    with pytest.raises(ValueError):
        DownloadLimiter(max_downloads=0)
    with pytest.raises(ValueError):
        DownloadLimiter(max_downloads=-1)


def test_rejects_max_downloads_above_hard_cap():
    with pytest.raises(ValueError):
        DownloadLimiter(max_downloads=MAX_ALLOWED_DOWNLOADS + 1)


def test_accepts_max_downloads_at_hard_cap():
    limiter = DownloadLimiter(max_downloads=MAX_ALLOWED_DOWNLOADS)
    assert limiter.max_downloads == MAX_ALLOWED_DOWNLOADS


def test_concurrent_consumers_never_exceed_limit():
    limiter = DownloadLimiter(max_downloads=5)
    successes: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        result = limiter.try_consume()
        with lock:
            successes.append(result)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert successes.count(True) == 5
    assert successes.count(False) == 45
