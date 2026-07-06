from __future__ import annotations

import builtins

import pytest

from onedrop import qr


def test_render_terminal_qr_returns_string_when_qrcode_installed():
    pytest.importorskip("qrcode")
    result = qr.render_terminal_qr("https://example.com:8443")
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_terminal_qr_returns_none_when_qrcode_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "qrcode":
            raise ImportError("simulated missing dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert qr.render_terminal_qr("https://example.com:8443") is None
