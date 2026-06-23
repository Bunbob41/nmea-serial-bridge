#!/usr/bin/env bash
# Build serial-link-vX.Y.Z-linux-headless.tar.gz for GitHub Releases.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
VERSION="$(python -c 'from version import __version__; print(__version__)')"
OUT_DIR="$ROOT/dist"
ARCHIVE="$OUT_DIR/serial-link-v${VERSION}-linux-headless.tar.gz"
mkdir -p "$OUT_DIR"
NAME="serial-link-v${VERSION}-linux-headless"
STAGE="$OUT_DIR/$NAME"
rm -rf "$STAGE"
mkdir -p "$STAGE"
tar -cf - \
  --exclude='.git' \
  --exclude='dist' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  -C "$ROOT" . \
  | tar -xf - -C "$STAGE"
chmod +x "$STAGE/packaging/linux/"*.sh 2>/dev/null || true
tar -czf "$ARCHIVE" -C "$OUT_DIR" "$NAME"
rm -rf "$STAGE"
echo "Built $ARCHIVE"
ls -lh "$ARCHIVE"
