"""Live log view model — presets, line classification, and persistence helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nmea_codec import NMEA_SENTENCE_TYPES, log_line_matches_sentence_filter

PRESET_OPS = "ops"
PRESET_SURVEY = "survey"
PRESET_WIRE = "wire_tap"
PRESET_WARN = "warn_only"
PRESET_DEBUG = "debug"
PRESET_CUSTOM = "custom"

PRESET_LABELS: dict[str, str] = {
    PRESET_OPS: "Ops (quiet)",
    PRESET_SURVEY: "Survey (GGA+RMC)",
    PRESET_WIRE: "Wire tap (all NMEA)",
    PRESET_WARN: "Problems only",
    PRESET_DEBUG: "Debug (everything)",
    PRESET_CUSTOM: "Custom…",
}

TOOLBAR_PRESETS: tuple[str, ...] = (
    PRESET_OPS,
    PRESET_SURVEY,
    PRESET_WIRE,
    PRESET_WARN,
    PRESET_DEBUG,
    PRESET_CUSTOM,
)

_SURVEY_TYPES = frozenset({"GGA", "RMC"})


@dataclass
class LogViewState:
    """What the on-screen live log is allowed to show (display only — not bridge NMEA mode)."""

    preset: str = PRESET_OPS
    rx: bool = True
    tx: bool = True
    warn: bool = True
    events: bool = True
    verbose: bool = False
    sentence_types: frozenset[str] = field(default_factory=frozenset)
    hex: bool = False

    def sentence_filter_key(self) -> str:
        if not self.sentence_types:
            return ""
        return ",".join(sorted(self.sentence_types))

    def toolbar_summary(self) -> str:
        if self.preset != PRESET_CUSTOM:
            return PRESET_LABELS.get(self.preset, self.preset)
        parts: list[str] = []
        if not self.rx:
            parts.append("no RX")
        if not self.tx:
            parts.append("no TX")
        if not self.warn:
            parts.append("no warn")
        if not self.events:
            parts.append("no UI")
        if self.verbose:
            if self.sentence_types:
                parts.append("+".join(sorted(self.sentence_types)))
            else:
                parts.append("all NMEA")
        if self.hex:
            parts.append("hex")
        return "Custom: " + (", ".join(parts) if parts else "mixed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset": self.preset,
            "rx": self.rx,
            "tx": self.tx,
            "warn": self.warn,
            "events": self.events,
            "verbose": self.verbose,
            "sentence_types": sorted(self.sentence_types),
            "hex": self.hex,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> LogViewState:
        if not isinstance(raw, dict):
            return state_from_preset(PRESET_OPS)
        preset = str(raw.get("preset", PRESET_OPS) or PRESET_OPS)
        types_raw = raw.get("sentence_types")
        types: frozenset[str] = frozenset()
        if isinstance(types_raw, list):
            types = frozenset(str(t).strip().upper() for t in types_raw if str(t).strip())
        elif isinstance(types_raw, str) and types_raw.strip():
            types = frozenset(p.strip().upper() for p in types_raw.split(",") if p.strip())
        legacy = str(raw.get("log_sentence", "") or "").strip()
        if not types and legacy:
            types = migrate_legacy_sentence_key(legacy)
        st = cls(
            preset=preset if preset in PRESET_LABELS else PRESET_CUSTOM,
            rx=bool(raw.get("rx", True)),
            tx=bool(raw.get("tx", True)),
            warn=bool(raw.get("warn", True)),
            events=bool(raw.get("events", True)),
            verbose=bool(raw.get("verbose", False)),
            sentence_types=types,
            hex=bool(raw.get("hex", False)),
        )
        st.preset = st.detect_preset()
        return st

    def _same_filters_as(self, other: LogViewState) -> bool:
        return (
            self.rx == other.rx
            and self.tx == other.tx
            and self.warn == other.warn
            and self.events == other.events
            and self.verbose == other.verbose
            and self.sentence_types == other.sentence_types
            and self.hex == other.hex
        )

    def detect_preset(self) -> str:
        for key in TOOLBAR_PRESETS:
            if key == PRESET_CUSTOM:
                continue
            if self._same_filters_as(state_from_preset(key)):
                return key
        return PRESET_CUSTOM


def state_from_preset(name: str) -> LogViewState:
    key = (name or PRESET_OPS).strip().lower()
    if key == PRESET_SURVEY:
        return LogViewState(
            preset=PRESET_SURVEY,
            rx=True,
            tx=True,
            warn=True,
            events=True,
            verbose=True,
            sentence_types=_SURVEY_TYPES,
        )
    if key == PRESET_WIRE or key == "all":
        return LogViewState(
            preset=PRESET_WIRE,
            rx=True,
            tx=True,
            warn=True,
            events=True,
            verbose=True,
            sentence_types=frozenset(),
        )
    if key in (PRESET_WARN, "warn"):
        return LogViewState(
            preset=PRESET_WARN,
            rx=False,
            tx=False,
            warn=True,
            events=False,
            verbose=False,
        )
    if key == PRESET_DEBUG:
        return LogViewState(
            preset=PRESET_DEBUG,
            rx=True,
            tx=True,
            warn=True,
            events=True,
            verbose=True,
            sentence_types=frozenset(),
        )
    return LogViewState(
        preset=PRESET_OPS,
        rx=True,
        tx=True,
        warn=True,
        events=True,
        verbose=False,
        sentence_types=frozenset(),
    )


def migrate_legacy_sentence_key(key: str) -> frozenset[str]:
    k = (key or "").strip().upper()
    if not k:
        return frozenset()
    return frozenset(p.strip() for p in k.split(",") if p.strip())


def classify_log_line(txt: str) -> tuple[bool, bool, bool]:
    """Return (is_warn, is_rx, is_tx). Everything else is a bridge/UI event line."""
    s = txt.upper()
    is_warn = (
        "[REJECT]" in s
        or "[DROP" in s
        or "TIMED OUT" in s
        or "ERROR" in s
        or "FAILED" in s
        or "DISCONNECT" in s
        or "FORCING PORT RELEASE" in s
        or "DID NOT EXIT CLEANLY" in s
    )
    is_rx = (
        "UDP←" in txt
        or "TCP←" in txt
        or "INJECT→SER" in txt
        or "GUI→SER" in txt
        or "N→S" in txt
        or "SEND→COM" in s
    )
    is_tx = (
        "SER→" in txt
        or "SER→NET" in txt
        or "COM→" in txt
        or "S→N" in txt
        or "UDP SEND" in s
        or "TCP SEND" in s
    )
    return is_warn, is_rx, is_tx


def log_line_allowed(txt: str, state: LogViewState) -> bool:
    """Whether a line may be appended to the live log under the current view."""
    if state.verbose and not log_line_matches_sentence_filter(txt, state.sentence_filter_key()):
        return False
    is_warn, is_rx, is_tx = classify_log_line(txt)
    if is_warn and state.warn:
        return True
    if is_rx and state.rx:
        return True
    if is_tx and state.tx:
        return True
    if not (is_warn or is_rx or is_tx):
        return state.events
    return False


def sentence_type_choices() -> tuple[str, ...]:
    return NMEA_SENTENCE_TYPES
