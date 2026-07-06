from __future__ import annotations

import pytest

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
