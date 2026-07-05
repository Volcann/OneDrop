from __future__ import annotations

import argparse
import os
import sys

from onedrop.auth import Credentials
from onedrop.config import Config
from onedrop.download_limiter import MAX_ALLOWED_DOWNLOADS
from onedrop.passphrase import is_weak
from onedrop.server import run_server
from onedrop.token_auth import generate_token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onedrop",
        description="Serve one file over HTTPS, with auth, to a trusted LAN.",
    )
    parser.add_argument(
        "file",
        help="Path to the file to share.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=443,
        help="TCP port to listen on (default: 443).",
    )
    parser.add_argument(
        "--bind",
        dest="bind_address",
        default="0.0.0.0",
        help=(
            "Address to bind to. Defaults to 0.0.0.0 (all interfaces) for "
            "backwards compatibility, but printing a warning each time — "
            "pass your LAN/VPN IP explicitly to restrict exposure."
        ),
    )
    parser.add_argument(
        "--cert",
        dest="cert_file",
        default="cert.pem",
        help="Path to the TLS certificate file (default: cert.pem).",
    )
    parser.add_argument(
        "--key",
        dest="key_file",
        default="key.pem",
        help="Path to the TLS private key file (default: key.pem).",
    )
    parser.add_argument(
        "--log-file",
        dest="log_file",
        default="access_audit.log",
        help="Path to the audit log file (default: access_audit.log).",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=1,
        help=(
            "Number of successful downloads to allow before the link "
            f"stops working (default: 1, hard cap: {MAX_ALLOWED_DOWNLOADS})."
        ),
    )
    parser.add_argument(
        "--no-qr",
        dest="show_qr",
        action="store_false",
        help="Don't print a terminal QR code for the share URL.",
    )
    parser.add_argument(
        "--auth-mode",
        choices=["token", "basic"],
        default="token",
        help="Authentication mode to use (default: token).",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help=argparse.SUPPRESS,
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.auth_mode == "basic":
        username = os.environ.get("SHARE_USERNAME")
        password = os.environ.get("SHARE_PASSWORD")

        if not username or not password:
            print(
                "ERROR: SHARE_USERNAME and SHARE_PASSWORD"
                " environment variables"
                " must be set when using --auth-mode basic.\n"
                "       Example:\n"
                '         export SHARE_USERNAME="jsmith"\n'
                '         export SHARE_PASSWORD="$(openssl rand -base64 24)"',
                file=sys.stderr,
            )
            raise SystemExit(1)

        if (reason := is_weak(password)) is not None:
            print(f"ERROR: Weak password: {reason}", file=sys.stderr)
            raise SystemExit(1)

        try:
            credentials = Credentials(username=username, password=password)
            config = Config(
                file_to_share=args.file,
                credentials=credentials,
                auth_mode="basic",
                port=args.port,
                bind_address=args.bind_address,
                cert_file=args.cert_file,
                key_file=args.key_file,
                log_file=args.log_file,
                max_downloads=args.max_downloads,
                show_qr=args.show_qr,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
    else:
        token = generate_token()

        try:
            config = Config(
                file_to_share=args.file,
                auth_mode="token",
                token=token,
                port=args.port,
                bind_address=args.bind_address,
                cert_file=args.cert_file,
                key_file=args.key_file,
                log_file=args.log_file,
                max_downloads=args.max_downloads,
                show_qr=args.show_qr,
            )

        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    run_server(config)
