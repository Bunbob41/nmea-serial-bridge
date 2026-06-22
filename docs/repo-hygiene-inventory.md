# Repo hygiene inventory

**Audit date:** 2026-06-22  
**Feature:** `011-repo-hygiene` (PR 1 of N)  
**App version at audit:** v1.40.12  
**Prior related audit:** `docs/pre-release-audit-inventory.md` (2026-06-17) — release readiness only, **not** dead-file / layout purge.

## Purpose

Reduce GitHub root clutter, delete confirmed dead scripts, and move the unittest tree under `tests/` without changing runtime bridge behavior or frozen-bundle paths (bench scripts stay at repo root until PR 2).

## Ship gate (this epic)

| Gate | Rule |
|------|------|
| Runtime | `verify_all.py` + `python -m unittest discover -s tests -p "test_*.py"` exit 0 |
| Frozen | `release.ps1` + `frozen_gui_smoke` unchanged (bench paths at root) |
| Delete | Only files marked **DELETE** below with zero importers |

---

## Root file classification

### Runtime — keep at repo root (do not move in PR 1)

| File(s) | Role |
|---------|------|
| `bridge_gui.py`, `launcher.py`, `bridge_core.py`, `nmea_codec.py` | App entry + engine |
| `app_facade.py`, `web_api.py`, `web_server.py` | Web / facade layer |
| `auto_discovery.py`, `discovery_service.py`, `network_scanner.py`, `port_release.py` | Connection Hub / discovery |
| `bench_config.py`, `bench_defaults.json` | Presets + bench defaults |
| `bench_*.py` (13 files) | QC automation + Diagnostics helpers (frozen manifest) |
| `check_setup.py`, `com_free.py`, `bridge_headless.py`, `nmea_static_sample.py` | verify_all + frozen helpers |
| `verify_all.py`, `version.py`, `py_interpreter.py` | Release / tooling entry |
| `product_ui_defaults.py`, `ntrip_client.py`, `survey_quality.py`, … | Supporting modules imported by `ui/` |

### Tests — **MOVED → `tests/`** (PR 1)

104 × `test_*.py` at repo root → `tests/test_*.py`.  
Fixtures remain `tests/fixtures/`.

### DELETE — PR 1

| File | Reason |
|------|--------|
| `_gen_mixin.py` | Deprecated generator; prints error unless missing `_mixin_body.txt`; zero imports |
| `_patch_guide.py` | One-shot HTML patch for `tool_tabs.py`; not referenced |

### DELETE — deferred (PR 2+ or gitignore only)

| Item | Reason |
|------|--------|
| `tools/patch_*.py`, `tools/_*.py`, `tools/restore_mhs.py` | Agent/dev scratch; mostly untracked / gitignored |
| `launch_logged.py`, `pythonw_min_probe.py` | Local probes; gitignored |
| `assets/_probe_*.png`, `_mhs_src.txt` | Dev artifacts; gitignored |
| Root `*.log` (`debug-*.log`, `launch_probe.log`, …) | Local noise; add/extend gitignore if tracked |

### Legacy layout — deferred (PR 3)

| Item | Notes |
|------|-------|
| `ui/standard.py` | Legacy alias after Standard layout removal; still referenced by registry aliases |
| `ui/minimal.py`, `ui/logfirst.py` | Alternate layouts; low traffic but still in `UI_ORDER` smoke |

### Bench scripts — deferred (PR 2)

Move `bench_*.py` → `tools/bench/` requires updates to:

- `nmea_serial_bridge.spec` `HELPER_SCRIPTS`
- `tools/frozen_bundle_manifest.py`
- `verify_all.py`, `bench_all.py`, `ui/mixin.py` diagnostics paths
- Operator docs + specs quickstarts

**Risk:** high — full frozen bundle retest required.

### Specs / docs — keep

`specs/` is large but intentional (Spec Kit history). Not bloat for operators; optional `docs/README.md` index update only.

---

## Verification log

| Date | Scope | Result | Notes |
|------|-------|--------|-------|
| 2026-06-22 | Inventory created | — | This document |
| 2026-06-22 | PR 1: delete 2 scripts + move 104 tests | pass | Branch `011-repo-hygiene-pr1` |

---

## PR plan

| PR | Scope |
|----|-------|
| **1** (this) | Inventory doc, delete `_gen_mixin.py` + `_patch_guide.py`, move `test_*.py` → `tests/`, update discover paths |
| **2** | Move `bench_*.py` → `tools/bench/` + frozen manifest/spec |
| **3** | Legacy UI layout trim (`standard` alias cleanup) |
| **4** | Root module grouping (`core/` expansion) — only if justified |
