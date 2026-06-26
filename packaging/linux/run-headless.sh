#!/usr/bin/env bash
# Run Serial Link headless from the repo venv (loads CONFIG_FILE when set).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$(dirname "$0")/venv.sh"
if ! activate_serial_link_venv "$ROOT"; then
  exit 1
fi
if [[ -n "${CONFIG_FILE:-}" && -f "${CONFIG_FILE}" ]]; then
  set -- --config "${CONFIG_FILE}" "$@"
elif [[ -n "${SERIAL_LINK_CONFIG:-}" && -f "${SERIAL_LINK_CONFIG}" ]]; then
  set -- --config "${SERIAL_LINK_CONFIG}" "$@"
fi
exec python serial_link_headless.py "$@"
