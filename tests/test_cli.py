from __future__ import annotations

import pytest

from onedrop.cli import build_parser, main


def test_parser_only_has_file_and_auth_mode():
    parser = build_parser()
    args = parser.parse_args(["payload.bin"])
    assert args.file == "payload.bin"
    assert args.auth_mode == "token"
    assert args.domain is None


def test_parser_accepts_auth_mode_basic():
    parser = build_parser()
    args = parser.parse_args(["payload.bin", "--auth-mode", "basic"])
    assert args.auth_mode == "basic"


def test_main_exits_when_credentials_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("SHARE_USERNAME", raising=False)
    monkeypatch.delenv("SHARE_PASSWORD", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "payload.bin"), "--auth-mode", "basic"])
    assert exc_info.value.code == 1


def test_main_exits_on_invalid_port(monkeypatch, tmp_path):
    monkeypatch.setenv("SHARE_USERNAME", "tester")
    monkeypatch.setenv("SHARE_PASSWORD", "a-long-enough-password")
    monkeypatch.setenv("ONEDROP_PORT", "0")
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "payload.bin"), "--auth-mode", "basic"])
    assert exc_info.value.code == 1


def test_main_exits_on_weak_password(monkeypatch, tmp_path):
    monkeypatch.setenv("SHARE_USERNAME", "tester")
    monkeypatch.setenv("SHARE_PASSWORD", "12345")
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "payload.bin"), "--auth-mode", "basic"])
    assert exc_info.value.code == 1


def test_config_defaults_from_env(monkeypatch):
    monkeypatch.setenv("ONEDROP_PORT", "9443")
    monkeypatch.setenv("ONEDROP_BIND", "192.168.1.99")
    monkeypatch.setenv("ONEDROP_CERT", "my.pem")
    monkeypatch.setenv("ONEDROP_KEY", "my-key.pem")
    monkeypatch.setenv("ONEDROP_LOG", "custom.log")
    monkeypatch.setenv("ONEDROP_MAX_DL", "5")

    from onedrop.config import Config
    from onedrop.token_auth import generate_token

    config = Config(
        file_to_share="payload.bin", auth_mode="token", token=generate_token()
    )
    assert config.port == 9443
    assert config.bind_address == "192.168.1.99"
    assert str(config.cert_file) == "my.pem"
    assert str(config.key_file) == "my-key.pem"
    assert str(config.log_file) == "custom.log"
    assert config.max_downloads == 5


def test_main_module_execution():
    import runpy
    from unittest.mock import patch

    with patch("onedrop.cli.main") as mock_main:
        runpy.run_module("onedrop", run_name="__main__")
        mock_main.assert_called_once()
