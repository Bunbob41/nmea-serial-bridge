# Quickstart: UI & Workflow Journey Modernization

**Branch**: `2034-ui-journey-modernization` | **Validation**: local only (no agent-browser)

## Prerequisites

- Python 3.10+ with project deps installed
- Windows bench PC or com0com pair optional for bridge steps
- `python verify_all.py` passes on baseline before changes

## 1. Automated gates (run after implementation)

```powershell
cd C:\Users\Morgan\Projects\udp-com-bridge
python -m unittest test_demo_snapshot.py test_ui_prefs.py test_ui_editor.py -v
python verify_all.py
python -m unittest discover -s . -p "test_*.py"
```

Expected: all tests pass; new demo snapshot tests cover restore and preset non-write.

## 2. Product Demo isolation (manual — SC-201/203)

1. Launch Standard layout: `python bridge_gui.py` (or your usual entry).
2. Set a **non-default** state:
   - Load a named preset (not Desk test) or set COM7 + UDP 10110 + strict NMEA.
   - Note whether bridge is **Running** or **Stopped**.
3. **View → Product demo** (or survey bar **Demo** on Field).
4. Advance through at least:
   - **Desk / bench preset** (or first preset step)
   - **UDP start** (if stopped, allows bridge start)
   - **Boat / INS preset**
5. Close demo with **Close** (or new **End demo** if added).
6. Verify within 5 seconds:
   - COM, baud, network mode, NMEA mode match step 2.
   - Active preset name matches step 2.
   - Bridge run/stop matches step 2.
   - Live log contains restore confirmation line.
7. Open `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json` — confirm file was **not** modified during demo (timestamp/hash vs step 2 backup optional).

**Fail if**: COM stuck on demo bench values, bridge left running when it was stopped before, or preset file gained new keys from demo.

## 3. Returning user (manual — SC-102)

1. Set preset **Boat / INS**, stop bridge, close app.
2. Relaunch — Connect should show Boat fields without opening Tools first (&lt; 60 s to Start).
3. **Recent** menu — entries show `· passthrough|strict|raw` suffix.

## 4. UI audit spot-check (manual — SC-103)

At **1280×720** window:

| Layout | Check |
|--------|-------|
| Standard | Start/Stop visible; Serial+Network side-by-side readable |
| Field | Field strip + drawer Presets |
| Tools → Phone | Token + QR: no “generate token first” when token set |
| Connect toolbar | No **Reset sizes** button |

Record failures in `docs/ui-audit-inventory.md`.

## 5. Regression smoke

- Start/stop bridge after demo restore — traffic OK on bench UDP.
- Open HUD after demo — no stuck “Demonstration” label.
- Web API Phone tab — port lock checkbox still works (007/008 unrelated but smoke).

## Deferred / out of scope

- agent-browser dashboard crawl
- Rewriting demo script narration
- Kernel / discovery changes
