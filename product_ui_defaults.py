"""Shipped / fleet UI layout defaults (Standard layout chrome, not path presets)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Optional

from ui.registry import UI_STANDARD, normalize_ui_id

PRODUCT_UI_SCHEMA_VERSION = 1
PRODUCT_UI_FILENAME = "product_ui_defaults.json"
PRODUCT_UI_LOCAL_FILENAME = "product_ui_defaults.local.json"

# Operator-specific keys — never export into product defaults.
_EXPORT_STRIP_KEYS = frozenset(
    {
        "recent_sessions",
        "last_known_good",
        "terminal_ping",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def product_defaults_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        roots.append(Path(sys.executable).resolve().parent)
    roots.append(_repo_root())
    return roots


def product_defaults_paths() -> list[Path]:
    paths: list[Path] = []
    for root in product_defaults_roots():
        paths.append(root / PRODUCT_UI_FILENAME)
        paths.append(root / "assets" / PRODUCT_UI_FILENAME)
        paths.append(root / PRODUCT_UI_LOCAL_FILENAME)
    return paths


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def load_merged_product_ui_defaults() -> dict[str, Any]:
    """Base JSON per root, then optional local override (fleet file beside exe)."""
    merged: dict[str, Any] = {}
    for root in product_defaults_roots():
        for name in (PRODUCT_UI_FILENAME, PRODUCT_UI_LOCAL_FILENAME):
            block = _load_json_file(root / name)
            if block:
                merged = _deep_merge_dict(merged, block)
        assets_block = _load_json_file(root / "assets" / PRODUCT_UI_FILENAME)
        if assets_block:
            merged = _deep_merge_dict(merged, assets_block)
    return merged


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dict(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def default_ui_layout_id() -> str:
    merged = load_merged_product_ui_defaults()
    ui = normalize_ui_id(str(merged.get("ui") or UI_STANDARD))
    return ui if ui else UI_STANDARD


def _sanitize_web_dashboard_for_export(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    try:
        from ui.ui_prefs import (
            WEB_DASHBOARD_STRIP_STORAGE_KEYS,
            _sanitize_web_dashboard_local_storage,
        )
    except Exception:
        return None
    mode = str(block.get("layout_mode") or "gridstack").strip().lower()
    if mode not in ("classic", "gridstack"):
        mode = "gridstack"
    raw_ls = block.get("local_storage")
    if not isinstance(raw_ls, dict):
        return {"layout_mode": mode, "local_storage": {}}
    filtered = {
        k: v
        for k, v in raw_ls.items()
        if k not in WEB_DASHBOARD_STRIP_STORAGE_KEYS
    }
    return {
        "layout_mode": mode,
        "local_storage": _sanitize_web_dashboard_local_storage(filtered),
    }


def sanitize_ui_prefs_for_product_export(prefs: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(prefs or {})
    for key in _EXPORT_STRIP_KEYS:
        out.pop(key, None)
    web = out.get("web_ui")
    if isinstance(web, dict):
        clean_web = dict(web)
        clean_web.pop("token", None)
        clean_web.pop("phone_base_url", None)
        out["web_ui"] = clean_web
    web_dash = _sanitize_web_dashboard_for_export(out.get("web_dashboard"))
    if web_dash is not None:
        out["web_dashboard"] = web_dash
    return out


def capture_ui_layout_snapshot_from_user_profile() -> dict[str, Any]:
    """Snapshot current operator UI files for saving as product default."""
    from ui.picker import CONFIG_PATH as UI_CHOICE_PATH
    from ui.ui_prefs import CONFIG_PATH as UI_PREFS_PATH

    ui = UI_STANDARD
    if UI_CHOICE_PATH.is_file():
        try:
            raw = json.loads(UI_CHOICE_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                ui = normalize_ui_id(str(raw.get("ui") or UI_STANDARD))
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    ui_prefs: dict[str, Any] = {}
    if UI_PREFS_PATH.is_file():
        try:
            raw_prefs = json.loads(UI_PREFS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw_prefs, dict):
                ui_prefs = sanitize_ui_prefs_for_product_export(raw_prefs)
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    return {
        "schema_version": PRODUCT_UI_SCHEMA_VERSION,
        "ui": ui,
        "ui_prefs": ui_prefs,
    }


def _write_product_file(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def _local_product_defaults_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _repo_root()


def save_product_ui_defaults_snapshot(
    snapshot: dict[str, Any],
    *,
    write_local: bool = True,
    write_repo_assets: bool = False,
) -> list[Path]:
    written: list[Path] = []
    if write_local:
        target = _local_product_defaults_dir() / PRODUCT_UI_LOCAL_FILENAME
        _write_product_file(target, snapshot)
        written.append(target.resolve())
    if write_repo_assets and not getattr(sys, "frozen", False):
        target = _repo_root() / "assets" / PRODUCT_UI_FILENAME
        _write_product_file(target, snapshot)
        written.append(target.resolve())
    return written


def apply_product_ui_defaults_to_user(*, overwrite: bool = True) -> bool:
    """Write merged product defaults into %USERPROFILE%\\.cursor-udp-com-bridge\\."""
    merged = load_merged_product_ui_defaults()
    if not merged:
        return False

    from ui.picker import save_ui_choice
    from ui.ui_prefs import CONFIG_PATH as UI_PREFS_PATH, _migrate_schema, _write_json

    ui = normalize_ui_id(str(merged.get("ui") or UI_STANDARD))
    save_ui_choice(ui)

    ui_prefs = merged.get("ui_prefs")
    if not isinstance(ui_prefs, dict) or not ui_prefs:
        return True

    if overwrite or not UI_PREFS_PATH.is_file():
        migrated, _ = _migrate_schema(copy.deepcopy(ui_prefs))
        _write_json(migrated)
    return True


def seed_user_ui_prefs_if_missing() -> bool:
    """First launch: seed ui_prefs.json and ui_choice when prefs file is absent."""
    from ui.picker import CONFIG_PATH as UI_CHOICE_PATH, load_saved_ui, save_ui_choice
    from ui.ui_prefs import CONFIG_PATH as UI_PREFS_PATH

    merged = load_merged_product_ui_defaults()
    if not merged:
        return False

    seeded = False
    if not UI_PREFS_PATH.is_file():
        ui_prefs = merged.get("ui_prefs")
        if isinstance(ui_prefs, dict) and ui_prefs:
            if apply_product_ui_defaults_to_user(overwrite=True):
                seeded = True
        elif not load_saved_ui():
            save_ui_choice(default_ui_layout_id())
            seeded = True
    elif not UI_CHOICE_PATH.is_file() and not load_saved_ui():
        save_ui_choice(default_ui_layout_id())
        seeded = True
    return seeded
