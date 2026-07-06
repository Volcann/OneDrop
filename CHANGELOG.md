# Changelog

All notable changes to OneDrop are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Nothing yet.

### Fixed

- Nothing yet.

---

## [0.2.0] - 2025-07-01

### Added

- **mkcert Root CA distribution.** If `mkcert` is installed, OneDrop now detects the Root CA path and serves it as a downloadable link on the landing page. Mobile devices (iOS, iPadOS, Android) can install it to trust the server certificate without warnings.
- **CA download endpoint.** New route `/t/{token}/rootCA.pem` serves the mkcert Root CA certificate with `Content-Type: application/x-x509-ca-cert`. The endpoint is authenticated by the same capability token as the main download.
- **"Trust this server on iPad/Android" section on landing page.** Step-by-step OS-specific instructions are rendered inline for iOS and Android CA installation.
- **TLS certificate fingerprint on landing page.** The SHA-256 fingerprint of the server's certificate is now shown below the file checksum on the landing page, so recipients can verify TOFU without switching to a terminal.
- **Temporary self-signed cert auto-generation.** If no certificate files are found at startup, OneDrop generates a temporary self-signed certificate via `openssl req -x509` and cleans it up on exit. No manual cert setup required for first-time use.
- **Programmatic API** (`onedrop.setup()` and `onedrop.share()`). OneDrop can now be embedded in Python scripts and CI pipelines without going through the CLI.
- **`PageViewLimiter` class** in `download_limiter.py`. Infrastructure for a future feature that limits how many times the landing page can be loaded before the link expires.

### Changed

- Server `Server` response header now reports `OneDrop/0.2` instead of Python's default.
- `build_base_url()` in `utils.py` now omits the port suffix when running on port 443, producing cleaner URLs.
- Default bind address changed from `0.0.0.0` to the auto-detected primary LAN IP. The `describe_bind_exposure()` warning is still shown when binding to `0.0.0.0` or `::` explicitly.
- `print_startup_banner()` moved from `server.py` into `rendering.py` alongside landing page rendering.
- Cert and key file resolution now checks `onedrop.pem` / `onedrop-key.pem` first, then falls back to `cert.pem` / `key.pem`.

### Fixed

- Shutdown daemon thread is now started _after_ `_stream_file()` returns, ensuring the HTTP response is fully written to the client before `serve_forever()` exits.
- `TokenChecker.check()` now explicitly returns `False` for empty-string candidates before calling `hmac.compare_digest`, preventing a potential short-circuit on zero-length input.
- `DownloadLimiter` now raises `ValueError` on construction if `max_downloads` exceeds `MAX_ALLOWED_DOWNLOADS` (25), rather than silently clamping.

---

## [0.1.0] - 2025-05-15

Initial release.

### Added

- Core HTTPS file server using Python `http.server` + `ssl`.
- Capability-URL token authentication. A 32-byte `secrets.token_urlsafe` token is generated at startup and embedded in the URL. Validated with `hmac.compare_digest` (constant-time).
- `DownloadLimiter` - thread-safe, mutex-backed download counter. Hard cap at 25. Default: 1.
- Automatic server shutdown when download limit is reached (daemon thread).
- HTTP 410 Gone response when limit is exhausted.
- SHA-256 file checksum computed in 1 MiB chunks at startup and displayed on the landing page.
- HTML landing page served at `/t/{token}/` - shows filename, size, checksum, downloads remaining, and a Download button.
- Structured audit log (`access_audit.log`) - every request logged with timestamp, client IP, sanitised path, and outcome. Capability token is always redacted from log entries.
- Startup terminal banner - URL, `curl` one-liner, SHA-256, cert fingerprint, download limit, bind-address exposure warning.
- Optional terminal QR code via the `qrcode` package (`pip install secure-lan-share[qr]`).
- `Config` dataclass with full validation in `__post_init__`. All defaults configurable via `ONEDROP_*` environment variables.
- Path-traversal protection - only three URL structures accepted; everything else returns 404 without touching the filesystem.
- `get_active_lan_ip()` - UDP connect trick to detect the primary outbound LAN interface without requiring root or reading routing tables.
- `describe_bind_exposure()` - warns loudly at startup when binding to `0.0.0.0` or `::`.
- Makefile targets: `dev`, `check`, `test`, `lint`, `format`, `cert`, `clean`.
- End-to-end integration test suite - starts a real TLS server in a background thread, drives it with genuine HTTPS requests, covers path traversal and download-limit exhaustion.
