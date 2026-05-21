# Contract: Qt UI Loader

**Module**: `ui/ui_loader.py`  
**Resources**: `ui/resources/*.ui`

## API

```python
class LayoutLoadError(Exception): ...

def resource_dir() -> Path:
    """Dev: repo ui/resources; frozen: sys._MEIPASS/ui/resources."""

def load_widget(name: str, parent: QWidget | None = None) -> QWidget:
    """Load {name}.ui; raise LayoutLoadError if missing/invalid."""

def load_standard_connect_shell(parent: QWidget) -> QWidget:
    """Loads standard_connect_shell.ui."""

def load_field_control_strip(parent: QWidget) -> QWidget:
    """Loads field_control_strip.ui."""
```

## Required object names (`standard_connect_shell.ui`)

| Object name | Type (expected) | Python wiring |
|-------------|-----------------|---------------|
| `connectPanelHost` | `QWidget` | `setup_connect_tab_panels` / hub embed target |
| `statusBannerHost` | `QWidget` | Parent for `status_banner` frame OR promote banner in .ui |
| `appSubtitle` | `QLabel` | Version subtitle (optional text set in code) |

## Required object names (`field_control_strip.ui`)

| Object name | Type (expected) | Python wiring |
|-------------|-----------------|---------------|
| `fieldStripHost` | `QWidget` | COM/UDP compact row container |
| `fieldStatusHost` | `QWidget` | `status_line` parent |

*Exact names finalized in implement; loader validates presence at startup.*

## Fallback

```python
def load_standard_connect_shell(parent: QWidget) -> QWidget:
    try:
        return load_widget("standard_connect_shell", parent)
    except LayoutLoadError:
        log.warning(...)
        return _build_standard_shell_programmatic(parent)
```

## PyInstaller

```python
datas += [(str(root / "ui" / "resources"), "ui/resources")]
```

## Tests

- `test_ui_loader.py` — fixture minimal `.ui` in `tests/fixtures/` loads; missing name raises `LayoutLoadError`.
- `bench_gui_smoke.py` — Standard + Field launch with `.ui` present.

## Invariants

- Loader MUST NOT register signal connections (wiring in `standard.py` / `field.py` only).
- Hub and bridge logic MUST NOT move into `.ui` files.
