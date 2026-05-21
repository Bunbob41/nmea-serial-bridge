# Research: Hybrid UI — Qt Visual + WebUI Bridge

**Feature**: `specs/005-hybrid-ui-webui`  
**Date**: 2026-05-21

## R1 — Qt Designer runtime load (Layer 1)

**Decision**: PySide6 `QUiLoader` via `ui/ui_loader.py`; layout files under `ui/resources/*.ui`; widget **wiring stays in Python** (`standard.py`, `field.py`, `mixin.py`).

**Rationale**:
- Native Qt workflow; no recompile for spacing/label tweaks in dev.
- `QUiLoader` is the documented PySide6 path; matches FR-101/102.
- Hub (`ConnectionHubWidget`) and dynamic panels remain code-built — only **shell containers** move to `.ui` to limit migration risk.

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| Full `.ui` for every Connect panel | High churn; hub/splitter logic is dynamic per `connect_panels.py` |
| `pyside6-uic` compile to `.py` | Requires rebuild step; violates “edit without recompilation” goal |
| QML migration | Larger rewrite; out of survey-bridge scope |

**Frozen bundle**: Add `ui/resources` to PyInstaller `datas` (same pattern as `docs/`, helper scripts).

**Fallback**: Keep programmatic shell builders for one release; show `QMessageBox` with path to log on load failure (FR-104).

---

## R2 — HTTP stack for local control plane (Layer 2)

**Decision**: **FastAPI** + **uvicorn** on a **daemon `threading.Thread`**; optional deps in `requirements-web.txt`.

**Rationale**:
- OpenAPI + `TestClient` enable FR-303 contract tests without binding ports.
- Small, well-understood stack; handlers stay thin (delegate to façade).
- Separate thread satisfies FR-205 (uvicorn event loop ≠ Qt main loop ≠ bridge asyncio loop).

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| NiceGUI hosts server on main thread | Risks blocking Qt; better as Phase B client over REST |
| `http.server` stdlib | No schema validation; poor test ergonomics |
| Flask | Heavier sync model; less ideal for async uvicorn co-existence |
| Embed Qt `QHttpServer` (Qt 6.5+) | Ties HTTP to Qt version; fewer contract-test examples in repo |

**Footprint**: ~15–25 MB extra in frozen folder when bundled (acceptable with manifest note per FR-304).

---

## R3 — Qt ↔ HTTP thread boundary

**Decision**: **`BridgeAppFacade`** with:
- **Reads**: `threading.Lock`-protected snapshot dict updated from mixin on coalesced stats timer (≥ 500 ms).
- **Writes**: `QTimer.singleShot(0, callable)` on the `QApplication` thread to call existing `start_bridge` / `stop_bridge` / config setters.

**Rationale**:
- HTTP handlers never touch `QWidget` (constitution + SC-203).
- Reuses `_validate_before_start()` for parity (FR-203).
- Snapshot reads are O(1) and safe at 5 Hz poll.

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| `BlockingQueuedConnection` for every GET | Blocks HTTP thread on Qt; bad at 5 Hz |
| Duplicate bridge instance for Web | Violates FR-204 |
| asyncio bridge loop serves HTTP | Couples failures; harder shutdown ordering |

---

## R4 — Web exposure & auth (Layer 2 security)

**Decision**:
- Default bind **`127.0.0.1:8765`** (`web_ui.enabled` true in dev bench, false in operator default until documented).
- **LAN bind** opt-in: `0.0.0.0` + optional **`X-Bridge-Token`** header when token configured.
- No OAuth in MVP.

**Rationale**: Matches spec User Story 6; survey laptops should not expose bridge control to café Wi‑Fi by default.

---

## R5 — NiceGUI / browser UI (deferred)

**Decision**: **Phase B** — optional NiceGUI or static HTML page at `GET /` that polls `/status` (MVP may return minimal JSON landing or OpenAPI redirect).

**Rationale**: FR-201–203 satisfied by REST alone; avoids second UI framework in MVP critical path.

---

## R6 — `.ui` migration scope

**Decision**: Migrate **containers only** in MVP:
- `standard_connect_shell.ui` — subtitle, status area, host for `setup_connect_tab_panels` output.
- `field_control_strip.ui` — bottom strip geometry.

**Not in MVP**: Minimal, Log-first, HUD, full Connect panel tree, NTRIP panel.

**Rationale**: Delivers SC-101 with lowest regression risk to v1.6.0 hub/discovery behavior.
