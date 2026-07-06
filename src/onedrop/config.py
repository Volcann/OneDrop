from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from onedrop.utils import (
    get_env,
    get_default_path,
    get_active_lan_ip
)


@dataclass
class Config:
    file_to_share: Path
    token: str

    port: int = field(
        default_factory=lambda: int(get_env("ONEDROP_PORT", "443"))
    )
    bind_address: str = field(
        default_factory=lambda: get_env("ONEDROP_BIND", get_active_lan_ip())
    )
    cert_file: Path = field(
        default_factory=lambda: get_default_path(
            "ONEDROP_CERT",
            "onedrop.pem",
            "cert.pem"
        )
    )
    key_file: Path = field(
        default_factory=lambda: get_default_path(
            "ONEDROP_KEY",
            "onedrop-key.pem",
            "key.pem"
        )
    )
    log_file: Path = field(
        default_factory=lambda: Path(
            get_env("ONEDROP_LOG", "access_audit.log")
        )
    )
    max_downloads: int = field(
        default_factory=lambda: int(get_env("ONEDROP_MAX_DL", "1"))
    )
    show_qr: bool = True

    def __post_init__(self) -> None:
        self.file_to_share = Path(self.file_to_share)
        self.cert_file = Path(self.cert_file)
        self.key_file = Path(self.key_file)
        self.log_file = Path(self.log_file)

        if not (1 <= self.port <= 65535):
            raise ValueError("Port must be between 1 and 65535")

        if not self.token:
            raise ValueError("Token must be non-empty")

        if not self.file_to_share.exists():
            raise ValueError("File to share must exist")

        if self.max_downloads < 1:
            raise ValueError("max_downloads must be at least 1")

        if not self.file_to_share.is_file():
            raise ValueError("File to share must exist and be a regular file")
