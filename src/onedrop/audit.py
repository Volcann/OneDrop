from __future__ import annotations

import logging
from pathlib import Path


def build_audit_logger(log_file: str | Path) -> logging.Logger:
    logger = logging.getLogger("onedrop.audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.handlers.clear()

    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s\t%(message)s"))
    logger.addHandler(handler)
    return logger


def redact_path(path: str) -> str:
    if path.startswith("/t/"):
        parts = path.split("/", 3)

        if len(parts) >= 3 and parts[2]:
            parts[2] = "***redacted***"
            return "/".join(parts)

    elif path.startswith("t/"):
        parts = path.split("/", 2)

        if len(parts) >= 2 and parts[1]:
            parts[1] = "***redacted***"
            return "/".join(parts)

    return path


def audit(
    logger: logging.Logger, client_ip: str, path: str, status: str, detail: str = ""
) -> None:
    safe_path = redact_path(path)
    message = (
        f"client={client_ip} path={safe_path} status={status} {detail}".rstrip(),
    )

    logger.info(message)
    print(f"[AUDIT] {message}")
