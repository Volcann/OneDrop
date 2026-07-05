from __future__ import annotations

import pytest


@pytest.fixture
def tmp_share_file(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"hello onedrop\n" * 100)
    return path
