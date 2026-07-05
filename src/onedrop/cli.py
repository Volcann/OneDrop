from __future__ import annotations

import argparse
import os
import sys
from typing import Literal, cast

from onedrop.auth import Credentials
from onedrop.config import Config
from onedrop.passphrase import is_weak
from onedrop.server import run_server
from onedrop.token_auth import generate_token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onedrop",
        description=(
            "Serve one file over HTTPS, with auth, to a trusted LAN.\n\n"
            "All server defaults (port, bind address, cert paths, etc.) are "
            "read from ONEDROP_* environment variables - set them in your .env file."
        ),
    )
    parser.add_argument(
        "file",
        help="Path to the file to share.",
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
    auth_mode = cast(
        Literal["token", "basic"],
        args.auth_mode.lower() or "token",
    )

    if auth_mode == "basic":
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
            config = Config(
                file_to_share=args.file,
                credentials=Credentials(username=username, password=password),
                auth_mode=auth_mode,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
    else:
        try:
            config = Config(
                file_to_share=args.file,
                auth_mode=auth_mode,
                token=generate_token(),
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    run_server(config)
