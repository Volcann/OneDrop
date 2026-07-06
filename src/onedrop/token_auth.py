from __future__ import annotations

import hmac
import secrets


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


class TokenChecker:
    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("Token must not be empty")
        self._token = token

    def check(self, candidate: str) -> bool:
        if not candidate:
            return False

        return hmac.compare_digest(self._token, candidate)
