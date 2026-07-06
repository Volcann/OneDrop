import os
import socket
from pathlib import Path


def get_env(key: str, default: str) -> str:
    return os.environ.get(key) or default


def get_default_path(
    env_key: str,
    primary: str,
    fallback: str
) -> Path:
    env_val = os.environ.get(env_key)
    if env_val:
        return Path(env_val)

    primary_path = Path(primary)
    return primary_path if primary_path.exists() else Path(fallback)


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
