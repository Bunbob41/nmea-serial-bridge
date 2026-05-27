# App icon assets

| File | Purpose |
|------|---------|
| `app-icon-source.png` | **Edit this** — RJ-45 + DB-9 art on a **white or transparent** matte (optional; falls back to `app-icon.png`). |
| `app-icon.png` | Shipped PNG (dark squircle background, generated). |
| `app-icon.ico` | Windows exe / shortcut icon (generated). |

Regenerate after changing source art:

```powershell
python tools/make_app_icon.py
```

The script removes the outer white box, keeps interior white DB-9 pins, and places the glyph on `#1a1d27` to match the dashboard theme.
