"""Fixed high-contrast stylesheet for the Modern tab-per-panel layout.

Vertical stack (top → bottom):
  Survey bar    : 38 px  — nav chips (mixin-managed)
  Global Header : 40 px  — Start/Stop · Status · COM chip  (always visible)
  Command tab bar: 32 px — dense #05070a rail
  Content area  : fills  — Activity | Control | Hub | Tools
  Footer         : 24 px — backup status · version
"""
from __future__ import annotations

MODERN_BG          = "#0a0e14"
MODERN_SURFACE     = "#111827"
MODERN_SURFACE_ALT = "#1a2332"
MODERN_BORDER      = "#334155"
MODERN_TEXT        = "#f8fafc"
MODERN_TEXT_MUTED  = "#94a3b8"
MODERN_ACCENT      = "#3b82f6"
MODERN_ACCENT_BRIGHT = "#60a5fa"     # brighter accent for active tab glow
MODERN_ACCENT_GREEN  = "#34d399"
MODERN_ACCENT_AMBER  = "#fbbf24"
MODERN_TERMINAL_BG   = "#050a12"
MODERN_TERMINAL_TEXT = "#e2f0ff"
MODERN_TABBAR_BG     = "#05070a"     # distinctly darker rail under tabs


def modern_stylesheet() -> str:
    return f"""
/* ═══ Root ════════════════════════════════════════════════════════════════ */
QWidget#BridgeRoot[uiMode="modern"] {{
    background-color: {MODERN_BG};
    color: {MODERN_TEXT};
    font-size: 10pt;
}}

/* ═══ Survey top bar ══════════════════════════════════════════════════════ */
QWidget#surveyMenuBar {{
    background-color: {MODERN_SURFACE};
    border-bottom: 1px solid {MODERN_BORDER};
    min-height: 36px;
    max-height: 40px;
    padding: 2px 6px;
}}
QWidget#surveyTopBarTrack {{
    background-color: transparent;
    border: none;
    padding: 0px 2px;
}}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 4px 9px;
    font-size: 9pt;
    font-weight: 600;
}}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:hover {{
    background-color: #1e3a5f;
    border-color: {MODERN_ACCENT};
    color: #ffffff;
}}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {{
    background-color: #1e3a5f;
    border-color: {MODERN_ACCENT};
    color: #ffffff;
}}
QWidget#surveyMenuBar QLabel {{
    color: {MODERN_TEXT};
    font-size: 9pt;
}}

/* ═══ Global Header Strip — always visible above tab bar ══════════════════
   Contains: ▶ Start  ■ Stop  |  Status banner  |  v1.17.77 · modern  |  COM
   This bar persists across all tab views so mission state is never hidden.  */
QFrame#modernGlobalHeader {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0e1729, stop:1 {MODERN_SURFACE});
    border-bottom: 2px solid rgba(59, 130, 246, 0.35);
    min-height: 40px;
}}
QFrame#modernGlobalHeader[sessionMode="true"] {{
    min-height: 34px;
    border-bottom-width: 1px;
}}
QFrame#modernGlobalHeader[sessionMode="true"] QPushButton#modernStartBtn,
QFrame#modernGlobalHeader[sessionMode="true"] QPushButton#modernStopBtn {{
    min-height: 24px;
    max-height: 26px;
    padding: 2px 10px;
    font-size: 8.5pt;
}}
QFrame#modernGlobalHeader[sessionMode="true"] QFrame#modernStatusBanner {{
    max-width: 999px;
}}
QToolButton#modernHeaderQrBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    font-size: 11pt;
    padding: 0px;
}}
QToolButton#modernHeaderQrBtn:hover {{
    border-color: {MODERN_ACCENT};
    background-color: #1e3a5f;
}}
QToolButton#modernHeaderChipBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    font-size: 8.5pt;
    font-weight: 600;
    padding: 2px 6px;
    min-height: 24px;
    max-height: 26px;
}}
QToolButton#modernHeaderChipBtn:hover {{
    border-color: {MODERN_ACCENT};
    color: {MODERN_TEXT};
    background-color: #1e3a5f;
}}
QToolButton#modernHeaderChipBtn:disabled {{
    color: {MODERN_BORDER};
}}

/* Vertical separators inside the global header and footer */
QFrame#modernFooterSep {{
    background-color: {MODERN_BORDER};
    max-width: 1px;
    min-width: 1px;
    margin: 5px 2px;
}}

/* Version label in the global header */
QLabel#globalHeaderVersion {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8pt;
    font-style: italic;
    padding: 0 4px;
}}

QLabel#modernStatusPill {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8.5pt;
    font-weight: 600;
    padding: 3px 7px;
    border-radius: 6px;
    background-color: {MODERN_SURFACE_ALT};
    border: 1px solid {MODERN_BORDER};
    max-height: 26px;
}}
QLabel#modernStatusPill[pillKind="backup"] {{
    color: {MODERN_ACCENT_GREEN};
}}
QLabel#modernStatusPill[pillKind="backpressure"][alertKind="warn"] {{
    color: {MODERN_ACCENT_AMBER};
    border-color: {MODERN_ACCENT_AMBER};
    background-color: rgba(251, 191, 36, 0.12);
}}
QLabel#modernStatusPill[pillKind="backpressure"][alertKind="error"] {{
    color: #fca5a5;
    border-color: #f87171;
    background-color: rgba(248, 113, 113, 0.14);
}}
QLabel#modernStatusPill[pillKind="health"][healthKind="ok"] {{
    color: {MODERN_ACCENT_GREEN};
}}
QLabel#modernStatusPill[pillKind="health"][healthKind="warn"] {{
    color: {MODERN_ACCENT_AMBER};
    border-color: {MODERN_ACCENT_AMBER};
    background-color: rgba(251, 191, 36, 0.10);
}}
QLabel#modernStatusPill[pillKind="health"][healthKind="error"] {{
    color: #fca5a5;
    border-color: #f87171;
    background-color: rgba(248, 113, 113, 0.12);
}}
QLabel#modernStatusPill[pillKind="hz"] {{
    color: {MODERN_ACCENT_GREEN};
}}
QLabel#modernStatusPill[lockKind="ok"] {{
    color: {MODERN_ACCENT_GREEN};
}}
QLabel#modernStatusPill[lockKind="warn"],
QLabel#modernStatusPill[lockKind="blocked"] {{
    color: {MODERN_ACCENT_AMBER};
}}

QWidget#modernHeaderNav {{
    background-color: transparent;
}}
QWidget#modernHeaderNav QWidget#surveyTopBarTrack {{
    background-color: transparent;
}}
QWidget#modernHeaderNav QFrame#topBarChip {{
    background-color: {MODERN_SURFACE_ALT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    max-width: 88px;
    min-width: 48px;
}}
QWidget#modernHeaderNav QFrame#topBarChip:hover {{
    border-color: {MODERN_ACCENT};
}}
QWidget#modernHeaderNav QToolButton#surveyQuickBtn {{
    background-color: transparent;
    border: none;
    padding: 2px 6px;
    font-size: 9pt;
    font-weight: 600;
}}
QWidget#modernHeaderNav QToolButton#surveyQuickBtn:hover {{
    color: {MODERN_ACCENT_BRIGHT};
}}

/* ═══ Status banner — inline in global header ════════════════════════════ */
QFrame#modernStatusBanner {{
    background-color: transparent;
    border: none;
    border-left: 3px solid {MODERN_BORDER};
    padding: 0px 8px;
    min-width: 60px;
}}
QFrame#modernStatusBanner[clickable="true"]:hover {{
    background-color: {MODERN_SURFACE_ALT};
    border-radius: 4px;
}}
QFrame#modernStatusBanner[clickable="true"]:hover QLabel#modernStatusBannerText {{
    color: {MODERN_ACCENT_BRIGHT};
}}
QFrame#modernStatusBanner[state="running"]  {{ border-left-color: {MODERN_ACCENT_GREEN}; }}
QFrame#modernStatusBanner[state="starting"] {{ border-left-color: {MODERN_ACCENT_AMBER}; }}
QFrame#modernStatusBanner[state="failed"]   {{ border-left-color: #f87171; }}
QLabel#modernStatusBannerText {{
    color: {MODERN_TEXT};
    font-size: 9pt;
    font-weight: 600;
    background: transparent;
}}
QLabel#modernIntentHint {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 9.5pt;
    font-weight: 600;
    padding: 0;
    background: transparent;
}}

/* COM lock chip */
QLabel#comLockChip {{
    color: {MODERN_TEXT};
    background-color: {MODERN_SURFACE_ALT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 3px 7px;
    font-size: 8pt;
}}
QLabel#comLockChip[lockKind="ok"] {{
    color: #d1fae5;
    background-color: #064e3b;
    border-color: {MODERN_ACCENT_GREEN};
}}
QLabel#comLockChip[lockKind="busy"] {{
    color: #fee2e2;
    background-color: #7f1d1d;
    border-color: #f87171;
}}
QLabel#comLockChip[lockKind="running"] {{
    color: #dbeafe;
    background-color: #1e3a8a;
    border-color: {MODERN_ACCENT};
}}

/* ═══ Start / Stop ════════════════════════════════════════════════════════ */
QPushButton#modernStartBtn {{
    background-color: #14532d;
    color: #ecfdf5;
    border: 1px solid {MODERN_ACCENT_GREEN};
    border-radius: 6px;
    padding: 4px 15px;
    font-size: 9pt;
    font-weight: 700;
    min-width: 74px;
}}
QPushButton#modernStartBtn:hover {{ background-color: #166534; }}
QPushButton#modernStartBtn:disabled {{
    background-color: #1a2332;
    color: #475569;
    border-color: {MODERN_BORDER};
}}
QPushButton#modernStopBtn {{
    background-color: #450a0a;
    color: #fef2f2;
    border: 1px solid #f87171;
    border-radius: 6px;
    padding: 4px 15px;
    font-size: 9pt;
    font-weight: 700;
    min-width: 66px;
}}
QPushButton#modernStopBtn:hover {{ background-color: #7f1d1d; }}
QPushButton#modernStopBtn:disabled {{
    background-color: #1a2332;
    color: #475569;
    border-color: {MODERN_BORDER};
}}

/* ═══ Command tab bar — dense dark rail with glow indicator ═══════════════
   {MODERN_TABBAR_BG} rail is noticeably darker than the {MODERN_BG} content
   pane, creating a clear visual seam between navigation and content.
   Active tab uses a brighter {MODERN_ACCENT_BRIGHT} bottom border with a
   subtle blue-gradient background — a "glow" cue without box-shadow.       */
QTabWidget#modernMainTabs {{
    background-color: {MODERN_BG};
}}
QTabWidget#modernMainTabs::pane {{
    border: none;
    background-color: {MODERN_BG};
}}
QTabWidget#modernMainTabs > QTabBar {{
    background-color: {MODERN_TABBAR_BG};
}}
QTabWidget#modernMainTabs QTabBar::tab {{
    background-color: {MODERN_TABBAR_BG};
    color: {MODERN_TEXT_MUTED};
    border: none;
    border-right: 1px solid #0d1117;
    border-bottom: 3px solid transparent;
    padding: 7px 15px;
    font-size: 9pt;
    font-weight: 600;
    min-width: 54px;
    margin: 0px;
}}
/* Active tab — bright accent bottom line + blue-fade glow background */
QTabWidget#modernMainTabs QTabBar::tab:selected {{
    color: #f0f9ff;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(30, 58, 95, 210),
        stop:0.45 rgba(15, 25, 50, 120),
        stop:1 rgba(10, 14, 20, 0));
    border-bottom: 3px solid {MODERN_ACCENT_BRIGHT};
    border-right: 1px solid {MODERN_BORDER};
}}
QTabWidget#modernMainTabs QTabBar::tab:hover:!selected {{
    color: {MODERN_TEXT};
    background-color: #0d1117;
    border-bottom: 3px solid #334155;
}}

/* ═══ Log tab (full dark terminal) ═══════════════════════════════════════ */
QPlainTextEdit#logView {{
    background-color: {MODERN_TERMINAL_BG};
    color: {MODERN_TERMINAL_TEXT};
    border: none;
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
    font-size: 10.5pt;
    padding: 10px;
    selection-background-color: #1d4ed8;
}}
QWidget#modernLogConduit QLabel,
QWidget#modernLogConduit QCheckBox {{
    color: {MODERN_TEXT};
}}
QWidget#modernLogConduit QPushButton {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 5px 10px;
}}

/* ═══ Control tab ════════════════════════════════════════════════════════ */
QWidget#modernControlTab {{
    background-color: {MODERN_BG};
}}
QWidget#modernControlTab QLabel {{
    color: {MODERN_TEXT};
}}
QFrame#modernControlFormCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid rgba(51, 65, 85, 0.45);
    border-radius: 12px;
}}
QLabel#modernControlSectionIcon {{
    font-size: 14pt;
    min-width: 22px;
    padding-top: 1px;
}}
QLabel#modernControlSectionTitle {{
    color: {MODERN_TEXT};
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 0.01em;
}}
QFrame#modernControlSectionSep {{
    color: rgba(51, 65, 85, 0.55);
    max-height: 1px;
    margin: 2px 0 4px 0;
}}
QLabel#modernControlFormLabel {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9pt;
    font-weight: 600;
    min-width: 88px;
}}
QFrame#modernControlFormCard QComboBox,
QFrame#modernControlFormCard QLineEdit {{
    background-color: {MODERN_BG};
    color: {MODERN_TEXT};
    border: 1px solid rgba(71, 85, 105, 0.75);
    border-radius: 8px;
    padding: 7px 11px;
    min-height: 34px;
    font-size: 10pt;
}}
QFrame#modernControlFormCard QComboBox:focus,
QFrame#modernControlFormCard QLineEdit:focus {{
    border-color: {MODERN_ACCENT};
}}
QFrame#modernControlFormCard QComboBox QAbstractItemView {{
    background-color: {MODERN_SURFACE};
    color: {MODERN_TEXT};
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
    border: 1px solid #64748b;
}}
QFrame#modernControlFormCard QCheckBox,
QFrame#modernControlFormCard QRadioButton {{
    color: {MODERN_TEXT};
    spacing: 8px;
    font-size: 9.5pt;
}}
QFrame#modernControlFormCard QPushButton {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}}
QFrame#modernControlFormCard QPushButton:hover {{
    border-color: {MODERN_ACCENT};
    color: #ffffff;
    background-color: #1e3a5f;
}}
QFrame#modernControlPresetBar {{
    background: transparent;
    border: none;
}}
QLabel#modernControlPresetIcon {{
    font-size: 12pt;
    min-width: 20px;
    padding-top: 1px;
}}
QFrame#modernControlFormCard QWidget#advancedNetPanel QGroupBox {{
    color: {MODERN_TEXT};
    font-size: 9.5pt;
    font-weight: 600;
    border: 1px solid rgba(51, 65, 85, 0.45);
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 14px;
}}
QFrame#modernControlFormCard QWidget#advancedNetPanel QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {MODERN_TEXT_MUTED};
}}
QFrame#modernControlFormCard QWidget#advancedNetPanel QLineEdit {{
    background-color: {MODERN_BG};
    color: {MODERN_TEXT};
    border: 1px solid rgba(71, 85, 105, 0.75);
    border-radius: 8px;
    padding: 7px 11px;
    min-height: 34px;
    font-size: 10pt;
}}
QFrame#modernControlFormCard QWidget#advancedNetPanel QLineEdit:focus {{
    border-color: {MODERN_ACCENT};
}}
QFrame#modernControlFormCard QWidget#advancedNetPanel QRadioButton,
QFrame#modernControlFormCard QWidget#advancedNetPanel QCheckBox {{
    color: {MODERN_TEXT};
    spacing: 8px;
    font-size: 9.5pt;
}}
QFrame#modernControlFormCard QWidget#advancedNetPanel QLabel {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9pt;
    font-weight: 600;
}}

QFrame#modernControlMapCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid rgba(51, 65, 85, 0.45);
    border-radius: 12px;
}}
QFrame#modernControlMapHeader {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 2px 0px;
}}
QFrame#modernControlMapHeader:hover {{
    background-color: rgba(255, 255, 255, 0.04);
}}
QLabel#modernControlMapTitle {{
    color: {MODERN_TEXT};
    font-size: 11pt;
    font-weight: 700;
}}
QWidget#modernControlMap {{
    background-color: #0f172a;
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
}}
QToolButton#modernControlMapCollapseBtn {{
    color: {MODERN_TEXT_MUTED};
    background: transparent;
    border: none;
    border-radius: 4px;
    font-size: 10pt;
    font-weight: 700;
    padding: 1px 4px;
}}
QToolButton#modernControlMapCollapseBtn:hover {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
}}
QGroupBox#connectGroupBox {{
    color: {MODERN_TEXT};
    font-weight: 700;
    border: 1px solid {MODERN_BORDER};
    border-radius: 10px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    background-color: {MODERN_SURFACE};
}}
QGroupBox#connectGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {MODERN_ACCENT};
    font-size: 9pt;
}}
QGroupBox#connectGroupBox QLabel {{ color: {MODERN_TEXT}; }}
QGroupBox#connectGroupBox QComboBox,
QGroupBox#connectGroupBox QLineEdit {{
    background-color: {MODERN_BG};
    color: {MODERN_TEXT};
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 7px 10px;
    min-height: 32px;
    font-size: 10pt;
}}
QGroupBox#connectGroupBox QComboBox:focus,
QGroupBox#connectGroupBox QLineEdit:focus {{
    border-color: {MODERN_ACCENT};
}}
QGroupBox#connectGroupBox QComboBox QAbstractItemView {{
    background-color: {MODERN_SURFACE};
    color: {MODERN_TEXT};
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
    border: 1px solid #64748b;
}}
QGroupBox#connectGroupBox QCheckBox,
QGroupBox#connectGroupBox QRadioButton {{
    color: {MODERN_TEXT};
    spacing: 8px;
}}
QGroupBox#connectGroupBox QPushButton {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}}
QGroupBox#connectGroupBox QPushButton:hover {{
    border-color: {MODERN_ACCENT};
    color: #ffffff;
    background-color: #1e3a5f;
}}

/* ═══ Hub tab ════════════════════════════════════════════════════════════ */
QWidget#modernHubTab {{
    background-color: {MODERN_BG};
}}
QWidget#modernHubTab QLabel {{ color: {MODERN_TEXT}; }}
QWidget#modernHubTab QPushButton {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}}
QWidget#modernHubTab QPushButton:hover {{
    border-color: {MODERN_ACCENT};
    background-color: #1e3a5f;
    color: #ffffff;
}}
QFrame#endpointCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
}}
QFrame#endpointCard[selected="true"] {{
    border: 2px solid {MODERN_ACCENT};
    background-color: #172554;
}}
QFrame#endpointCard QLabel#endpointCardTitle {{ color: {MODERN_TEXT}; font-weight: 700; }}
QFrame#endpointCard QLabel#endpointCardSubtitle {{ color: {MODERN_TEXT_MUTED}; }}
QFrame#endpointCard QLabel#endpointCardStatus {{
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
    color: #e2e8f0;
    background-color: #475569;
}}
QFrame#endpointCard[cardStatus="available"] QLabel#endpointCardStatus,
QFrame#endpointCard[cardStatus="idle"] QLabel#endpointCardStatus,
QFrame#endpointCard[cardStatus="stale"] QLabel#endpointCardStatus {{
    color: #cbd5e1;
    background-color: #475569;
}}
QFrame#endpointCard[cardStatus="ready"] QLabel#endpointCardStatus {{
    color: #0f172a;
    background-color: #86efac;
}}
QFrame#endpointCard[cardStatus="running"] QLabel#endpointCardStatus,
QFrame#endpointCard[cardStatus="ok"] QLabel#endpointCardStatus {{
    color: #0f172a;
    background-color: {MODERN_ACCENT_GREEN};
}}
QFrame#endpointCard[cardStatus="warn"] QLabel#endpointCardStatus,
QFrame#endpointCard[cardStatus="port_busy"] QLabel#endpointCardStatus,
QFrame#endpointCard[cardStatus="in_use"] QLabel#endpointCardStatus {{
    color: #0f172a;
    background-color: {MODERN_ACCENT_AMBER};
}}

/* ═══ Modern workspace — persistent sidebar + main pane ═══════════════════ */
QWidget#modernWorkspace {{
    background-color: {MODERN_BG};
}}
QScrollArea#modernSettingsSidebar {{
    background-color: {MODERN_SURFACE};
    border: none;
}}
QToolButton#modernSidebarCollapseBtn {{
    color: {MODERN_TEXT_MUTED};
    border: none;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11pt;
    font-weight: 600;
}}
QToolButton#modernSidebarCollapseBtn:hover {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
}}

/* ═══ Settings page — sidebar nav + stacked content ══════════════════════════ */
QWidget#modernSettingsPage {{
    background-color: {MODERN_BG};
}}
QWidget#modernSettingsSidebar,
QWidget#modernSettingsSidebarInner {{
    background-color: {MODERN_SURFACE};
    border-right: none;
}}
QFrame#modernSettingsSep {{
    color: {MODERN_BORDER};
    max-width: 1px;
    min-width: 1px;
    background-color: {MODERN_BORDER};
    border: none;
}}
QLabel#modernSettingsNavHeader {{
    color: {MODERN_TEXT_MUTED};
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 0 14px;
}}
QLabel#modernSettingsNavGroup {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    padding: 10px 14px 4px 14px;
}}
QPushButton#modernSettingsNavBtn {{
    background-color: transparent;
    color: {MODERN_TEXT_MUTED};
    border: none;
    border-radius: 0;
    text-align: left;
    padding: 7px 12px;
    font-size: 9pt;
    font-weight: 500;
}}
QPushButton#modernSettingsNavBtn:hover {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
}}
QPushButton#modernSettingsNavBtn[navActive="true"] {{
    background-color: rgba(59, 130, 246, 0.15);
    color: {MODERN_ACCENT_BRIGHT};
    font-weight: 600;
    border-left: 3px solid {MODERN_ACCENT};
    padding-left: 11px;
}}

/* ── Top tools chip rail ──────────────────────────────────────────────── */
QFrame#modernToolsChipRail {{
    background-color: {MODERN_SURFACE};
    border-bottom: 1px solid {MODERN_BORDER};
}}
QScrollArea#modernToolsChipScroll {{
    background: transparent;
    border: none;
}}
QWidget#modernToolsChipInner {{
    background: transparent;
}}
QFrame#modernToolsChipSep {{
    color: {MODERN_BORDER};
    background-color: {MODERN_BORDER};
    margin: 0 4px;
}}
QPushButton#modernToolsNavChip {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-radius: 16px;
    padding: 2px 12px;
    font-size: 8.5pt;
    font-weight: 600;
    min-height: 0;
    max-height: 32px;
}}
QPushButton#modernToolsNavChip:hover {{
    background-color: {MODERN_BG};
    color: {MODERN_TEXT};
    border-color: {MODERN_ACCENT};
}}
QPushButton#modernToolsNavChip[navActive="true"] {{
    background-color: rgba(59, 130, 246, 0.22);
    color: {MODERN_ACCENT_BRIGHT};
    border: 1px solid {MODERN_ACCENT};
    font-weight: 700;
}}
QPushButton#modernToolsNavChip:checked {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
}}

QStackedWidget#modernSettingsStack {{
    background-color: {MODERN_BG};
}}

/* ── Settings content — cascade applies to all 7 sections ───────────────── */

/* Scroll hosts */
QWidget#toolTabScrollHost,
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport {{
    background-color: {MODERN_BG};
    border: none;
}}

/* Generic labels inside settings */
QStackedWidget#modernSettingsStack QLabel#tabHint {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8.5pt;
    padding: 2px 0;
}}
QStackedWidget#modernSettingsStack QLabel#tabNote {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8pt;
    font-style: italic;
}}

/* GroupBoxes → subtle modern cards */
QStackedWidget#modernSettingsStack QGroupBox {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding: 14px 12px 10px 12px;
    font-size: 9pt;
    font-weight: 600;
    color: {MODERN_TEXT};
}}
QStackedWidget#modernSettingsStack QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -2px;
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    background-color: {MODERN_SURFACE};
    padding: 0 6px;
}}

/* Inputs */
QStackedWidget#modernSettingsStack QLineEdit,
QStackedWidget#modernSettingsStack QSpinBox,
QStackedWidget#modernSettingsStack QDoubleSpinBox {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 9pt;
    selection-background-color: {MODERN_ACCENT};
}}
QStackedWidget#modernSettingsStack QLineEdit:focus,
QStackedWidget#modernSettingsStack QSpinBox:focus {{
    border-color: {MODERN_ACCENT};
    background-color: #1e2d42;
}}
QStackedWidget#modernSettingsStack QLineEdit:disabled,
QStackedWidget#modernSettingsStack QSpinBox:disabled {{
    color: {MODERN_TEXT_MUTED};
    border-color: #222d3a;
    background-color: {MODERN_SURFACE};
}}

/* ComboBoxes */
QStackedWidget#modernSettingsStack QComboBox {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 9pt;
}}
QStackedWidget#modernSettingsStack QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QStackedWidget#modernSettingsStack QComboBox QAbstractItemView {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    selection-background-color: {MODERN_ACCENT};
}}

/* Checkboxes */
QStackedWidget#modernSettingsStack QCheckBox {{
    color: {MODERN_TEXT};
    font-size: 9pt;
    spacing: 8px;
}}
QStackedWidget#modernSettingsStack QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {MODERN_BORDER};
    border-radius: 4px;
    background-color: {MODERN_SURFACE_ALT};
}}
QStackedWidget#modernSettingsStack QCheckBox::indicator:checked {{
    background-color: {MODERN_ACCENT};
    border-color: {MODERN_ACCENT};
}}
QStackedWidget#modernSettingsStack QCheckBox::indicator:hover {{
    border-color: {MODERN_ACCENT_BRIGHT};
}}

/* Radio buttons */
QStackedWidget#modernSettingsStack QRadioButton {{
    color: {MODERN_TEXT};
    font-size: 9pt;
    spacing: 8px;
}}
QStackedWidget#modernSettingsStack QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    background-color: {MODERN_SURFACE_ALT};
}}
QStackedWidget#modernSettingsStack QRadioButton::indicator:checked {{
    background-color: {MODERN_ACCENT};
    border-color: {MODERN_ACCENT};
}}

/* Buttons — default */
QStackedWidget#modernSettingsStack QPushButton {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 9pt;
    font-weight: 500;
}}
QStackedWidget#modernSettingsStack QPushButton:hover {{
    background-color: #1e3a5f;
    border-color: {MODERN_ACCENT};
    color: #ffffff;
}}
QStackedWidget#modernSettingsStack QPushButton:pressed {{
    background-color: #1a3050;
}}
QStackedWidget#modernSettingsStack QPushButton:disabled {{
    color: {MODERN_TEXT_MUTED};
    border-color: #222d3a;
    background-color: {MODERN_SURFACE};
}}

QWidget#modernChecksPage QPlainTextEdit#diagOutput {{
    min-height: 200px;
}}

/* ── Tools page layout: header band + content card ─────────────────────── */
QFrame#modernToolsPageHeader {{
    background-color: {MODERN_SURFACE};
    border-bottom: 1px solid {MODERN_BORDER};
}}
QLabel#modernToolsPageIcon {{
    font-size: 22pt;
    padding: 0;
    margin: 0;
    min-width: 28px;
}}
QLabel#modernToolsPageTitle {{
    color: {MODERN_TEXT};
    font-size: 16pt;
    font-weight: 700;
    letter-spacing: 0.02em;
}}
QLabel#modernToolsPageSubtitle {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9.5pt;
    padding-left: 38px;
    line-height: 1.35;
}}
QFrame#modernToolsContentCard {{
    background-color: {MODERN_BG};
    border: none;
}}
QLabel#modernToolsInlineSection {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding-top: 4px;
}}
QFrame#modernToolsSectionSep {{
    color: {MODERN_BORDER};
    max-height: 1px;
    margin: 8px 0;
}}
QFrame#modernToolsBenchBanner {{
    background-color: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.45);
    border-radius: 8px;
}}
QFrame#modernToolsBenchBanner QLabel {{
    color: {MODERN_ACCENT_AMBER};
    font-size: 9.5pt;
    font-weight: 600;
}}

QWidget#modernBlackBoxPage,
QWidget#modernFileLogPage,
QWidget#modernActivityToolsPage,
QWidget#modernPresetsPage,
QWidget#modernNmeaPage,
QWidget#modernPhonePage,
QWidget#modernInjectPage,
QWidget#modernTerminalPage,
QWidget#modernGuidePage,
QWidget#modernChecksPage {{
    background-color: {MODERN_BG};
}}

QLabel#modernToolsLiveStatus {{
    font-size: 10pt;
    font-weight: 600;
    padding: 8px 12px;
    border-radius: 8px;
}}
QLabel#modernToolsLiveStatus[statusKind="idle"] {{
    color: {MODERN_TEXT_MUTED};
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
}}
QLabel#modernToolsLiveStatus[statusKind="ready"] {{
    color: {MODERN_ACCENT_BRIGHT};
    background-color: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.35);
}}
QLabel#modernToolsLiveStatus[statusKind="ok"],
QLabel#modernToolsLiveStatus[summaryKind="ok"] {{
    color: {MODERN_ACCENT_GREEN};
    background-color: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}
QLabel#modernToolsLiveStatus[statusKind="warn"],
QLabel#modernToolsLiveStatus[summaryKind="warn"] {{
    color: {MODERN_ACCENT_AMBER};
    background-color: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.35);
}}
QLabel#modernToolsLiveStatus[statusKind="recording"] {{
    color: {MODERN_ACCENT_GREEN};
    background-color: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

/* Tools → NMEA (Modern) */
QLabel#modernNmeaSummary {{
    font-size: 10pt;
    font-weight: 600;
    padding: 10px 14px;
    border-radius: 8px;
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
}}
QLabel#modernNmeaSummary[summaryKind="ok"] {{
    color: {MODERN_ACCENT_GREEN};
    border-color: rgba(34, 197, 94, 0.45);
}}
QLabel#modernNmeaSummary[summaryKind="strict"] {{
    color: {MODERN_ACCENT_BRIGHT};
    border-color: rgba(59, 130, 246, 0.45);
}}
QLabel#modernNmeaSummary[summaryKind="warn"] {{
    color: {MODERN_ACCENT_AMBER};
    border-color: rgba(245, 158, 11, 0.45);
}}
QLabel#modernNmeaSummary[summaryKind="raw"] {{
    color: {MODERN_TEXT_MUTED};
}}
QFrame#modernNmeaPresetLink {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
}}
QLabel#modernNmeaPresetLinkText {{
    font-size: 9.5pt;
    font-weight: 600;
    padding: 8px 10px 0 10px;
}}
QLabel#modernNmeaPresetLinkText[summaryKind="ok"] {{
    color: {MODERN_ACCENT_GREEN};
}}
QLabel#modernNmeaPresetLinkText[summaryKind="warn"] {{
    color: {MODERN_ACCENT_AMBER};
}}
QLabel#modernNmeaPresetLinkText[summaryKind="idle"] {{
    color: {MODERN_TEXT_MUTED};
}}
QLabel#modernNmeaPresetLinkText[summaryKind="ready"] {{
    color: {MODERN_ACCENT_BRIGHT};
}}

/* Tools → shared summary banners (Presets, Activity, logging) */
QLabel#modernToolsSummary {{
    font-size: 10pt;
    font-weight: 600;
    padding: 10px 14px;
    border-radius: 8px;
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
}}
QLabel#modernToolsSummary[summaryKind="ok"],
QLabel#modernToolsSummary[statusKind="ok"] {{
    color: {MODERN_ACCENT_GREEN};
    border-color: rgba(34, 197, 94, 0.45);
}}
QLabel#modernToolsSummary[summaryKind="warn"],
QLabel#modernToolsSummary[statusKind="warn"] {{
    color: {MODERN_ACCENT_AMBER};
    border-color: rgba(245, 158, 11, 0.45);
}}
QLabel#modernToolsSummary[summaryKind="idle"],
QLabel#modernToolsSummary[statusKind="idle"] {{
    color: {MODERN_TEXT_MUTED};
}}
QLabel#modernToolsSummary[summaryKind="ready"],
QLabel#modernToolsSummary[statusKind="ready"] {{
    color: {MODERN_ACCENT_BRIGHT};
    border-color: rgba(59, 130, 246, 0.45);
}}
QLabel#modernToolsSummary[summaryKind="recording"],
QLabel#modernToolsSummary[statusKind="recording"] {{
    color: {MODERN_ACCENT_GREEN};
    border-color: rgba(34, 197, 94, 0.45);
}}
QPushButton#modernToolsPrimaryBtn {{
    background-color: #1e3a5f;
    color: #ffffff;
    border: 1px solid {MODERN_ACCENT};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 9pt;
    font-weight: 600;
}}
QPushButton#modernToolsPrimaryBtn:hover {{
    background-color: {MODERN_ACCENT};
}}
QPushButton#modernToolsSecondaryBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 9pt;
    font-weight: 600;
}}
QPushButton#modernToolsSecondaryBtn:hover {{
    border-color: {MODERN_ACCENT};
    color: {MODERN_ACCENT_BRIGHT};
}}
QGroupBox#modernToolsFormGroup {{
    color: {MODERN_TEXT};
    font-size: 9.5pt;
    font-weight: 600;
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 14px;
}}
QGroupBox#modernToolsFormGroup::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}

QFrame#modernNmeaModeCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 10px;
}}
QFrame#modernNmeaModeCard[modeCard="active"] {{
    border-color: {MODERN_ACCENT};
    background-color: rgba(59, 130, 246, 0.12);
}}
QFrame#modernNmeaModeCard[modeCard="recommended"] {{
    border-color: rgba(34, 197, 94, 0.35);
}}
QLabel#modernNmeaModeTitle {{
    color: {MODERN_TEXT};
    font-size: 11pt;
    font-weight: 700;
}}
QLabel#modernNmeaModeBody {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9pt;
    padding-left: 28px;
}}
QLabel#modernNmeaModeBadge {{
    color: {MODERN_ACCENT_GREEN};
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
QPushButton#modernNmeaPresetBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 8.5pt;
    font-weight: 600;
}}
QPushButton#modernNmeaPresetBtn:hover {{
    border-color: {MODERN_ACCENT};
    color: {MODERN_ACCENT_BRIGHT};
}}
QGroupBox#modernNmeaTypesBox {{
    color: {MODERN_TEXT};
    font-size: 9.5pt;
    font-weight: 600;
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 14px;
}}
QGroupBox#modernNmeaTypesBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
QCheckBox#modernNmeaTypeChip {{
    color: {MODERN_TEXT};
    font-size: 9pt;
    spacing: 6px;
}}
QCheckBox#modernNmeaTypeChip::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {MODERN_BORDER};
    border-radius: 3px;
    background-color: {MODERN_SURFACE_ALT};
}}
QCheckBox#modernNmeaTypeChip::indicator:checked {{
    background-color: {MODERN_ACCENT};
    border-color: {MODERN_ACCENT};
}}
QLabel#modernToolsLiveStatus[statusKind="error"] {{
    color: #f87171;
    background-color: rgba(248, 113, 113, 0.1);
    border: 1px solid rgba(248, 113, 113, 0.4);
}}

/* ── Operator guide (Tools → Guide) ─────────────────────────────────────── */
QLabel#guidePickLabel {{
    color: {MODERN_TEXT};
    font-size: 10pt;
    font-weight: 600;
}}
QLabel#guideIntro {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9.5pt;
    line-height: 1.4;
}}
QPushButton#guideScenarioChip {{
    background-color: {MODERN_SURFACE};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 9.5pt;
    font-weight: 600;
}}
QPushButton#guideScenarioChip:hover {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border-color: {MODERN_ACCENT};
}}
QPushButton#guideScenarioChip:checked {{
    background-color: rgba(59, 130, 246, 0.18);
    color: {MODERN_ACCENT_BRIGHT};
    border-color: {MODERN_ACCENT};
}}
QWidget#guideFlowHost {{
    background-color: transparent;
}}
QLabel#guideFlowNode {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    padding: 10px 8px;
    color: {MODERN_TEXT};
    font-size: 9pt;
    font-weight: 600;
    min-width: 72px;
}}
QLabel#guideFlowArrow {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 14pt;
    font-weight: 700;
}}
QFrame#guideStepCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-left: 3px solid {MODERN_ACCENT};
    border-radius: 8px;
}}
QLabel#guideStepNumber {{
    background-color: {MODERN_ACCENT};
    color: #fff;
    border-radius: 14px;
    font-size: 10pt;
    font-weight: 700;
}}
QLabel#guideStepTitle {{
    color: {MODERN_TEXT};
    font-size: 10.5pt;
    font-weight: 700;
}}
QLabel#guideStepBody {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9.5pt;
}}
QPushButton#guideStepAction {{
    min-width: 108px;
    font-weight: 600;
}}
QPushButton#guideStepActionSecondary {{
    min-width: 108px;
}}
QFrame#guideTipCard {{
    background-color: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.28);
    border-radius: 8px;
}}
QLabel#guideTipTitle {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 9.5pt;
    font-weight: 700;
}}
QLabel#guideTipBody {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9pt;
}}
QFrame#guideFixCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
}}
QLabel#guideFixTitle {{
    color: {MODERN_TEXT};
    font-size: 10pt;
    font-weight: 700;
}}
QLabel#guideFixBody {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9.5pt;
}}
QLabel#guideFixBullet {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 11pt;
}}
QLabel#guideDocLabel {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8.5pt;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding-top: 4px;
}}
QPushButton#guideDocBtn {{
    font-size: 9pt;
}}

/* Plain text areas inside settings (send, diag output) */
QStackedWidget#modernSettingsStack QPlainTextEdit,
QPlainTextEdit#sendEdit,
QPlainTextEdit#diagOutput {{
    background-color: {MODERN_TERMINAL_BG};
    color: {MODERN_TERMINAL_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 9pt;
    padding: 4px;
    selection-background-color: {MODERN_ACCENT};
}}

/* List widget (presets list) */
QListWidget#presetList {{
    background-color: {MODERN_SURFACE};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    font-size: 9pt;
    outline: none;
    padding: 4px;
}}
QListWidget#presetList::item {{
    padding: 7px 10px;
    border-radius: 4px;
}}
QListWidget#presetList::item:selected {{
    background-color: rgba(59, 130, 246, 0.25);
    color: {MODERN_ACCENT_BRIGHT};
}}
QListWidget#presetList::item:hover:!selected {{
    background-color: {MODERN_SURFACE_ALT};
}}

/* Preset action buttons */
QPushButton#btnPresetLoad {{
    background-color: rgba(59, 130, 246, 0.2);
    border-color: {MODERN_ACCENT};
    color: {MODERN_ACCENT_BRIGHT};
    font-weight: 600;
}}
QPushButton#btnPresetLoad:hover {{
    background-color: rgba(59, 130, 246, 0.35);
}}
QPushButton#btnPresetDelete {{
    background-color: rgba(239, 68, 68, 0.12);
    border-color: #ef4444;
    color: #fca5a5;
}}
QPushButton#btnPresetDelete:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    border-color: #f87171;
}}

/* Phone dashboard cards */
QFrame#phoneDashboardCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
    padding: 8px;
}}
QLabel#phoneCardTitle {{
    color: {MODERN_ACCENT_BRIGHT};
    font-size: 9.5pt;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
QPushButton#webPrimaryBtn {{
    background-color: rgba(59, 130, 246, 0.2);
    border-color: {MODERN_ACCENT};
    color: {MODERN_ACCENT_BRIGHT};
    font-weight: 600;
    padding: 6px 18px;
}}
QPushButton#webPrimaryBtn:hover {{
    background-color: rgba(59, 130, 246, 0.35);
}}
QLabel#webPortStatus, QLabel#webListenStatus {{
    color: {MODERN_ACCENT_GREEN};
    font-size: 8.5pt;
    font-weight: 600;
}}
QScrollArea#phoneDashboardScroll,
QScrollArea#phoneDashboardScroll > QWidget > QWidget {{
    background-color: {MODERN_BG};
    border: none;
}}

/* Guide text browsers */
QTextBrowser#guideTextBrowser {{
    background-color: {MODERN_TERMINAL_BG};
    color: {MODERN_TEXT};
    border: none;
    font-size: 9.5pt;
    selection-background-color: {MODERN_ACCENT};
}}
QTabWidget#guideTabWidget {{
    background-color: {MODERN_BG};
}}
QTabWidget#guideTabWidget::pane {{
    border: 1px solid {MODERN_BORDER};
    border-radius: 0 6px 6px 6px;
    background-color: {MODERN_TERMINAL_BG};
}}
QTabWidget#guideTabWidget QTabBar::tab {{
    background-color: {MODERN_SURFACE};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 6px 14px;
    font-size: 8.5pt;
    margin-right: 2px;
}}
QTabWidget#guideTabWidget QTabBar::tab:selected {{
    background-color: {MODERN_TERMINAL_BG};
    color: {MODERN_TEXT};
    border-bottom: 1px solid {MODERN_TERMINAL_BG};
}}
QTabWidget#guideTabWidget QTabBar::tab:hover:!selected {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
}}

/* iOS-style collapsible cards (diagnostics) */
QFrame#iosCard {{
    background-color: {MODERN_SURFACE};
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
}}
QToolButton#iosCardToggle {{
    background-color: transparent;
    color: {MODERN_TEXT};
    border: none;
    font-size: 9pt;
    font-weight: 600;
    text-align: left;
    padding: 8px 12px;
}}
QToolButton#iosCardToggle:hover {{
    color: {MODERN_ACCENT_BRIGHT};
}}
QWidget#iosCardBody {{
    background-color: transparent;
}}
QSplitter#diagCardsSplitter::handle {{
    background-color: {MODERN_BORDER};
    height: 1px;
    margin: 0 16px;
}}

/* ═══ Section titles (Mission Review, Tools bench, etc.) ═══════════════════ */
QLabel#modernTabSectionTitle {{
    color: {MODERN_ACCENT};
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding-bottom: 4px;
}}
QLabel#modernToolsSectionTitle {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.14em;
    padding-top: 4px;
}}

/* ═══ Status footer ═══════════════════════════════════════════════════════ */
QFrame#modernStatusFooter {{
    background-color: {MODERN_SURFACE};
    border-top: 1px solid {MODERN_BORDER};
}}
QLabel#modernFooterVersion {{
    color: #475569;
    font-size: 8pt;
    padding-right: 4px;
}}
QLabel#backupStatus {{
    color: {MODERN_ACCENT_GREEN};
    font-size: 9pt;
    font-weight: 600;
    padding: 0 4px;
}}
QLabel#backupStatus[backupState="warn"]  {{ color: {MODERN_ACCENT_AMBER}; }}
QLabel#backupStatus[backupState="error"] {{ color: #f87171; }}
QLabel#lblStats {{
    color: {MODERN_TEXT_MUTED};
    font-size: 9pt;
}}
QLabel#lblStats[bridgeRunning="true"] {{
    color: {MODERN_ACCENT_AMBER};
    font-weight: 700;
}}

/* ═══ Wire terminal tab ══════════════════════════════════════════════════ */
QWidget#bridgeTerminalPanel {{
    background-color: {MODERN_BG};
}}
QFrame#wireTerminalToolbar {{
    background-color: {MODERN_SURFACE};
    border-bottom: 1px solid {MODERN_BORDER};
    min-height: 36px;
    max-height: 40px;
}}
QLabel#wireToolbarLabel {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8.5pt;
}}
/* Direction filter — segmented bar */
QFrame#wireSegmentBar {{
    background-color: {MODERN_SURFACE_ALT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
}}
QPushButton#wireSegBtn {{
    background-color: transparent;
    color: {MODERN_TEXT_MUTED};
    border: none;
    border-right: 1px solid {MODERN_BORDER};
    padding: 3px 11px;
    font-size: 8.5pt;
    font-weight: 600;
    min-width: 52px;
    border-radius: 0px;
}}
QPushButton#wireSegBtn[segmentEdge="left"] {{
    border-top-left-radius: 5px;
    border-bottom-left-radius: 5px;
}}
QPushButton#wireSegBtn[segmentEdge="right"] {{
    border-right: none;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}
QPushButton#wireSegBtn:hover {{
    background-color: rgba(59, 130, 246, 0.10);
    color: {MODERN_TEXT};
}}
QPushButton#wireSegBtn:checked {{
    background-color: rgba(59, 130, 246, 0.22);
    color: {MODERN_ACCENT_BRIGHT};
}}
QToolButton#wireTypeBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 8.5pt;
    font-weight: 600;
    min-height: 26px;
}}
QToolButton#wireTypeBtn:hover {{
    border-color: {MODERN_ACCENT};
    color: {MODERN_TEXT};
}}
QToolButton#wireTypeBtn[filterActive="true"] {{
    background-color: rgba(59, 130, 246, 0.18);
    color: {MODERN_ACCENT_BRIGHT};
    border-color: {MODERN_ACCENT};
}}
QToolButton#wireHexBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 8.5pt;
    font-weight: 600;
    min-height: 26px;
}}
QToolButton#wireHexBtn:hover {{
    border-color: {MODERN_ACCENT};
    color: {MODERN_TEXT};
}}
QToolButton#wireHexBtn:checked {{
    background-color: rgba(251, 191, 36, 0.15);
    color: {MODERN_ACCENT_AMBER};
    border-color: {MODERN_ACCENT_AMBER};
}}
QToolButton#wireIconBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 6px;
    font-size: 11pt;
    padding: 0px;
}}
QToolButton#wireIconBtn:hover {{
    background-color: #1e3a5f;
    border-color: {MODERN_ACCENT};
    color: #ffffff;
}}
QToolButton#wireIconBtn:checked {{
    background-color: rgba(251, 191, 36, 0.15);
    border-color: {MODERN_ACCENT_AMBER};
    color: {MODERN_ACCENT_AMBER};
}}
/* Legacy chip styles (Standard/other layouts) */
QPushButton#wireDirChip {{
    background-color: transparent;
    color: {MODERN_TEXT_MUTED};
    border: 1px solid {MODERN_BORDER};
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 8.5pt;
    font-weight: 600;
    min-width: 62px;
}}
QPushButton#wireDirChip:hover {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border-color: {MODERN_ACCENT};
}}
QPushButton#wireDirChip:checked {{
    background-color: rgba(59, 130, 246, 0.18);
    color: {MODERN_ACCENT_BRIGHT};
    border-color: {MODERN_ACCENT};
}}
/* Type combo */
QComboBox#wireTypeCombo {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 8.5pt;
}}
QComboBox#wireTypeCombo QAbstractItemView {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    selection-background-color: {MODERN_ACCENT};
}}
/* Hex checkbox */
QCheckBox#wireHexCheck {{
    color: {MODERN_TEXT_MUTED};
    font-size: 8.5pt;
    spacing: 6px;
}}
QCheckBox#wireHexCheck::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {MODERN_BORDER};
    border-radius: 3px;
    background-color: {MODERN_SURFACE_ALT};
}}
QCheckBox#wireHexCheck::indicator:checked {{
    background-color: {MODERN_ACCENT};
    border-color: {MODERN_ACCENT};
}}
/* Action buttons */
QPushButton#wireActionBtn {{
    background-color: {MODERN_SURFACE_ALT};
    color: {MODERN_TEXT};
    border: 1px solid {MODERN_BORDER};
    border-radius: 5px;
    padding: 3px 12px;
    font-size: 8.5pt;
    font-weight: 600;
}}
QPushButton#wireActionBtn:hover {{
    background-color: #1e3a5f;
    border-color: {MODERN_ACCENT};
    color: #ffffff;
}}
QPushButton#wireActionBtn:checked {{
    background-color: rgba(251,191,36,0.15);
    border-color: {MODERN_ACCENT_AMBER};
    color: {MODERN_ACCENT_AMBER};
}}
/* Toolbar separator */
QFrame#wireToolbarSep {{
    background-color: {MODERN_BORDER};
    max-width: 1px;
    min-width: 1px;
    margin: 5px 2px;
}}
/* Wire view */
QPlainTextEdit#wireTerminalView {{
    background-color: {MODERN_TERMINAL_BG};
    color: {MODERN_TERMINAL_TEXT};
    border: none;
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
    font-size: 9.5pt;
    padding: 8px;
    selection-background-color: #1d4ed8;
}}

/* ═══ Mission Review ══════════════════════════════════════════════════════ */
QWidget#modernMissionReview {{ background-color: {MODERN_BG}; }}
QWidget#missionThroughputChart,
QWidget#missionHealthTimeline {{
    border: 1px solid {MODERN_BORDER};
    border-radius: 8px;
}}

/* ═══ Scrollbars ══════════════════════════════════════════════════════════ */
QWidget#BridgeRoot[uiMode="modern"] QScrollBar:vertical {{
    background: {MODERN_SURFACE};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}
QWidget#BridgeRoot[uiMode="modern"] QScrollBar::handle:vertical {{
    background: #475569;
    min-height: 36px;
    border-radius: 5px;
    margin: 2px;
}}
QWidget#BridgeRoot[uiMode="modern"] QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
QWidget#BridgeRoot[uiMode="modern"] QScrollBar::add-line:vertical,
QWidget#BridgeRoot[uiMode="modern"] QScrollBar::sub-line:vertical {{ height: 0; }}
QWidget#BridgeRoot[uiMode="modern"] QScrollBar:horizontal {{
    background: {MODERN_SURFACE};
    height: 10px;
    border-radius: 5px;
    margin: 0;
}}
QWidget#BridgeRoot[uiMode="modern"] QScrollBar::handle:horizontal {{
    background: #475569;
    min-width: 36px;
    border-radius: 5px;
    margin: 2px;
}}
QWidget#BridgeRoot[uiMode="modern"] QScrollBar::handle:horizontal:hover {{
    background: #94a3b8;
}}
"""
