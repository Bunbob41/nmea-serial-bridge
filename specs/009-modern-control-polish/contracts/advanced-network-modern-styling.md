# Contract: Advanced Network Panel — Modern Control Styling

**Modules**: `ui/modern_styles.py`, `ui/controls.py` (read-only), `ui/modern.py`

## Scope

When **Advanced network** is checked on Modern Control, `#advancedNetPanel` inside `#modernControlFormCard` MUST match Network card field styling (FR-203).

Standard / Field / Minimal layouts MUST NOT change (panel not under `modernControlFormCard` there).

## QSS selectors (minimum)

```text
QFrame#modernControlFormCard QWidget#advancedNetPanel QGroupBox
QFrame#modernControlFormCard QWidget#advancedNetPanel QLineEdit
QFrame#modernControlFormCard QWidget#advancedNetPanel QRadioButton
QFrame#modernControlFormCard QWidget#advancedNetPanel QLabel
QFrame#modernControlFormCard QWidget#advancedNetPanel QPushButton
```

## Visual rules

| Element | Rule |
|---------|------|
| `QLineEdit` | Same as card COM/UDP fields: bg `#0a0e14`, border rgba slate, radius 8px, min-height 34px |
| `QGroupBox` | Subtle border `rgba(51,65,85,0.45)`, radius 8px, title muted 9pt weight 600 |
| `QRadioButton` | spacing 8px; font 9.5pt |
| Focus | `border-color: MODERN_ACCENT` on line edits |

## Layout rules

- Collapsed: `advancedNetPanel.setVisible(False)` — unchanged from mixin toggle.
- Expanded at 640×420: no horizontal clip on TCP client host row; vertical scroll acceptable on content card if both map + advanced expanded (edge case).

## Verification

- Manual quickstart § Advanced network at minimum size.
- No new tests required beyond existing `test_modern_control_forms_stack_narrow` + manual SC-202.
