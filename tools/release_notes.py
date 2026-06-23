#!/usr/bin/env python3
"""Build GitHub release notes from CHANGELOG.md (UTF-8, no PowerShell mojibake)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
INSTALL_FOOTER = """\
### Install

- Unzip and run `serial-link\\serial-link.exe` (keep the whole folder).
- Settings persist under `%USERPROFILE%\\.cursor-udp-com-bridge\\`.
- **Unsigned** — SmartScreen may warn. See `docs/OPERATOR_GUIDE.md`.

### Assets

- `serial-link-v{version}-win64.zip` — Windows x64 one-folder build
- `release-manifest-v{version}.json` — SHA-256 checksums
- `build-env-v{version}.txt` — pip freeze / build environment lock
"""

# Bullets aimed at maintainers/CI — omit from operator-facing GitHub releases.
_MAINTAINER_BULLET_HINTS = (
    "release notes generated",
    "--notes-file",
    "mojibake",
    "github actions skips",
    "verify_all",
    "qt offscreen",
    "pillow",
)


def _operator_bullets(bullets: list[str]) -> list[str]:
    kept: list[str] = []
    for bullet in bullets:
        low = bullet.lower()
        if any(hint in low for hint in _MAINTAINER_BULLET_HINTS):
            continue
        kept.append(bullet)
    return kept


def read_version(explicit: str | None) -> str:
    if explicit:
        return explicit.lstrip("v").strip()
    text = (ROOT / "version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise SystemExit("Could not read __version__ from version.py")
    return match.group(1).strip()


def _parse_sections(changelog_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in changelog_text.splitlines():
        heading = re.match(r"^##\s+v(\d+\.\d+\.\d+)\s*$", line.strip())
        if heading:
            current = heading.group(1)
            sections[current] = []
            continue
        if current is None:
            continue
        if line.startswith("## "):
            current = None
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            sections[current].append(stripped[2:].strip())
    return sections


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def _versions_since(sections: dict[str, list[str]], since_exclusive: str | None) -> list[str]:
    keys = sorted(sections.keys(), key=_version_key, reverse=True)
    if since_exclusive is None:
        return keys
    floor = _version_key(since_exclusive)
    return [v for v in keys if _version_key(v) > floor]


def build_release_notes(
    version: str,
    *,
    since: str | None = None,
    max_sections: int = 8,
) -> str:
    if not CHANGELOG.exists():
        raise SystemExit(f"Missing {CHANGELOG}")
    sections = _parse_sections(CHANGELOG.read_text(encoding="utf-8"))
    if version not in sections and not sections:
        raise SystemExit(f"No changelog sections found for v{version}")

    picked = sorted(
        [
            v
            for v in sections
            if _version_key(v) <= _version_key(version)
            and (since is None or _version_key(v) > _version_key(since))
        ],
        key=_version_key,
        reverse=True,
    )[:max_sections]
    if not picked:
        raise SystemExit(f"No changelog bullets for v{version} (since v{since or 'start'})")

    lo = picked[-1]
    hi = picked[0]

    lines = [
        f"Windows x64 one-folder build (PyInstaller) — **v{version}**.",
        "",
    ]
    if lo != hi:
        lines.append(f"### Highlights (v{lo}–v{hi})")
    else:
        lines.append(f"### Highlights (v{version})")
    lines.append("")

    for ver in picked:
        bullets = _operator_bullets(sections.get(ver, []))
        if not bullets:
            continue
        if len(picked) > 1:
            lines.append(f"### v{ver}")
        for bullet in bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append(INSTALL_FOOTER.format(version=version).rstrip())
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GitHub release notes from CHANGELOG.md")
    parser.add_argument("--version", help="Release version (default: version.py)")
    parser.add_argument(
        "--since",
        help="Only include changelog sections after this version (e.g. 1.40.20 for a 1.41.x drop)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write UTF-8 notes file (recommended for gh release --notes-file)",
    )
    parser.add_argument("--max-sections", type=int, default=8)
    args = parser.parse_args()

    version = read_version(args.version)
    notes = build_release_notes(
        version,
        since=args.since.lstrip("v") if args.since else None,
        max_sections=max(1, args.max_sections),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(notes, encoding="utf-8", newline="\n")
        print(f"[release_notes] wrote {args.output}", flush=True)
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
