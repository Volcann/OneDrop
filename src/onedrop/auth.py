from __future__ import annotations

import base64
import hmac
from dataclasses import dataclass

from onedrop.passphrase import is_weak


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str

    def __post_init__(self) -> None:
        if not self.username or not self.password:
            raise ValueError("username and password must both be non-empty")

        if len(self.password) < 12:
            raise ValueError(
                "Password is too short; use at least 12 characters.",
            )

        if len(self.password) > 64:  # Protects against DoS hashing attacks
            raise ValueError("Password must be 64 characters or less.")

        if (reason := is_weak(self.password)) is not None:
            raise ValueError(f"Weak password: {reason}")

    def __repr__(self) -> str:
        return f"Credentials(username={self.username!r}, password='***redacted***')"

    def __str__(self) -> str:
        return self.__repr__()


class BasicAuthChecker:
    def __init__(self, credentials: Credentials) -> None:
        token = base64.b64encode(
            f"{credentials.username}:{credentials.password}".encode()
        ).decode()
        self._expected_header = f"Basic {token}"

    def check(self, authorization_header: str | None) -> bool:
        if not authorization_header:
            return False
        return hmac.compare_digest(authorization_header, self._expected_header)
