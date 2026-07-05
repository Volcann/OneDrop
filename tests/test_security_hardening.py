from __future__ import annotations

import pytest

from onedrop.passphrase import is_weak
from onedrop.token_auth import TokenChecker, generate_token


def test_token_generation_and_validation():
    token = generate_token()
    assert len(token) >= 43

    checker = TokenChecker(token)
    assert checker.check(token) is True
    assert checker.check("wrong-token-value") is False
    assert checker.check("") is False
    assert checker.check(None) is False

    with pytest.raises(ValueError, match="at least 32 characters"):
        TokenChecker("short-token")


def test_passphrase_sequential_pattern():
    assert is_weak("12345") == "password contains a simple sequential pattern"
    assert is_weak("abcde") == "password contains a simple sequential pattern"
    assert is_weak("54321") == "password contains a simple sequential pattern"
    assert is_weak("edcba") == "password contains a simple sequential pattern"


def test_passphrase_low_variety():
    assert is_weak("aaaaaa") == "password has too little character variety"
    assert is_weak("ababab") == "password has too little character variety"
    assert is_weak("a1b1a1") is None


def test_passphrase_blocklist():
    assert is_weak("password") == "password is in the list of commonly used credentials"
    assert is_weak("admin123") == "password is in the list of commonly used credentials"
    assert is_weak("not-in-blocklist-1234-and-strong") is None
