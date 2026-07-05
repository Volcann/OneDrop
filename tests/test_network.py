from __future__ import annotations

from onedrop.network import describe_bind_exposure, get_primary_ip


def test_get_primary_ip_returns_a_string():
    ip = get_primary_ip()
    assert isinstance(ip, str)
    assert ip.count(".") == 3  # crude but sufficient IPv4 shape check


def test_describe_bind_exposure_warns_on_all_interfaces():
    message = describe_bind_exposure("0.0.0.0")
    assert "WARNING" in message
    assert "0.0.0.0" in message


def test_describe_bind_exposure_warns_on_ipv6_any():
    message = describe_bind_exposure("::")
    assert "WARNING" in message


def test_describe_bind_exposure_is_quiet_for_specific_interface():
    message = describe_bind_exposure("192.168.1.50")
    assert "WARNING" not in message
    assert "192.168.1.50" in message
