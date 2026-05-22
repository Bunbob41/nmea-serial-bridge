"""Render API token as QR pixmap for desktop Guide (optional qrcode package)."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui


def make_token_qr_pixmap(
    token: str,
    *,
    size: int = 180,
    setup_url: Optional[str] = None,
) -> Optional[QtGui.QPixmap]:
    """Return QR pixmap for setup URL (preferred) or raw token, or None if qrcode missing."""
    text = (setup_url or "").strip() or (token or "").strip()
    if not text:
        return None
    try:
        import io

        import qrcode
        from qrcode.constants import ERROR_CORRECT_M

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pix = QtGui.QPixmap()
        if not pix.loadFromData(buf.getvalue(), "PNG"):
            return None
        return pix.scaled(
            size,
            size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None
