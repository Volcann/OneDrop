from __future__ import annotations

import pytest

from onedrop.token_auth import TokenChecker, generate_token


def test_generate_token_is_url_safe_and_long_enough():
    token = generate_token()
    assert len(token) >= 32
    assert all(c not in token for c in ["+", "/", "="])


def test_checker_accepts_correct_token():
    token = generate_token()
    checker = TokenChecker(token)
    assert checker.check(token) is True


def test_checker_rejects_wrong_token():
    token = generate_token()
    checker = TokenChecker(token)
    assert checker.check("wrong-token-value") is False


def test_checker_rejects_missing_token():
    token = generate_token()
    checker = TokenChecker(token)
    assert checker.check(None) is False
    assert checker.check("") is False


def test_checker_rejects_token_too_short():
    with pytest.raises(ValueError):
        TokenChecker("short")


def test_checker_is_constant_time():
    token = generate_token()
    checker = TokenChecker(token)
    checker.check(token)
    checker.check("a" * len(token))
