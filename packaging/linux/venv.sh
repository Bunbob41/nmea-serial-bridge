#!/usr/bin/env bash
# Resolve venv location (repo .venv vs Linux-side path for WSL /mnt/c).
resolve_serial_link_venv() {
  local root="$1"
  if [[ -n "${SERIAL_LINK_VENV:-}" ]]; then
    printf '%s\n' "$SERIAL_LINK_VENV"
    return 0
  fi
  if [[ -f "$root/.serial-link-venv" ]]; then
    tr -d '\r\n' <"$root/.serial-link-venv"
    return 0
  fi
  # WSL: venv on drvfs (/mnt/c/...) often breaks ensurepip — use native Linux FS.
  if [[ "$root" == /mnt/* ]]; then
    printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/serial-link/venv"
    return 0
  fi
  printf '%s\n' "$root/.venv"
}

activate_serial_link_venv() {
  local root="$1"
  local venv
  venv="$(resolve_serial_link_venv "$root")"
  if [[ ! -f "$venv/bin/activate" ]]; then
    echo "Missing venv at $venv — run ./packaging/linux/install.sh first." >&2
    return 1
  fi
  # shellcheck disable=SC1090
  source "$venv/bin/activate"
}
