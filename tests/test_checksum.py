from __future__ import annotations

import hashlib

from onedrop.checksum import sha256_file


def test_sha256_file_matches_hashlib_reference(tmp_share_file):
    expected = hashlib.sha256(tmp_share_file.read_bytes()).hexdigest()
    assert sha256_file(tmp_share_file) == expected


def test_sha256_file_is_stable_across_calls(tmp_share_file):
    assert sha256_file(tmp_share_file) == sha256_file(tmp_share_file)


def test_sha256_file_differs_for_different_content(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"content a")
    b.write_bytes(b"content b")
    assert sha256_file(a) != sha256_file(b)


def test_sha256_file_handles_empty_file(tmp_path):
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert sha256_file(empty) == hashlib.sha256(b"").hexdigest()
