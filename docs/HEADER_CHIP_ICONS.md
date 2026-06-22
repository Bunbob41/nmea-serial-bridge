# Header chip icons (Modern UI)

Use this when **View → Customize chip icons…** or when importing a JSON file.

## Format

```json
{
  "schema_version": 1,
  "icons": {
    "control": "🎛",
    "activity": "📋",
    "presets": "⚙",
    "hub": "🛰",
    "fleet": "🔀",
    "nmea": "📡",
    "logging": "📋",
    "bench_tools": "🧪"
  }
}
```

Flat maps are also accepted (`{ "control": "🎛" }`) when every key is a known section id.

## Rules

| Field | Requirement |
|-------|-------------|
| `schema_version` | Optional; must be `1` if present |
| Keys | Section **sid** or dropdown **tier** id (see table below) |
| Values | **1–4 UTF-8 characters** per icon (emoji strongly recommended) |
| Files | UTF-8 `.json`, pretty-print optional |

## Valid keys

| Key | Default | Label |
|-----|---------|-------|
| `control` | 🎛 | Control |
| `activity` | 📋 | Activity |
| `presets` | ⚙ | Presets |
| `hub` | 🛰 | Hub |
| `fleet` | 🔀 | Fleet |
| `nmea` | 📡 | NMEA |
| `black_box` | 💾 | Black box |
| `file_log` | 📄 | File log |
| `phone` | 📱 | Dashboard |
| `inject` | 💉 | Inject |
| `terminal` | ⌨ | Terminal |
| `checks` | 🧪 | Checks |
| `theme` | 🎨 | Theme |
| `guide` | 📖 | Guide |
| `logging` | 📋 | Logging dropdown |
| `bench_tools` | 🧪 | Bench Tools dropdown |

## Reset

**View → Reset chip icons to defaults** clears overrides and restores the product glyphs above.

## Tips

- Prefer single emoji — they read clearly at 30px chip height in **icons-only** mode.
- Avoid multi-codepoint sequences longer than 4 scalar characters (import validator enforces length).
- After import, the chip rail rebuilds immediately; no restart required.
