"""Short NMEA mode labels for status chips and compact UI."""


def nmea_mode_display_label(mode: str) -> str:
    """UI-facing label (internal mode strings unchanged)."""
    m = (mode or "").strip().lower()
    if m == "passthrough":
        return "PassThru"
    if m == "strict":
        return "Strict"
    if m == "raw":
        return "Raw"
    return (mode or "—").strip() or "—"
