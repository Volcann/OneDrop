from __future__ import annotations

import base64
import hashlib
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def get_env(key: str, default: str) -> str:
    return os.environ.get(key) or default


def get_default_path(env_key: str, primary: str, fallback: str) -> Path:
    env_val = os.environ.get(env_key)
    if env_val:
        return Path(env_val)

    primary_path = Path(primary)
    return primary_path if primary_path.exists() else Path(fallback)


def format_size(size_bytes: float) -> str:
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1

    return f"{size:.2f} {units[i]}"


def get_active_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def describe_bind_exposure(bind_address: str) -> str:
    if bind_address in ("0.0.0.0", "::"):  # nosec B104
        lan_ip = get_active_lan_ip()
        return (
            f"WARNING: binding to {bind_address} listens on ALL network "
            f"interfaces on this machine, not just your main LAN/VPN adapter.\n"
            f"         Detected active LAN IP: {lan_ip}\n"
            f"         Use --bind <ip> to restrict to a single interface "
            f"if that's not what you want."
        )
    return f"Bound to a single interface: {bind_address}"


def build_base_url(host: str, port: int) -> str:
    return f"https://{host}" if port == 443 else f"https://{host}:{port}"


def get_cert_fingerprint(cert_path: str | Path) -> str:
    try:
        content = Path(cert_path).read_text()
        start = content.find("-----BEGIN CERTIFICATE-----")
        end = content.find("-----END CERTIFICATE-----")
        if start == -1 or end == -1:
            return "Unknown"
        cert_pem = content[start + 27 : end].replace("\n", "").replace("\r", "").strip()
        der_bytes = base64.b64decode(cert_pem)
        fingerprint = hashlib.sha256(der_bytes).hexdigest()
        return ":".join(
            fingerprint[i : i + 2].upper() for i in range(0, len(fingerprint), 2)
        )
    except Exception:
        return "Unknown"


def get_root_ca_path() -> Path | None:
    try:
        result = subprocess.run(
            ["mkcert", "-CAROOT"], capture_output=True, text=True, check=True
        )
        ca_path = Path(result.stdout.strip()) / "rootCA.pem"
        if ca_path.is_file():
            return ca_path
    except Exception:  # noqa: BLE001
        pass

    home = Path.home()
    for path in [
        home / ".local/share/mkcert/rootCA.pem",
        home / "Library/Application Support/mkcert/rootCA.pem",
        home / "AppData/Local/mkcert/rootCA.pem",
    ]:
        if path.is_file():
            return path
    return None


def generate_temp_cert(
    ip_address: str = "127.0.0.1",
) -> tuple[Path, Path, tempfile.TemporaryDirectory]:
    tmp_dir = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp_dir.name)
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"

    cn = ip_address or "127.0.0.1"
    san = f"IP:{cn}" if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", cn) else f"DNS:{cn}"

    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "1",
                "-nodes",
                "-subj",
                f"/CN={cn}",
                "-addext",
                f"subjectAltName={san}",
            ],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        tmp_dir.cleanup()
        fail(
            "TLS certificate/key not found and 'openssl' is not available.\n"
            "Install openssl or supply existing certificate/key files."
        )

    return cert, key, tmp_dir
