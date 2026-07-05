from __future__ import annotations

import base64
import http.client
import ssl
import subprocess
import threading
import time
from pathlib import Path

import pytest

from onedrop.auth import BasicAuthChecker, Credentials
from onedrop.config import Config
from onedrop.download_limiter import DownloadLimiter
from onedrop.server import ShareRequestHandler, ShareTCPServer, build_ssl_context
from onedrop.token_auth import TokenChecker


def _generate_self_signed_cert(tmp_path: Path) -> tuple[Path, Path]:
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key_path),
            "-out",
            str(cert_path),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ],
        check=True,
        capture_output=True,
    )
    return cert_path, key_path


@pytest.fixture
def running_server(tmp_path, tmp_share_file):
    if not _openssl_available():
        pytest.skip("openssl CLI not available in this environment")

    cert_path, key_path = _generate_self_signed_cert(tmp_path)
    free_port = _find_free_port()
    config = Config(
        file_to_share=tmp_share_file,
        credentials=Credentials(
            username="tester", password="a-long-enough-password"
        ),
        auth_mode="basic",
        port=free_port,
        bind_address="127.0.0.1",
        cert_file=cert_path,
        key_file=key_path,
        log_file=tmp_path / "audit.log",
        max_downloads=2,
        show_qr=False,
    )

    auth_checker = BasicAuthChecker(config.credentials)
    limiter = DownloadLimiter(max_downloads=config.max_downloads)
    ssl_context = build_ssl_context(
        str(config.cert_file), str(config.key_file)
    )

    server = ShareTCPServer(
        (config.bind_address, free_port),
        ShareRequestHandler,
        config,
        auth_checker,
        limiter,
    )
    server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    assigned_port = server.socket.getsockname()[1]

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    yield assigned_port, config

    server.shutdown()
    server.server_close()


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _openssl_available() -> bool:
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _client(port: int) -> http.client.HTTPSConnection:
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return http.client.HTTPSConnection(
        "127.0.0.1", port, context=ssl_context, timeout=5
    )


def _auth_header(username: str, password: str) -> str:
    encoded_token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {encoded_token}"


def test_landing_page_requires_auth(running_server):
    port, _ = running_server
    connection = _client(port)
    connection.request("GET", "/")
    response = connection.getresponse()
    assert response.status == 401


def test_landing_page_with_valid_auth(running_server):
    port, config = running_server
    connection = _client(port)
    auth_header = _auth_header("tester", "a-long-enough-password")
    connection.request("GET", "/", headers={"Authorization": auth_header})
    response = connection.getresponse()
    response_body = response.read().decode()
    assert response.status == 200
    assert "OneDrop" in response_body
    assert config.file_to_share.name in response_body


def test_download_succeeds_and_matches_file_content(
    running_server, tmp_share_file
):
    port, _ = running_server
    connection = _client(port)
    auth_header = _auth_header("tester", "a-long-enough-password")
    connection.request(
        "GET",
        f"/{tmp_share_file.name}",
        headers={"Authorization": auth_header},
    )
    response = connection.getresponse()
    response_body = response.read()
    assert response.status == 200
    assert response_body == tmp_share_file.read_bytes()


