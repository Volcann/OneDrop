from __future__ import annotations

import argparse
import sys

from onedrop.config import Config
from onedrop.server import run_server
from onedrop.token_auth import generate_token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onedrop",
        description=(
            "Serve one secret file over HTTPS on a trusted LAN.\n\n"
            "A single-use capability-URL token is generated automatically at "
            "startup — no credentials to configure. All server defaults "
            "(port, bind address, cert paths, etc.) are read from ONEDROP_* "
            "environment variables."
        ),
    )
    parser.add_argument(
        "file",
        help="Path to the file to share (e.g. .env.production, secrets.json).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = Config(
            file_to_share=args.file,
            token=generate_token(),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    run_server(config)
