from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from onedrop.auth import Credentials


def _env(key: str, default: str) -> str:
    return os.environ.get(key) or default


@dataclass
class Config:
    file_to_share: Path
    credentials: Credentials | None = None
    auth_mode: Literal["token", "basic"] = "token"
    token: str | None = None

    port: int = field(
        default_factory=lambda: int(_env("ONEDROP_PORT", "443"))
    )
    bind_address: str = field(
        default_factory=lambda: _env("ONEDROP_BIND", "0.0.0.0")
    )
    cert_file: Path = field(
        default_factory=lambda: Path(_env("ONEDROP_CERT", "cert.pem"))
    )
    key_file: Path = field(
        default_factory=lambda: Path(_env("ONEDROP_KEY", "key.pem"))
    )
    log_file: Path = field(
        default_factory=lambda: Path(
            _env("ONEDROP_LOG", "access_audit.log")
        )
    )
    max_downloads: int = field(
        default_factory=lambda: int(_env("ONEDROP_MAX_DL", "1"))
    )
    show_qr: bool = True

    def __post_init__(self) -> None:
        self.file_to_share = Path(self.file_to_share)
        self.cert_file = Path(self.cert_file)
        self.key_file = Path(self.key_file)
        self.log_file = Path(self.log_file)

        if not (1 <= self.port <= 65535):
            raise ValueError("Port must be between 1 and 65535")

        if self.auth_mode == "basic" and self.credentials is None:
            raise ValueError(
                "Credentials must be set when auth_mode is basic"
            )

        if self.auth_mode == "token" and not self.token:
            raise ValueError(
                "Token must be set when auth_mode is token"
            )
