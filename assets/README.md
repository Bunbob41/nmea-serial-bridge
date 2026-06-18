# App icon assets

| File | Purpose |
|------|---------|
| `app-icon-source.png` | **Edit this** — DE-9 connector art on a **white or transparent** matte (your provided logo). Required; the build fails if it is missing. |
| `app-icon.png` | Shipped PNG (dark squircle background, generated). |
| `app-icon.ico` | Windows exe / shortcut icon (generated). |

Regenerate after changing source art:

```powershell
python tools/make_app_icon.py
```

The script removes the outer white box, keeps interior white DB-9 pins, and places the glyph on `#1a1d27` to match the dashboard theme. ICO sizes **48px and below** use a **high-contrast shell** variant (lighter glyph) so the logo reads on the Windows taskbar and title bar.
