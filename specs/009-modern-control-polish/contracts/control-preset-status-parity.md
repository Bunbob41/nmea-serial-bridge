# Contract: Control Preset Status Parity

**Modules**: `ui/modern.py`, `ui/modern_live_status.py`, `ui/modern_styles.py`, `ui/mixin.py`, `ui/backup_status.py`

## Goal

Control preset summary strip MUST use the same **`modernToolsLiveStatus`** visual system as Tools → Presets loaded state (FR-201).

## Widget contract

| Widget | objectName | Parent |
|--------|------------|--------|
| Preset strip frame | `modernControlPresetBar` | Control content card |
| Status label | `modernToolsLiveStatus` | Inside preset strip (replaces `modernIntentHint` on Modern) |
| Optional icon | `modernControlPresetIcon` | Left of label; icon **📌** (not 📋) |

## Behavior

1. **Text source**: Existing `_intent_hint_text()` / `apply_compact_intent_hint()` — unchanged semantics.
2. **Visibility**: Preset strip frame hidden when label text empty (existing `_apply_intent_hint_display` + bar sync).
3. **Kind**: When visible and preset loaded, `statusKind="ready"` (maps from Presets `summaryKind="ok"`).
4. **No bespoke strip colors**: Remove `modernControlPresetBar` blue rgba QSS; appearance comes from `QLabel#modernToolsLiveStatus[statusKind="ready"]`.

## Shared helper

```python
# ui/modern_live_status.py
def apply_modern_live_status(
    lbl: QtWidgets.QLabel,
    line: str,
    tip: str,
    *,
    summary_kind: str | None = None,
    status_kind: str | None = None,
) -> None: ...

def summary_kind_to_status_kind(summary_kind: str) -> str: ...
```

Mixin `_apply_live_chip` MUST delegate to `apply_modern_live_status`.

## Verification

- Manual: Load preset → Presets green “Loaded:” and Control strip match family.
- `test_ui_tabs.test_modern_control_page_chrome` — label objectName is `modernToolsLiveStatus`.
- Regression: `test_field_intent_hint_visible_when_stopped` still passes (Field uses `intentHint`, not Modern).
