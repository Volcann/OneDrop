from __future__ import annotations

import errno
import http.server
import mimetypes
import os
import socketserver
import ssl
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import unquote

from onedrop.audit import audit, build_audit_logger
from onedrop.checksum import sha256_file
from onedrop.config import Config
from onedrop.download_limiter import DownloadLimiter
from onedrop.rendering import print_startup_banner, render_landing_page
from onedrop.token_auth import TokenChecker
from onedrop.utils import (
    fail,
    format_size,
    generate_temp_cert,
    get_cert_fingerprint,
    get_root_ca_path,
)


class ShareTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[http.server.BaseHTTPRequestHandler],
        config: Config,
        auth_checker: TokenChecker,
        limiter: DownloadLimiter,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.config = config
        self.auth_checker = auth_checker
        self.limiter = limiter
        self.audit_logger = build_audit_logger(config.log_file)


class ShareRequestHandler(http.server.BaseHTTPRequestHandler):
    server_version = "OneDrop/0.2"
    server: ShareTCPServer
    timeout = 30

    def do_GET(self) -> None:
        client_ip = self.client_address[0]
        srv = self.server
        parts = [p for p in unquote(self.path).split("/") if p]

        if len(parts) < 2 or parts[0] != "t":
            audit(srv.audit_logger, client_ip, self.path, "DENIED_NO_AUTH")
            self.send_error(404, "Not found")
            return

        if not srv.auth_checker.check(parts[1]):
            audit(srv.audit_logger, client_ip, self.path, "DENIED_NO_AUTH")
            self.send_error(404, "Not found")
            return

        file_name = srv.config.file_to_share.name
        if len(parts) == 2:
            audit(srv.audit_logger, client_ip, self.path, "PAGE_VIEW")
            self._serve_landing_page()
        elif len(parts) == 3 and parts[2] == file_name:
            self._handle_download(client_ip, file_name)
        elif len(parts) == 3 and parts[2] == "rootCA.pem":
            self._handle_ca_download(client_ip)
        else:
            audit(srv.audit_logger, client_ip, self.path, "DENIED_INVALID_PATH")
            self.send_error(404, "Not found")

    def _handle_download(self, client_ip: str, requested_path: str) -> None:
        srv = self.server
        config = srv.config

        if not config.file_to_share.is_file():
            audit(
                srv.audit_logger,
                client_ip,
                requested_path,
                "DOWNLOAD_FAILED",
                "file missing",
            )
            self.send_error(404, "File not found")
            return

        if not srv.limiter.try_consume():
            audit(
                srv.audit_logger,
                client_ip,
                requested_path,
                "DENIED_LIMIT_REACHED",
                f"max={srv.limiter.max_downloads}",
            )
            self._send_exhausted()
            return

        audit(
            srv.audit_logger,
            client_ip,
            requested_path,
            "DOWNLOAD_OK",
            f"remaining={srv.limiter.remaining}",
        )
        self._stream_file(config.file_to_share)

        if srv.limiter.remaining == 0:
            audit(
                srv.audit_logger,
                "server",
                "",
                "SHUTDOWN_INITIATED",
                "download limit reached",
            )
            threading.Thread(target=srv.shutdown, daemon=True).start()

    def _stream_file(self, path: Path) -> None:
        size = path.stat().st_size
        content_type, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                self.wfile.write(chunk)

    def _handle_ca_download(self, client_ip: str) -> None:
        srv = self.server
        ca_path = get_root_ca_path()
        if not ca_path or not ca_path.is_file():
            audit(
                srv.audit_logger,
                client_ip,
                "rootCA.pem",
                "CA_DOWNLOAD_FAILED",
                "not found on host",
            )
            self.send_error(404, "Root CA certificate not found. Is mkcert installed?")
            return
        audit(srv.audit_logger, client_ip, "rootCA.pem", "CA_DOWNLOAD_OK")
        self._stream_ca_file(ca_path)

    def _stream_ca_file(self, path: Path) -> None:
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-type", "application/x-x509-ca-cert")
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", 'attachment; filename="rootCA.pem"')
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(64 * 1024):
                self.wfile.write(chunk)

    def _serve_landing_page(self) -> None:
        config = self.server.config
        limiter = self.server.limiter
        file_exists = config.file_to_share.is_file()
        file_size = (
            format_size(config.file_to_share.stat().st_size)
            if file_exists
            else "Unknown"
        )
        checksum = sha256_file(config.file_to_share) if file_exists else None
        fingerprint = get_cert_fingerprint(config.cert_file)

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Strict-Transport-Security", "max-age=63072000")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

        token = config.token
        ca_instruction_html = _build_ca_instruction_html(f"/t/{token}/rootCA.pem")

        html = render_landing_page(
            file_name=config.file_to_share.name,
            file_exists=file_exists,
            file_size=file_size,
            checksum=checksum,
            downloads_remaining=limiter.remaining,
            max_downloads=limiter.max_downloads,
            cert_fingerprint=fingerprint,
            download_url=f"/t/{token}/{config.file_to_share.name}",
            ca_instruction_html=ca_instruction_html,
        )
        self.wfile.write(html.encode("utf-8"))

    def _send_exhausted(self) -> None:
        self.send_response(410)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Download limit reached. This link is no longer valid.")

    def log_message(self, fmt: str, *args: object) -> None:
        pass


