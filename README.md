<p align="center">
  <img src="assets/logo.gif" alt="OneDrop" width="250" height="250">
</p>

<h1 align="center">OneDrop</h1>

<p align="center">
  Send one secret file, directly, over your LAN. No cloud. No accounts. No residue.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · <a href="#cli-reference">CLI Reference</a> · <a href="#tls-setup">TLS Setup</a> · <a href="#architecture">Architecture</a> · <a href="SECURITY.md">Security</a>
</p>

---

## The Problem

You need to send a secret file to a teammate - an `.env`, a private key, a credentials bundle - and every obvious option is wrong:

- **Slack / Teams** - indexed, stored on their servers, searchable by admins
- **AirDrop** - relays through Apple infrastructure, requires Bluetooth pairing
- **Google Drive / Dropbox** - your production secrets now live on someone else's servers
- **Email** - unencrypted in transit on most internal mail servers, stored forever
- **`scp` or `rsync`** - requires SSH access to the recipient's machine, which most people don't have set up

You're already on the same network. The file should go directly, encrypted, with a link that stops working the moment it's been received.

## What OneDrop Does

OneDrop starts a minimal HTTPS server on your machine, generates a single-use capability URL, prints a QR code, and waits. The recipient opens the link, clicks download, and the server shuts itself off. The file never left your network.

```
$ onedrop .env.production

================================================================
ONEDROP - HTTPS server running
================================================================
File:        .env.production
Size:        4.21 KB
SHA-256:     a3f1c8...e290b1
URL:         https://192.168.1.42/t/xK9mP2...Qr7/  (LAN / VPN only)
curl:        curl -O https://192.168.1.42/t/xK9mP2...Qr7/.env.production
Downloads:   1 allowed before link expires
================================================================

[QR code appears here - scan from phone on same Wi-Fi]
```

That's it. After one download, the URL returns 410 Gone and the server exits.

---

## Key Features

- **Zero third-party routing** - traffic goes directly from your machine to the recipient's, over your LAN or VPN
- **Single-use capability URL** - a cryptographically random token is baked into the URL; the link is useless after `--max-downloads` hits zero (default: 1)
- **TLS 1.2+ in transit** - encrypted even on a "trusted" LAN; auto-generates a self-signed cert if you don't supply one
- **SHA-256 integrity display** - checksum printed at startup and shown on the landing page so the recipient can verify the file wasn't touched
- **Constant-time token validation** - uses `hmac.compare_digest` to prevent timing-based token recovery
- **Thread-safe download counter** - a mutex-backed limiter counts downloads; a daemon thread triggers clean shutdown the moment the limit is hit
- **Structured audit log** - every request (including rejections) is timestamped and written to `access_audit.log`; the capability token is always redacted from log entries
- **TLS certificate fingerprint** - displayed at startup and on the landing page for manual Trust-On-First-Use (TOFU) verification; prevents MITM even with a self-signed cert
- **mkcert Root CA distribution** - if you use `mkcert`, OneDrop serves the Root CA certificate from the landing page so mobile devices can trust it without warnings
- **Terminal QR code** - optional; scan from your phone, no typing required
- **Zero mandatory third-party dependencies** - the core server runs on Python stdlib only

---

## Quick Start

```bash
# 1. Clone and run the one-time setup (installs deps, copies .env, generates TLS certs)
git clone https://github.com/your-org/onedrop.git
cd onedrop
make setup

# 2. Share a file - the link self-destructs after one download
make share FILE=".env.production"

# 3. Recipient downloads using the URL or curl command printed in the terminal
curl -O https://192.168.1.42/t/<token>/.env.production
```

That's the whole workflow. `make setup` runs once. `make share FILE=...` runs every time you need to transfer something.

---

## Prerequisites

| Requirement     | Version     | Notes                                                                        |
| --------------- | ----------- | ---------------------------------------------------------------------------- |
| Python          | 3.10 – 3.12 | Tested in CI on all three                                                    |
| OpenSSL (CLI)   | Any modern  | Only needed if auto-generating a self-signed cert and `openssl` is in `PATH` |
| mkcert          | Optional    | For locally-trusted certs without browser warnings                           |
| qrcode (Python) | Optional    | `pip install secure-lan-share[qr]` - for terminal QR codes                   |

All core functionality (server, TLS, token auth, audit log, checksum) uses Python stdlib only. No network calls, no telemetry, no external services.

---

## Installation & Setup

Setup is a single command. Seriously - that's it.

```bash
git clone https://github.com/your-org/onedrop.git
cd onedrop
make setup
```

`make setup` runs `setup.sh` which does three things automatically:

1. **Installs the package and all dev dependencies** (`pip install -e ".[dev]"`)
2. **Creates your `.env` config** by copying `.env.example` - your defaults live there, nothing to memorise
3. **Generates locally-trusted TLS certificates** (`onedrop.pem` + `onedrop-key.pem`) using `mkcert` if it's installed, or prints a clear warning if it isn't

If `mkcert` is on your machine, you get certificates your browser already trusts - no warnings, no fingerprint verification required. If it isn't, OneDrop will auto-generate a temporary self-signed cert at runtime and clean it up on exit. Either way, you can start sharing immediately.

> **Don't have mkcert?** Install it from [mkcert.dev](https://github.com/FiloSottile/mkcert), then run `make cert` to regenerate trusted certificates.

After `make setup`, you're done. Open `.env` if you want to change defaults (port, bind address, log path), or just go straight to sharing:

```bash
make share FILE=".env.production"
```

### Environment variables (all optional)

