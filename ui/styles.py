"""Qt stylesheets per UI variant."""

# Shared dark tab-page rules (standard + log-first)
_TAB_PAGE_DARK = """
QTabWidget { background-color: #1a2420; }
QTabWidget::pane {
    background-color: #222e26;
    border: 1px solid #3d5244;
    border-radius: 0 0 6px 6px;
    top: -1px;
}
QTabBar { background-color: #1a2420; }
QTabBar::tab {
    background-color: #2a3830;
    color: #c0d8c8;
    padding: 8px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #324a38;
    color: #f0faf1;
}
QTabBar::tab:hover:!selected { background-color: #2e4034; }
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport,
QWidget#toolTabScrollHost {
    background-color: #222e26;
    color: #e8f2ea;
}
QLabel#tabHint {
    color: #e0f4e6;
    font-size: 10pt;
    padding-bottom: 4px;
}
QLabel#tabNote {
    color: #b0d0bc;
    font-size: 9pt;
}
QCheckBox { color: #d8ebe0; }
QRadioButton { color: #d8ebe0; }
"""

_TAB_PAGE_LIGHT = """
QTabWidget { background-color: #f0f0f0; }
QTabWidget::pane {
    background-color: #f5f5f5;
    border: 1px solid #ccc;
    top: -1px;
}
QTabBar { background-color: #e8e8e8; }
QTabBar::tab {
    background-color: #e0e0e0;
    color: #333;
    padding: 6px 12px;
}
QTabBar::tab:selected { background-color: #f5f5f5; color: #111; }
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport,
QWidget#toolTabScrollHost {
    background-color: #f5f5f5;
    color: #222;
}
QLabel#tabHint { color: #222; font-size: 10pt; }
QLabel#tabNote { color: #444; font-size: 9pt; }
"""

BRIDGE_STYLESHEET_STANDARD = (
    """
QWidget#BridgeRoot {
    background-color: #1a2420;
    color: #e8f2ea;
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QLabel#appTitle { font-size: 15pt; font-weight: 600; color: #e8f8eb; }
QLabel#appSubtitle { color: #9bb8a4; font-size: 9pt; }
QFrame#statusBanner {
    border-radius: 8px; padding: 10px 12px;
    border: 1px solid #4a6b52; background-color: #243328;
}
QFrame#statusBanner[state="running"] { background-color: #1e3d28; border-color: #6fcf97; }
QFrame#statusBanner[state="starting"] { background-color: #3d3a22; border-color: #d4c06a; }
QFrame#statusBanner[state="failed"] { background-color: #3d2424; border-color: #c97a7a; }
QLabel#statusBannerText { font-size: 12pt; font-weight: 600; color: #f0faf1; }
QLabel#intentHint { color: #c8e6d0; padding: 6px 4px; }
QPushButton#pathBench, QPushButton#pathProduction {
    text-align: left; padding: 12px 14px; border-radius: 8px;
    border: 2px solid #4a6b52; background-color: #2a3830; font-weight: 600; color: #f0faf1;
}
QPushButton#pathBench[active="true"], QPushButton#pathProduction[active="true"] {
    border-color: #8ee0a0; background-color: #2d4a36;
}
QPushButton#btnStart {
    background-color: #2d6a3e; border: 1px solid #6fcf97; border-radius: 8px;
    font-weight: 600; min-height: 44px; color: #f0faf1;
}
QPushButton#btnStop {
    background-color: #4a3234; border: 1px solid #a07070; border-radius: 8px;
    font-weight: 600; min-height: 44px; color: #f0faf1;
}
QPlainTextEdit {
    background-color: #141c18; color: #d8ebe0; border: 1px solid #3d5244;
    font-family: Consolas, monospace; font-size: 9pt;
}
QPlainTextEdit#sendEdit {
    background-color: #141c18; color: #e8f2ea; border: 1px solid #4a6b52;
    border-radius: 4px; font-family: Consolas, monospace; font-size: 9pt;
}
QStatusBar { background: #1e2a22; color: #b8d0c0; border-top: 1px solid #3d5244; }
QGroupBox {
    border: 1px solid #3d5244; border-radius: 6px; margin-top: 12px;
    padding: 10px; color: #e8f2ea;
}
QGroupBox::title { color: #9fd4a8; }
QPushButton {
    background-color: #324a38; color: #f0faf1;
    border: 1px solid #5a7d62; border-radius: 6px; padding: 6px 12px;
}
QComboBox, QLineEdit, QSpinBox {
    background-color: #1a2420; color: #e8f2ea; border: 1px solid #4a6b52; padding: 4px 6px;
}
"""
    + _TAB_PAGE_DARK
)

BRIDGE_STYLESHEET_MINIMAL = (
    """
QWidget#BridgeRoot {
    background-color: #f5f5f5;
    color: #222;
    font-family: "Segoe UI", sans-serif;
    font-size: 9pt;
}
QLabel#statusLine { font-weight: 600; padding: 4px 0; }
QLabel#statusLine[state="running"] { color: #1a6b2e; }
QLabel#statusLine[state="starting"] { color: #8a6d00; }
QLabel#statusLine[state="failed"] { color: #a02020; }
QLabel#statusLine[state="stopped"] { color: #555; }
QPlainTextEdit {
    background-color: #fff; color: #111; border: 1px solid #bbb;
    font-family: Consolas, monospace; font-size: 9pt;
}
QPlainTextEdit#sendEdit {
    background-color: #fff; color: #111; border: 1px solid #999;
    font-family: Consolas, monospace; font-size: 9pt;
}
QPushButton#btnStart { background-color: #e8f5e9; border: 1px solid #4caf50; min-height: 32px; font-weight: 600; color: #111; }
QPushButton#btnStop { background-color: #ffebee; border: 1px solid #e57373; min-height: 32px; color: #111; }
QGroupBox { border: 1px solid #ccc; margin-top: 8px; padding: 8px; color: #222; }
QStatusBar { background: #eee; color: #333; }
"""
    + _TAB_PAGE_LIGHT
)

BRIDGE_STYLESHEET_LOGFIRST = (
    """
QWidget#BridgeRoot {
    background-color: #0d1110;
    color: #c8e0d4;
    font-family: "Segoe UI", sans-serif;
    font-size: 9pt;
}
QPlainTextEdit#logView {
    background-color: #0a0f0c; color: #9fdfb0; border: none;
    font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt;
}
QFrame#controlStrip {
    background-color: #1a2420; border-top: 1px solid #3d5244;
}
QPushButton#btnStart { background-color: #2d6a3e; border: 1px solid #6fcf97; min-height: 28px; color: #f0faf1; }
QPushButton#btnStop { background-color: #4a3234; border: 1px solid #a07070; min-height: 28px; color: #f0faf1; }
QLabel#statusLine { font-weight: 600; color: #8ee0a0; }
QStatusBar { background: #141c18; color: #9bb8a4; }
QPlainTextEdit#sendEdit {
    background-color: #0a0f0c; color: #c8e8d0; border: 1px solid #3d5244;
    font-family: Consolas, monospace; font-size: 9pt;
}
QGroupBox { border: 1px solid #3d5244; color: #e8f2ea; }
QPushButton { background-color: #324a38; color: #f0faf1; border: 1px solid #5a7d62; }
QLineEdit { background-color: #1a2420; color: #e8f2ea; border: 1px solid #4a6b52; }
"""
    + _TAB_PAGE_DARK
)
