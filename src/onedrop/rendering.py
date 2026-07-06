from __future__ import annotations

import os
from importlib.resources import files

from onedrop.checksum import sha256_file
from onedrop.config import Config
from onedrop.qr import render_terminal_qr
from onedrop.utils import (
    build_base_url,
    get_active_lan_ip,
    describe_bind_exposure,
    format_size,
    get_cert_fingerprint,
)


def render_landing_page(
    file_name: str,
    file_exists: bool,
    file_size: str,
    checksum: str | None,
    downloads_remaining: int,
    max_downloads: int,
    cert_fingerprint: str = "",
    download_url: str = "",
    ca_instruction_html: str = "",
) -> str:
    if not download_url:
        download_url = f"/{file_name}"

    badge_text = "READY TO SHARE" if file_exists else "FILE NOT FOUND"
    badge_color = "#3fb950" if file_exists else "#f85149"
    badge_bg = "rgba(46, 160, 67, 0.15)" if file_exists else "rgba(248, 81, 73, 0.15)"
    badge_border = "rgba(46, 160, 67, 0.4)" if file_exists else "rgba(248, 81, 73, 0.4)"
    disabled_attr = "disabled" if not file_exists else ""
    checksum_html = (
        f'<div class="checksum">SHA-256: {checksum}</div>' if checksum else ""
    )
    cert_html = (
        f'<div class="checksum" style="margin-top:6px; font-size:10px;">'
        f"Cert SHA-256: {cert_fingerprint}</div>"
        if cert_fingerprint
        else ""
    )
    template = (
        files("onedrop").joinpath("templates/landing.html").read_text(encoding="utf-8")
    )
    return template.format(
        badge_text=badge_text,
        badge_color=badge_color,
        badge_bg=badge_bg,
        badge_border=badge_border,
        disabled_attr=disabled_attr,
        checksum_html=checksum_html,
        cert_html=cert_html,
        file_name=file_name,
        file_size=file_size,
        downloads_remaining=downloads_remaining,
        max_downloads=max_downloads,
        download_url=download_url,
        ca_instruction_html=ca_instruction_html,
    )


def print_startup_banner(config: Config) -> None:
    display_host = (
        get_active_lan_ip()
        if config.bind_address in ("0.0.0.0", "::")
        else config.bind_address
    )
    base = build_base_url(display_host, config.port)
    url = f"{base}/t/{config.token}"

    print("\n" + "=" * 64)
    print("ONEDROP - HTTPS server running")
    print("=" * 64)
    print(f"File:        {config.file_to_share.name}")
    if config.file_to_share.is_file():
        file_size = format_size(config.file_to_share.stat().st_size)
        print(f"Size:        {file_size}")
        print(f"SHA-256:     {sha256_file(config.file_to_share)}")
    else:
        print("Size:        WARNING - file not found")
    print(f"URL:         {url}  (org network / VPN only)")
    print(f"curl:        curl -O {url}/{config.file_to_share.name}")
    print(f"Downloads:   {config.max_downloads} allowed before link expires")
    print(f"Audit log:   {os.path.abspath(config.log_file)}")
    print(f"Cert SHA256: {get_cert_fingerprint(config.cert_file)}")
    print("(Verify this fingerprint in the browser to prevent MITM attacks)")
    print(describe_bind_exposure(config.bind_address))
    print(
        "Reminder:    Self-signed cert will trigger a browser warning unless "
        "your org's CA issued/trusts it."
    )
    print("iOS/Safari bypass: Tap 'Show Details' → 'visit this website' → Confirm.")

    if config.show_qr:
        qr_text = render_terminal_qr(url)
        if qr_text:
            print("\nScan to open on a phone on the same network:\n")
            print(qr_text)
        else:
            print(
                "\n(Install 'qrcode': `pip install secure-lan-share[qr]` "
                "for a scannable QR code here.)"
            )
    print("=" * 64 + "\n")