def test_download_limit_is_enforced(running_server, tmp_share_file):
    port, _ = running_server
    auth_headers = {
        "Authorization": _auth_header("tester", "a-long-enough-password")
    }

    for _ in range(2):
        connection = _client(port)
        connection.request(
            "GET", f"/{tmp_share_file.name}", headers=auth_headers
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 200
        connection.close()

    time.sleep(0.5)

    with pytest.raises((ConnectionRefusedError, OSError)):
        connection = _client(port)
        connection.request(
            "GET", f"/{tmp_share_file.name}", headers=auth_headers
        )
        connection.getresponse()


def test_path_traversal_is_rejected(running_server):
    port, _ = running_server
    connection = _client(port)
    auth_header = _auth_header("tester", "a-long-enough-password")
    connection.request(
        "GET",
        "/../../etc/passwd",
        headers={"Authorization": auth_header},
    )
    response = connection.getresponse()
    response.read()
    assert response.status == 404


def test_wrong_credentials_are_rejected(running_server):
    port, _ = running_server
    connection = _client(port)
    auth_header = _auth_header("tester", "wrong-password")
    connection.request("GET", "/", headers={"Authorization": auth_header})
    response = connection.getresponse()
    assert response.status == 401


def test_auto_generate_cert_and_fingerprint():
    from onedrop.server import _generate_temp_cert, get_cert_fingerprint

    cert_path, key_path, temp_dir = _generate_temp_cert()
    try:
        assert cert_path.exists()
        assert key_path.exists()
        fingerprint = get_cert_fingerprint(cert_path)
        assert fingerprint != "Unknown"
        assert len(fingerprint.split(":")) == 32
    finally:
        temp_dir.cleanup()


@pytest.fixture
def running_token_server(tmp_path, tmp_share_file):
    if not _openssl_available():
        pytest.skip("openssl CLI not available in this environment")

    cert_path, key_path = _generate_self_signed_cert(tmp_path)
    free_port = _find_free_port()
    config = Config(
        file_to_share=tmp_share_file,
        auth_mode="token",
        token="gI6cZ45t8v9B1mPxLq1W234567890abcdef",
        port=free_port,
        bind_address="127.0.0.1",
        cert_file=cert_path,
        key_file=key_path,
        log_file=tmp_path / "audit.log",
        max_downloads=2,
        show_qr=False,
    )

    auth_checker = TokenChecker(config.token)
    limiter = DownloadLimiter(max_downloads=config.max_downloads)
    ssl_context = build_ssl_context(
        str(config.cert_file), str(config.key_file)
    )

    server = ShareTCPServer(
        (config.bind_address, free_port),
        ShareRequestHandler,
        config,
        auth_checker,
        limiter,
    )
    server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    assigned_port = server.socket.getsockname()[1]

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    yield assigned_port, config

    server.shutdown()
    server.server_close()


def test_token_landing_page_with_valid_token(running_token_server):
    port, config = running_token_server
    connection = _client(port)
    connection.request("GET", f"/t/{config.token}")
    response = connection.getresponse()
    response_body = response.read().decode()
    assert response.status == 200
    assert "OneDrop" in response_body
    assert config.file_to_share.name in response_body


def test_token_landing_page_with_invalid_token(running_token_server):
    port, _ = running_token_server
    connection = _client(port)
    connection.request("GET", "/t/wrong-token")
    response = connection.getresponse()
    response.read()
    assert response.status == 404


def test_token_download_succeeds(running_token_server, tmp_share_file):
    port, config = running_token_server
    connection = _client(port)
    connection.request("GET", f"/t/{config.token}/{tmp_share_file.name}")
    response = connection.getresponse()
    response_body = response.read()
    assert response.status == 200
    assert response_body == tmp_share_file.read_bytes()


def test_token_invalid_route_returns_404(running_token_server):
    port, _ = running_token_server
    connection = _client(port)
    connection.request("GET", "/")
    response = connection.getresponse()
    response.read()
    assert response.status == 404


def test_ca_download_in_basic_auth(running_server, tmp_path):
    from unittest.mock import patch

    port, _ = running_server
    dummy_ca = tmp_path / "dummy_rootCA.pem"
    dummy_ca.write_bytes(b"DUMMY_CA_CONTENT")

    with patch("onedrop.server.get_root_ca_path", return_value=dummy_ca):
        connection = _client(port)
        auth_header = _auth_header("tester", "a-long-enough-password")
        connection.request("GET", "/rootCA.pem", headers={"Authorization": auth_header})
        response = connection.getresponse()
        response_body = response.read()
        assert response.status == 200
        assert response_body == b"DUMMY_CA_CONTENT"
        assert response.getheader("Content-Type") == "application/x-x509-ca-cert"


def test_ca_download_in_token_auth(running_token_server, tmp_path):
    from unittest.mock import patch

    port, config = running_token_server
    dummy_ca = tmp_path / "dummy_rootCA.pem"
    dummy_ca.write_bytes(b"DUMMY_CA_CONTENT")

    with patch("onedrop.server.get_root_ca_path", return_value=dummy_ca):
        connection = _client(port)
        connection.request("GET", f"/t/{config.token}/rootCA.pem")
        response = connection.getresponse()
        response_body = response.read()
        assert response.status == 200
        assert response_body == b"DUMMY_CA_CONTENT"
        assert response.getheader("Content-Type") == "application/x-x509-ca-cert"