def _build_ca_instruction_html(ca_url: str) -> str:
    ca_path = get_root_ca_path()
    if not ca_path or not ca_path.is_file():
        return ""
    return f"""
  <details class="instructions-details">
    <summary class="instructions-summary">Trust this server on iPad/Android</summary>
    <div class="instructions-content">
      <p>Download and trust this server's Root CA to avoid certificate warnings:</p>
      <a href="{ca_url}" class="ca-download-link">
        <button class="download-btn ca-btn">Download Root CA Certificate</button>
      </a>
      <div class="steps">
        <h4>iOS / iPadOS:</h4>
        <ol>
          <li>Tap the download button and allow the profile.</li>
          <li><strong>Settings</strong> &rarr; <strong>Profile Downloaded</strong> &rarr; <strong>Install</strong>.</li>
          <li><strong>Settings</strong> &rarr; <strong>General</strong> &rarr; <strong>About</strong> &rarr; <strong>Certificate Trust Settings</strong>.</li>
          <li>Enable the switch for the <strong>mkcert</strong> root CA.</li>
        </ol>
        <h4>Android:</h4>
        <ol>
          <li>Tap the download button to get <code>rootCA.pem</code>.</li>
          <li><strong>Settings</strong> &rarr; <strong>Security</strong> &rarr; <strong>Encryption &amp; credentials</strong>.</li>
          <li><strong>Install a certificate</strong> &rarr; <strong>CA certificate</strong>.</li>
          <li>Select the downloaded <code>rootCA.pem</code>.</li>
        </ol>
      </div>
    </div>
  </details>
"""


def build_ssl_context(cert_file: str, key_file: str) -> ssl.SSLContext:
    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        fail(
            f"TLS certificate/key not found ({cert_file}, {key_file}).\n"
            "       Generate one first - see README.md 'TLS Certificate Setup'."
        )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    return context


def _setup_temp_cert(config: Config) -> tempfile.TemporaryDirectory | None:
    if config.cert_file == Path("cert.pem") and config.key_file == Path("key.pem"):
        if not (config.cert_file.exists() and config.key_file.exists()):
            print(
                "TLS cert/key not found. Auto-generating a temporary "
                "self-signed certificate..."
            )
            cert_path, key_path, temp_dir_obj = generate_temp_cert(
                ip_address=config.bind_address
            )
            config.cert_file = cert_path
            config.key_file = key_path
            return temp_dir_obj
    return None


def _handle_bind_error(exc: OSError, config: Config) -> None:
    if exc.errno == errno.EACCES:
        if config.port < 1024:
            fail(
                f"Permission denied: cannot bind to port {config.port}.\n"
                f"       Ports under 1024 are privileged and require superuser (root/sudo) privileges.\n"
                f"       Suggestions:\n"
                f"         1. Run with a non-privileged port (e.g. 8443, 9443):\n"
                f"            ONEDROP_PORT=9443 make share FILE=\"{config.file_to_share}\"\n"
                f"         2. Run using sudo:\n"
                f"            sudo env PATH=$PATH ONEDROP_PORT={config.port} onedrop \"{config.file_to_share}\""
            )
        else:
            fail(f"Permission denied: {exc}")
    elif exc.errno == errno.EADDRINUSE:
        fail(
            f"Address already in use: cannot bind to {config.bind_address}:{config.port}.\n"
            f"       Another process is already listening on this port.\n"
            f"       Suggestions:\n"
            f"         1. Stop the other process.\n"
            f"         2. Run with a different port (e.g. 8443, 9443):\n"
            f"            ONEDROP_PORT=8443 make share FILE=\"{config.file_to_share}\""
        )
    else:
        raise


def run_server(config: Config) -> None:
    if not config.file_to_share.exists():
        print(
            f"WARNING: {config.file_to_share} does not exist yet; "
            "the server will start but downloads will 404 until it does.",
            file=sys.stderr,
        )

    auth_checker = TokenChecker(config.token)
    limiter = DownloadLimiter(max_downloads=config.max_downloads)

    temp_dir_obj = _setup_temp_cert(config)
    context = build_ssl_context(str(config.cert_file), str(config.key_file))

    server_started = False
    try:
        with ShareTCPServer(
            (config.bind_address, config.port),
            ShareRequestHandler,
            config,
            auth_checker,
            limiter,
        ) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            print_startup_banner(config)
            server_started = True
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
    except OSError as exc:
        _handle_bind_error(exc, config)
    finally:
        if temp_dir_obj is not None:
            temp_dir_obj.cleanup()
        if server_started:
            print("\nServer stopped.")