| Variable         | Default                       | Description                                                  |
| ---------------- | ----------------------------- | ------------------------------------------------------------ |
| `ONEDROP_PORT`   | `8443`                        | TCP port to listen on                                        |
| `ONEDROP_BIND`   | Detected LAN IP               | Interface to bind to - set explicitly to lock to one adapter |
| `ONEDROP_CERT`   | `onedrop.pem` → `cert.pem`    | Path to TLS certificate                                      |
| `ONEDROP_KEY`    | `onedrop-key.pem` → `key.pem` | Path to TLS private key                                      |
| `ONEDROP_LOG`    | `access_audit.log`            | Audit log file path                                          |
| `ONEDROP_MAX_DL` | `1`                           | Downloads allowed before the link expires (max: 25)          |

---

## CLI Reference

```
onedrop FILE

Positional:
  FILE                   Path to the file to share

Options (also configurable via ONEDROP_* env vars):
  --port PORT            TCP port (default: 8443)
  --bind ADDRESS         Interface IP to bind to (default: detected LAN IP)
  --cert PATH            TLS certificate file
  --key PATH             TLS private key file
  --log-file PATH        Audit log destination
  --max-downloads N      Max downloads before link expires (default: 1, cap: 25)
  --no-qr                Skip terminal QR code
```

### Common invocations

```bash
# Share once (default - link dies after one download)
onedrop .env.production

# Allow up to 3 downloads (useful for a small team pulling the same file)
onedrop credentials.json --max-downloads 3

# Bind to a specific interface instead of the auto-detected LAN IP
onedrop secrets.tar.gz --bind 10.0.0.5

# Custom port (useful when you don't have root for 443)
onedrop archive.zip --port 8443

# Headless / CI use - recipient runs the printed curl command
onedrop deploy-key.pem --no-qr
```

---

## Architecture

OneDrop is a thin layered package. Each concern lives in its own module so it can be tested in isolation from the network.

```
cli.py          →  parses args + env vars, builds Config, calls run_server()
config.py       →  Config dataclass; validates on __post_init__
server.py       →  ShareTCPServer (holds shared state) + ShareRequestHandler (routes each request)
token_auth.py   →  generates tokens; TokenChecker uses hmac.compare_digest
download_limiter.py  →  thread-safe counter with mutex; hard cap at 25
audit.py        →  structured logging; redacts capability token from all entries
checksum.py     →  SHA-256 in 1 MiB chunks; used at startup + per landing page request
rendering.py    →  HTML template rendering (importlib.resources) + startup banner
utils.py        →  LAN IP detection, cert fingerprint, mkcert root CA discovery, temp cert generation
qr.py           →  optional terminal QR via the qrcode package
```

**Request flow:**

```
GET /t/{token}/{filename}
        │
        ├── Token missing or wrong path format → 404
        ├── hmac.compare_digest(token, candidate) fails → 404  (not 401, to avoid enumeration)
        ├── path == "" (landing page) → render HTML with file info + download button
        ├── path == filename → DownloadLimiter.try_consume()
        │       ├── False (limit reached) → 410 Gone
        │       └── True → stream file in 1 MiB chunks → audit → if remaining==0: daemon shutdown
        └── path == "rootCA.pem" → serve mkcert Root CA if found on host
```

---

## TLS Setup & TOFU Verification

### Verifying the certificate fingerprint

Every time OneDrop starts it prints a `Cert SHA256` fingerprint in the terminal and displays it on the landing page. This fingerprint lets the recipient verify they're talking to your machine and not a MITM:

1. Read the `Cert SHA256` value from your terminal.
2. Share it out-of-band with the recipient (over chat, spoken aloud, etc.).
3. The recipient opens the browser's certificate viewer and confirms the SHA-256 matches.

This is Trust On First Use (TOFU). It's not PKI, but it defeats passive MITM on the same network.

### Trusting mkcert certificates on mobile

If you generated your cert with `mkcert`, your laptop trusts it automatically - but your phone doesn't. OneDrop handles this: if it detects a mkcert Root CA on the host, it serves it as a downloadable link on the landing page.

**iOS / iPadOS:**

1. Open the OneDrop URL on your iPhone/iPad and tap through the certificate warning.
2. On the landing page, expand **"Trust this server on iPad/Android"** and tap **Download Root CA Certificate**.
3. Go to **Settings → Profile Downloaded → Install**.
4. Go to **Settings → General → About → Certificate Trust Settings** and enable the `mkcert` CA.

**Android:**

1. Download `rootCA.pem` from the landing page.
2. Go to **Settings → Security → Encryption & credentials → Install a certificate → CA certificate**.
3. Select the downloaded file.

---

## Development

```bash
make setup        # one-time: install deps + copy .env + generate TLS certs
make share FILE=… # share a file (reads defaults from .env or ONEDROP_* vars)
make cert         # regenerate onedrop.pem + onedrop-key.pem via mkcert

make ci           # full CI pipeline: format + lint + typecheck + test + gitleaks
make check        # lint + typecheck + tests (faster, no secret scanning)
make test         # pytest only
make lint         # ruff check only
make format       # ruff format (auto-fix)
make typecheck    # mypy only
make security     # bandit + pip-audit + gitleaks
make clean        # remove build caches and coverage artifacts
```

Run `make help` to see all targets with the current active values from your `.env`.

The test suite covers every module in isolation (auth, checksum, download limiter, QR fallback, CLI parsing, landing page rendering) plus an end-to-end integration suite that starts a real TLS server in a background thread and drives it with genuine HTTPS requests - including path-traversal attempts and download-limit exhaustion.

---

## License

MIT - see `pyproject.toml`.
