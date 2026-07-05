from __future__ import annotations

import io


def render_terminal_qr(data: str) -> str | None:
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)

    buffer = io.StringIO()
    qr.print_ascii(out=buffer, invert=True)
    return buffer.getvalue()
