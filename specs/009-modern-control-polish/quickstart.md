# Quickstart: Modern Control Tab Polish

**Branch**: `2035-modern-control-polish` | **Target**: v1.33.0

## Prerequisites

- Python 3.10+ with project deps
- Modern UI: `python bridge_gui.py` (default or `--modern`)
- Baseline v1.32.7 Control layout already shipped

## 1. Automated gates

```powershell
cd C:\Users\Morgan\Projects\udp-com-bridge
python -m py_compile ui\modern.py ui\modern_live_status.py ui\modern_styles.py
python -m unittest test_ui_tabs.TestUiTabs.test_modern_control_forms_stack_narrow test_ui_tabs.TestUiTabs.test_modern_control_page_chrome test_ui_tabs.TestUiTabs.test_modern_hub_page_banner -v
python verify_all.py
python -m unittest discover -s . -p "test_*.py"
```

Expected: new chrome tests pass; 640px side-by-side regression intact.

## 2. Preset status parity (SC-201)

1. Launch Serial Link; open **Presets**; load «Desk test» (or any named preset).
2. Note green **Loaded:** strip on Presets.
3. Open **Control** — preset summary strip MUST use the same green **ready** family (not legacy blue bar).
4. Hover elided text — full preset path in tooltip.
5. Clear preset / empty session — preset strip on Control hidden.

**Fail if**: Control uses distinct blue styling for same loaded state as Presets green.

## 3. Advanced network at minimum size (SC-202)

1. Window **640×420** (minimum).
2. **Control** → enable **Advanced network**.
3. Cycle UDP remote, TCP server, TCP client — host/port fields readable, no overlap with fan-out checkbox.

**Fail if**: clipped inputs or unreadable labels at minimum width.

## 4. Icons & typography (SC-201 visual scan)

| Surface | Check |
|---------|-------|
| Control preset strip | Icon 📌 (not 📋) |
| Activity page banner | Icon 📋 unchanged |
| Position track header | Title weight/size matches Serial/Network section titles |

## 5. Layout regression (FR-206)

1. **640×420** + **top chips** nav — Serial | Network side-by-side.
2. Repeat with **View → Tools navigation → Sidebar** — forms usable; COM row not clipped.

## 6. Hub banner (FR-209)

1. Open **Hub** — page banner “Hub” with 🛰.
2. No duplicate “Connection hub” title; **Refresh discovery** / **Unlock ports** below banner.

## 7. Operator guide (SC-205)

- `docs/OPERATOR_GUIDE.md` mentions Modern Control sections and tools nav toggle in ≤150 words combined.

## Release checklist

- [ ] `version.py` → 1.33.0
- [ ] `CHANGELOG.md` ## v1.33.0
- [ ] `version_info.txt` aligned if packaging
- [ ] No duplicate `modernControlTab` QSS blocks (grep check)
