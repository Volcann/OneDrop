from __future__ import annotations

import hmac
import secrets


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


class TokenChecker:
    def __init__(self, token: str) -> None:
        if not token or len(token) < 32:
            raise ValueError("Token must be at least 32 characters")
        self._token = token

    def check(self, candidate: str) -> bool:
        if not candidate:
            return False

        return hmac.compare_digest(self._token, candidate)
