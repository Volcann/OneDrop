from __future__ import annotations

import base64

import pytest

from onedrop.auth import BasicAuthChecker, Credentials


def _header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def test_credentials_rejects_empty_username():
    with pytest.raises(ValueError):
        Credentials(username="", password="a-long-enough-password")


def test_credentials_rejects_empty_password():
    with pytest.raises(ValueError):
        Credentials(username="jsmith", password="")


def test_credentials_rejects_short_password():
    with pytest.raises(ValueError):
        Credentials(username="jsmith", password="short")


def test_credentials_accepts_valid_input():
    creds = Credentials(username="jsmith", password="a-long-enough-password")
    assert creds.username == "jsmith"


def test_checker_accepts_correct_credentials():
    creds = Credentials(username="jsmith", password="correct-horse-battery")
    checker = BasicAuthChecker(creds)
    assert checker.check(_header("jsmith", "correct-horse-battery")) is True


def test_checker_rejects_wrong_password():
    creds = Credentials(username="jsmith", password="correct-horse-battery")
    checker = BasicAuthChecker(creds)
    assert checker.check(_header("jsmith", "wrong-password-here")) is False


def test_checker_rejects_wrong_username():
    creds = Credentials(username="jsmith", password="correct-horse-battery")
    checker = BasicAuthChecker(creds)
    assert checker.check(_header("nobody", "correct-horse-battery")) is False


def test_checker_rejects_missing_header():
    creds = Credentials(username="jsmith", password="correct-horse-battery")
    checker = BasicAuthChecker(creds)
    assert checker.check(None) is False
    assert checker.check("") is False


def test_checker_rejects_malformed_header():
    creds = Credentials(username="jsmith", password="correct-horse-battery")
    checker = BasicAuthChecker(creds)
    assert checker.check("Bearer not-basic-auth") is False


def test_credentials_redacts_password():
    creds = Credentials(username="jsmith", password="a-long-enough-password")
    assert "a-long-enough-password" not in repr(creds)
    assert "***redacted***" in repr(creds)
    assert str(creds) == repr(creds)


def test_credentials_rejects_weak_password():
    with pytest.raises(ValueError, match="Weak password"):
        Credentials(username="jsmith", password="password12345")
