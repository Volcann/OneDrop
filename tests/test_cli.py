from __future__ import annotations

import pytest

from onedrop.cli import build_parser, main


def test_parser_accepts_file_argument():
    parser = build_parser()
    args = parser.parse_args([".env.production"])
    assert args.file == ".env.production"


def test_parser_has_no_auth_mode_flag():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([".env.production", "--auth-mode", "basic"])


def test_main_exits_on_invalid_port(monkeypatch, tmp_path):
    monkeypatch.setenv("ONEDROP_PORT", "0")
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / ".env.production")])
    assert exc_info.value.code == 1


def test_config_defaults_from_env(monkeypatch, tmp_path):
    fake_file = tmp_path / ".env.production"
    fake_file.write_text("dummy content")

    monkeypatch.setenv("ONEDROP_PORT", "9443")
    monkeypatch.setenv("ONEDROP_BIND", "192.168.1.99")
    monkeypatch.setenv("ONEDROP_CERT", "my.pem")
    monkeypatch.setenv("ONEDROP_KEY", "my-key.pem")
    monkeypatch.setenv("ONEDROP_LOG", "custom.log")
    monkeypatch.setenv("ONEDROP_MAX_DL", "5")

    from onedrop.config import Config
    from onedrop.token_auth import generate_token

    config = Config(file_to_share=str(fake_file), token=generate_token())
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
