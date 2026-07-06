from __future__ import annotations

from onedrop.server import render_landing_page


def test_shows_ready_badge_and_checksum_when_file_exists():
    html = render_landing_page(
        file_name="payload.bin",
        file_exists=True,
        file_size="1.95 KB",
        checksum="abc123",
        downloads_remaining=1,
        max_downloads=1,
    )
    assert "READY TO SHARE" in html
    assert "payload.bin" in html
    assert "SHA-256: abc123" in html
    assert 'button class="download-btn" disabled' not in html


def test_shows_missing_badge_and_disables_button_when_file_absent():
    html = render_landing_page(
        file_name="payload.bin",
        file_exists=False,
        file_size="Unknown",
        checksum=None,
        downloads_remaining=1,
        max_downloads=1,
    )
    assert "FILE NOT FOUND" in html
    assert 'button class="download-btn" disabled' in html
    assert "SHA-256" not in html


def test_shows_remaining_download_count():
    html = render_landing_page(
        file_name="payload.bin",
        file_exists=True,
        file_size="1.95 KB",
        checksum="abc123",
        downloads_remaining=2,
        max_downloads=5,
    )
    assert "Downloads remaining: 2 of 5" in html


def test_shows_cert_fingerprint():
    html = render_landing_page(
        file_name="payload.bin",
        file_exists=True,
        file_size="1.95 KB",
        checksum="abc123",
        downloads_remaining=1,
        max_downloads=1,
        cert_fingerprint="AA:BB:CC:DD",
    )
    assert "Cert SHA-256: AA:BB:CC:DD" in html


def test_shows_ca_instructions():
    html = render_landing_page(
        file_name="payload.bin",
        file_exists=True,
        file_size="1.95 KB",
        checksum="abc123",
        downloads_remaining=1,
        max_downloads=1,
        ca_instruction_html="<div class='test-ca'>Download Root CA</div>",
    )
    assert "<div class='test-ca'>Download Root CA</div>" in html
