"""Qt stylesheets per UI variant — readability-first surfaces and contrast."""

# Callout bars: readable body text on muted surface (accent = left border only).
_CALLOUT_DARK = """
QLabel#intentHint, QLabel#appSubtitle {
    color: #f4f0ea;
    background-color: #3a3238;
    border: 1px solid #6a5a48;
    border-left: 4px solid #c9a227;
    border-radius: 4px;
    padding: 6px 10px;
    font-weight: 600;
}
QLabel#intentHint[intentCompact="true"] {
    padding: 3px 8px;
    font-size: 9pt;
    font-weight: 500;
    max-height: 24px;
}
"""
_CALLOUT_LIGHT = """
QLabel#intentHint, QLabel#appSubtitle {
    color: #1a1a1a;
    background-color: #e4e0da;
    border: 1px solid #a09888;
    border-left: 4px solid #8a7028;
    border-radius: 4px;
    padding: 6px 10px;
    font-weight: 600;
}
QLabel#intentHint[intentCompact="true"] {
    padding: 3px 8px;
    font-size: 9pt;
    font-weight: 500;
    max-height: 24px;
}
"""

_ROUND_CONNECT_ROWS_DARK = """
QWidget#connectPanelRow {
    border: 1px solid #7f9a73;
    border-radius: 14px;
    background-color: rgba(24, 34, 26, 0.52);
    margin: 5px 6px;
    padding: 2px;
}
QToolButton#connectPanelDisclosure {
    border: 1px solid #6f8d63;
    border-radius: 12px;
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(62, 88, 64, 0.92),
        stop:1 rgba(48, 68, 50, 0.9)
    );
    color: #f2f6ed;
    font-weight: 600;
    text-align: left;
    padding: 8px 13px;
    margin: 4px 7px;
}
QToolButton#connectPanelDisclosure:hover {
    border-color: #9fc092;
    background-color: rgba(70, 100, 74, 0.95);
}
QToolButton#connectPanelDisclosure:checked {
    border-color: #b8d4ae;
    background-color: rgba(96, 139, 102, 0.95);
    color: #f7fbf4;
}
"""

_ROUND_CONNECT_ROWS_LIGHT = """
QWidget#connectPanelRow {
    border: 1px solid #a7b59c;
    border-radius: 14px;
    background-color: rgba(238, 245, 234, 0.95);
    margin: 5px 6px;
    padding: 2px;
}
QToolButton#connectPanelDisclosure {
    border: 1px solid #96aa86;
    border-radius: 12px;
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(228, 238, 220, 0.98),
        stop:1 rgba(214, 228, 204, 0.98)
    );
    color: #253025;
    font-weight: 600;
    text-align: left;
    padding: 8px 13px;
    margin: 4px 7px;
}
QToolButton#connectPanelDisclosure:hover {
    border-color: #7f9a70;
    background-color: rgba(206, 224, 196, 0.99);
}
QToolButton#connectPanelDisclosure:checked {
    border-color: #67865a;
    background-color: rgba(190, 214, 178, 0.99);
    color: #1d281d;
}
"""

_APPLE_ROUND_DARK = """
QPushButton, QComboBox, QLineEdit, QSpinBox {
    border-radius: 12px;
    padding: 6px 10px;
}
QPlainTextEdit { border-radius: 12px; }
QTabBar::tab { border-radius: 12px 12px 0 0; }
QStatusBar::item { border-radius: 10px; }
QGroupBox {
    border-radius: 12px;
    margin-top: 14px;
    padding: 10px;
}
"""

_APPLE_ROUND_LIGHT = """
QPushButton, QComboBox, QLineEdit, QSpinBox {
    border-radius: 12px;
    padding: 6px 10px;
}
QPlainTextEdit { border-radius: 12px; }
QTabBar::tab { border-radius: 12px 12px 0 0; }
QStatusBar::item { border-radius: 10px; }
QGroupBox {
    border-radius: 12px;
    margin-top: 14px;
    padding: 10px;
}
"""

# Shared dark tab pages (Standard + Log-first tool areas)
_TAB_PAGE_DARK = """
QTabWidget { background-color: #241a1f; }
QTabWidget::pane {
    background-color: #2f2329;
    border: 1px solid #7a5a2d;
    border-radius: 0 0 8px 8px;
    top: -1px;
}
QTabBar { background-color: #241a1f; }
QTabBar::tab {
    background-color: #4a2f39;
    color: #f2e7d2;
    padding: 8px 16px;
    margin-right: 8px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background-color: #6b3a4a;
    color: #f8f4ec;
    font-weight: 600;
}
QTabBar::tab:hover:!selected { background-color: #5a3543; }
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport,
QWidget#toolTabScrollHost {
    background-color: #2f2329;
    color: #f6eee0;
}
QWidget#toolTabScrollHost[themeStudio="true"] {
    background-color: #2a1d22;
    border: 1px solid #5a3240;
    border-radius: 8px;
    padding: 6px;
}
QLabel#themeStudioHint {
    color: #f4f0ea;
    font-size: 10pt;
    font-weight: 600;
}
QGroupBox#themeStudioCard {
    background-color: rgba(53, 38, 46, 0.75);
    border: 1px solid #8d6a34;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px;
}
QGroupBox#themeStudioCard::title {
    color: #ffe2a1;
    padding: 0 6px;
}
QComboBox#themeStudioCombo {
    border: 1px solid #7a5a2d;
    background-color: #241a1f;
}
QCheckBox#themeStudioSeedLock {
    color: #eadcc8;
}
QPushButton#themeStudioRandomBtn {
    background-color: #5a9e62;
    color: #0f1a10;
    border: 1px solid #7bc084;
    font-weight: 700;
}
QPushButton#themeStudioRandomBtn:hover { background-color: #72b87a; }
QPushButton#themeStudioFavBtn {
    background-color: #3a4f74;
    color: #e8f0ff;
    border: 1px solid #5d7eb2;
    font-weight: 600;
}
QPushButton#themeStudioFavBtn:hover { background-color: #4a628c; }
QPushButton#themeStudioIOBtn {
    background-color: #3c3f56;
    color: #eceff6;
    border: 1px solid #5f668a;
}
QPushButton#themeStudioIOBtn:hover { background-color: #4a5070; }
QPushButton#themeStudioZoneSwatch {
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton#themeStudioZoneReset {
    background-color: #463544;
    color: #f0ebe4;
    border: 1px solid #735364;
}
QPushButton#themeStudioZoneReset:hover {
    background-color: #574255;
}
QLabel#themeStudioTip {
    color: #d4ccc0;
    font-size: 9pt;
}
QLabel#tabHint { color: #f0ebe4; font-size: 10pt; padding-bottom: 4px; }
QLabel#tabNote { color: #d4ccc0; font-size: 9pt; }
QListWidget#presetList {
    background-color: #1e181c;
    border: 1px solid #7a5a2d;
    border-radius: 4px;
    outline: none;
}
QListWidget#presetList::item {
    padding: 6px 10px;
    color: #f0ebe4;
}
QListWidget#presetList::item:selected {
    background-color: #6b3a4a;
    color: #fff8ec;
    font-weight: 600;
}
QListWidget#presetList::item:hover:!selected {
    background-color: #4a3540;
}
QDialog#UiEditorDialog QListWidget#uiEditorList {
    background-color: #1e181c;
    border: 1px solid #7a5a2d;
    border-radius: 6px;
    color: #f0ebe4;
    font-size: 10pt;
    outline: none;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item {
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 28px;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item:selected {
    background-color: #6b3a4a;
    color: #fff8ec;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item:hover:!selected {
    background-color: #4a3540;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item:alternate {
    background-color: rgba(36, 28, 32, 0.45);
}
QCheckBox { color: #f0ebe4; }
QRadioButton { color: #f0ebe4; }
QFrame#iosCard {
    background-color: rgba(68, 44, 52, 0.55);
    border: 1px solid #7a5a2d;
    border-radius: 12px;
}
QToolButton#iosCardToggle {
    color: #f4f0ea;
    font-weight: 600;
    text-align: left;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    background-color: rgba(36, 26, 31, 0.65);
}
QToolButton#iosCardToggle:hover {
    background-color: rgba(95, 54, 67, 0.65);
}
QWidget#iosCardBody {
    background: transparent;
}
"""

_TAB_PAGE_LIGHT = """
QTabWidget { background-color: #e8e4de; }
QTabWidget::pane {
    background-color: #f0ece6;
    border: 1px solid #a09888;
    top: -1px;
}
QTabBar { background-color: #ddd8d0; }
QTabBar::tab {
    background-color: #d0cbc4;
    color: #1a1a1a;
    padding: 6px 12px;
    margin-right: 8px;
}
QTabBar::tab:selected { background-color: #f0ece6; color: #1a1a1a; font-weight: 600; }
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport,
QWidget#toolTabScrollHost {
    background-color: #f0ece6;
    color: #1a1a1a;
}
QWidget#toolTabScrollHost[themeStudio="true"] {
    background-color: #ece4d6;
    border: 1px solid #c8a668;
    border-radius: 8px;
    padding: 6px;
}
QLabel#themeStudioHint {
    color: #3a1f13;
    font-size: 10pt;
    font-weight: 600;
}
QGroupBox#themeStudioCard {
    background-color: rgba(239, 227, 206, 0.75);
    border: 1px solid #c2964a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px;
}
QGroupBox#themeStudioCard::title {
    color: #4a202a;
    padding: 0 6px;
}
QComboBox#themeStudioCombo {
    border: 1px solid #b28a42;
    background-color: #f7f1e6;
}
QCheckBox#themeStudioSeedLock {
    color: #4a202a;
}
QPushButton#themeStudioRandomBtn {
    background-color: #67a873;
    color: #0f1a10;
    border: 1px solid #4b8e58;
    font-weight: 700;
}
QPushButton#themeStudioRandomBtn:hover { background-color: #7cbd87; }
QPushButton#themeStudioFavBtn {
    background-color: #7a89a6;
    color: #f7fbff;
    border: 1px solid #5b6b8a;
    font-weight: 600;
}
QPushButton#themeStudioFavBtn:hover { background-color: #8f9dbc; }
QPushButton#themeStudioIOBtn {
    background-color: #c8d1e2;
    color: #2a3040;
    border: 1px solid #8a98b4;
}
QPushButton#themeStudioIOBtn:hover { background-color: #d5dceb; }
QPushButton#themeStudioZoneSwatch {
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton#themeStudioZoneReset {
    background-color: #d6c7b0;
    color: #3a3028;
    border: 1px solid #ad9470;
}
QPushButton#themeStudioZoneReset:hover {
    background-color: #e4d6c0;
}
QLabel#themeStudioTip {
    color: #5a5048;
    font-size: 9pt;
}
QLabel#tabHint { color: #1a1a1a; font-size: 10pt; padding-bottom: 4px; }
QLabel#tabNote { color: #3a3028; font-size: 9pt; }
QListWidget#presetList {
    background-color: #f5f2ec;
    border: 1px solid #a09888;
    border-radius: 4px;
    outline: none;
}
QListWidget#presetList::item {
    padding: 6px 10px;
    color: #1a1a1a;
}
QListWidget#presetList::item:selected {
    background-color: #d4af37;
    color: #3a1f13;
    font-weight: 600;
}
QListWidget#presetList::item:hover:!selected {
    background-color: #e8e0d4;
}
QDialog#UiEditorDialog QListWidget#uiEditorList {
    background-color: #f5f2ec;
    border: 1px solid #a09888;
    border-radius: 6px;
    color: #1a1a1a;
    font-size: 10pt;
    outline: none;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item {
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 28px;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item:selected {
    background-color: #d4af37;
    color: #3a1f13;
    font-weight: 600;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item:hover:!selected {
    background-color: #e8e0d4;
}
QDialog#UiEditorDialog QListWidget#uiEditorList::item:alternate {
    background-color: #ece8e2;
}
QCheckBox { color: #1a1a1a; }
QRadioButton { color: #1a1a1a; }
QFrame#iosCard {
    background-color: #f7f1e6;
    border: 1px solid #b28a42;
    border-radius: 12px;
}
QToolButton#iosCardToggle {
    color: #4a202a;
    font-weight: 600;
    text-align: left;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    background-color: #eadcc3;
}
QToolButton#iosCardToggle:hover {
    background-color: #dfcfaf;
}
QWidget#iosCardBody {
    background: transparent;
}
"""

BRIDGE_STYLESHEET_STANDARD = (
    """
QWidget#BridgeRoot {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2f2329, stop:1 #241a1f);
    color: #f4f0ea;
    font-family: "Segoe UI", sans-serif;
    font-size: 10.5pt;
}
QLabel { color: #f4f0ea; }
QSplitter::handle { background-color: #57333f; }
QSplitter::handle:hover { background-color: #7a4a58; }
QSplitter#connectPanelSplitter::handle:vertical,
QSplitter#diagCardsSplitter::handle:vertical,
QSplitter#fieldMainSplitter::handle:vertical {
    height: 10px;
    margin: 3px 12px;
}
QSplitter#connectPanelSplitter::handle:vertical:hover,
QSplitter#diagCardsSplitter::handle:vertical:hover,
QSplitter#fieldMainSplitter::handle:vertical:hover {
    background-color: #c9a227;
}
QWidget#surveyMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a2a31, stop:1 #2a1d22);
    border-bottom: 1px solid #7a5a2d;
    min-height: 0;
    max-height: 40px;
}
QWidget#surveyTopBarTrack {
    min-width: 0;
}
QWidget#surveyMenuBar QToolButton {
    background: transparent;
    border: none;
    padding: 2px 10px;
    color: #f6eee0;
    font-weight: 600;
}
QWidget#surveyMenuBar QToolButton:hover { background-color: #5f3643; }
QWidget#surveyMenuBar QToolButton::menu-indicator { image: none; width: 0; }
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {
    font-weight: 500; font-size: 9pt; padding: 2px 7px;
}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {
    background-color: #5f3643; color: #ffe2a1;
}
QFrame#surveyBarSep { color: #7a5a2d; max-height: 18px; margin: 0 4px; }
QFrame#topBarChip {
    border: 1px solid #7a5a2d;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.04);
    margin: 1px 0;
}
QFrame#topBarChip:hover { border-color: #c9a227; background-color: rgba(201, 162, 39, 0.08); }
QFrame#topBarChip[dragging="true"] {
    border-color: #d4af37;
    background-color: rgba(212, 175, 55, 0.14);
}
QFrame#topBarChip[compact="true"] {
    min-width: 36px;
}
QFrame#topBarChip[compact="true"] QToolButton {
    font-weight: 700;
    font-size: 10pt;
    padding: 0 4px;
    min-width: 0;
}
QLabel#topBarDragGrip {
    color: #7a6a5a;
    font-size: 7pt;
    padding: 0;
    min-width: 12px;
    max-width: 14px;
}
QWidget#topBarResizeEdge {
    background: transparent;
    min-width: 5px;
    max-width: 5px;
}
QWidget#topBarResizeEdge:hover {
    background-color: rgba(212, 175, 55, 0.35);
}
QFrame#topBarDropLine { background-color: #d4af37; border: none; max-width: 2px; }
QWidget#surveyMenuBar QFrame#topBarChip QToolButton {
    border: none;
    padding: 2px 6px;
    margin: 0;
    min-width: 0;
    qproperty-toolButtonStyle: ToolButtonTextOnly;
}
QWidget#surveyMenuBar QFrame#topBarChip QLabel#topBarDragGrip:hover {
    color: #d4af37;
}
QMenu { background-color: #3a2a31; color: #f4f0ea; border: 1px solid #7a5a2d; }
QMenu::item:selected { background-color: #5f3643; color: #f8f4ec; }
QLabel#appTitle { font-size: 15pt; font-weight: 600; color: #f8f4ec; }
QFrame#statusBanner {
    border-radius: 8px; padding: 10px 12px;
    border: 1px solid #7a5a2d; background-color: #3a2a31;
}
QFrame#statusBanner[state="running"] { background-color: #4c2d37; border-color: #d4af37; }
QFrame#statusBanner[state="starting"] { background-color: #4a3a24; border-color: #d4af37; }
QFrame#statusBanner[state="failed"] { background-color: #4a3038; border-color: #d08080; }
QLabel#statusBannerText { font-size: 12pt; font-weight: 600; color: #faf6f0; }
QPushButton#pathBench, QPushButton#pathProduction {
    text-align: left; padding: 12px 14px; border-radius: 8px;
    border: 2px solid #7a5a2d; background-color: #4a2f39; font-weight: 600; color: #f5ead8;
}
QPushButton#pathBench[active="true"], QPushButton#pathProduction[active="true"] {
    border-color: #d4af37; background-color: #6b3a4a;
}
QPushButton#btnStart {
    background-color: #d4af37; border: 1px solid #f1d483; border-radius: 8px;
    font-weight: 700; min-height: 44px; color: #3a1f13;
}
QPushButton#btnStop {
    background-color: #6b3643; border: 1px solid #b47a88; border-radius: 8px;
    font-weight: 600; min-height: 44px; color: #f6eee0;
}
QPushButton#btnStart:hover { background-color: #e0be56; border-color: #ffe7b0; }
QPushButton#btnStart:pressed { background-color: #bf9928; }
QPushButton#btnStop:hover { background-color: #7b4150; border-color: #c78f9b; }
QPlainTextEdit {
    background-color: #1e181c; color: #ece6dc; border: 1px solid #7a5a2d;
    font-family: Consolas, monospace; font-size: 9.5pt;
}
QPlainTextEdit#sendEdit {
    background-color: #1e181c; color: #ece6dc; border: 1px solid #8d6a34;
    border-radius: 4px; font-family: Consolas, monospace; font-size: 9.5pt;
}
QStatusBar { background: #2a1d22; color: #e0d6c8; border-top: 1px solid #7a5a2d; font-weight: 500; }
QStatusBar QLabel { color: #f4f0ea; }
QStatusBar::item {
    border: 1px solid #5a5048;
    border-radius: 4px;
    background-color: #3a3238;
    padding: 1px 6px;
}
QStatusBar QLabel {
    padding: 0;
    margin: 0;
}
QGroupBox {
    border: 1px solid #7a5a2d; border-radius: 6px; margin-top: 12px;
    padding: 10px; color: #f4f0ea;
}
QGroupBox::title { color: #e8dcc8; font-weight: 600; }
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a3d4c, stop:1 #4a2a36);
    color: #f4f0ea;
    border: 1px solid #8d6a34; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background-color: #6b3a4a; }
QPushButton:pressed { background-color: #3a2a31; }
QComboBox, QLineEdit, QSpinBox {
    background-color: #2a1d22; color: #f4f0ea; border: 1px solid #8d6a34; padding: 4px 6px;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border: 1px solid #c9a227; }
"""
    + _CALLOUT_DARK
    + _TAB_PAGE_DARK
    + _ROUND_CONNECT_ROWS_DARK
    + _APPLE_ROUND_DARK
)

BRIDGE_STYLESHEET_MINIMAL = (
    """
QWidget#BridgeRoot {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f7f1e6, stop:1 #e8e4de);
    color: #1a1a1a;
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QLabel { color: #1a1a1a; }
QSplitter::handle { background-color: #ccb993; }
QSplitter::handle:hover { background-color: #b79b69; }
QWidget#surveyMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e7dcc9, stop:1 #ddd8d0);
    border-bottom: 1px solid #b28a42;
    min-height: 0;
    max-height: 40px;
}
QWidget#surveyMenuBar QToolButton {
    background: transparent;
    border: none;
    padding: 2px 10px;
    color: #4a202a;
    font-weight: 600;
}
QWidget#surveyMenuBar QToolButton:hover { background-color: #d9c6a1; }
QWidget#surveyMenuBar QToolButton::menu-indicator { image: none; width: 0; }
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {
    font-weight: 500; font-size: 9pt; padding: 2px 7px;
}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {
    background-color: #d9c6a1; color: #4a202a;
}
QFrame#surveyBarSep { color: #b28a42; max-height: 18px; margin: 0 4px; }
QFrame#topBarChip {
    border: 1px solid #b28a42;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.35);
    margin: 1px 0;
}
QFrame#topBarChip:hover { border-color: #8a6a30; background-color: rgba(255, 255, 255, 0.55); }
QFrame#topBarChip[dragging="true"] {
    border-color: #8a6a30;
    background-color: rgba(212, 175, 55, 0.22);
}
QFrame#topBarChip[compact="true"] {
    min-width: 36px;
}
QFrame#topBarChip[compact="true"] QToolButton {
    font-weight: 700;
    font-size: 10pt;
    padding: 0 4px;
    min-width: 0;
}
QLabel#topBarDragGrip {
    color: #8a7a68;
    font-size: 7pt;
    padding: 0;
    min-width: 12px;
    max-width: 14px;
}
QFrame#topBarDropLine { background-color: #8a6a30; border: none; max-width: 2px; }
QWidget#surveyMenuBar QFrame#topBarChip QToolButton {
    border: none;
    padding: 2px 6px;
    margin: 0;
    min-width: 0;
    qproperty-toolButtonStyle: ToolButtonTextOnly;
}
QWidget#surveyMenuBar QFrame#topBarChip QLabel#topBarDragGrip:hover {
    color: #8a6a30;
}
QMenu { background-color: #f7f1e6; color: #4a202a; border: 1px solid #b28a42; }
QMenu::item:selected { background-color: #e3cfab; color: #4a202a; }
QLabel#statusLine { font-weight: 600; padding: 4px 0; }
QLabel#statusLine[state="running"] { color: #6b3643; }
QLabel#statusLine[state="starting"] { color: #7a5a2d; }
QLabel#statusLine[state="failed"] { color: #a02020; }
QLabel#statusLine[state="stopped"] { color: #5a2a33; }
QPlainTextEdit {
    background-color: #f5f2ec; color: #1a1a1a; border: 1px solid #a09888;
    font-family: Consolas, monospace; font-size: 9.5pt;
}
QPlainTextEdit#sendEdit {
    background-color: #f5f2ec; color: #1a1a1a; border: 1px solid #a09888;
    font-family: Consolas, monospace; font-size: 9.5pt;
}
QPushButton#btnStart { background-color: #d4af37; border: 1px solid #b28a42; min-height: 32px; font-weight: 700; color: #3a1f13; }
QPushButton#btnStop { background-color: #cfa0ab; border: 1px solid #9b6a73; min-height: 32px; color: #4a202a; }
QPushButton#btnStart:hover { background-color: #e0be56; }
QPushButton#btnStop:hover { background-color: #d9b0b8; }
QGroupBox { border: 1px solid #a09888; margin-top: 8px; padding: 8px; color: #1a1a1a; }
QGroupBox::title { color: #3a3028; font-weight: 600; }
QStatusBar { background: #ddd8d0; color: #1a1a1a; border-top: 1px solid #a09888; font-weight: 500; }
QStatusBar QLabel { color: #1a1a1a; }
QStatusBar::item {
    border: 1px solid #a09888;
    border-radius: 4px;
    background-color: #d0cbc4;
    padding: 2px 8px;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e8e0d4, stop:1 #d0cbc4);
    color: #1a1a1a; border: 1px solid #a09888; border-radius: 6px;
}
QPushButton:hover { background-color: #e3cfab; }
QComboBox, QLineEdit, QSpinBox {
    background-color: #f5f2ec; color: #1a1a1a; border: 1px solid #a09888; padding: 4px 6px;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border: 1px solid #6a5a40; }
"""
    + _CALLOUT_LIGHT
    + _TAB_PAGE_LIGHT
    + _ROUND_CONNECT_ROWS_LIGHT
    + _APPLE_ROUND_LIGHT
)

BRIDGE_STYLESHEET_LOGFIRST = (
    """
QWidget#BridgeRoot {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2f2329, stop:1 #241a1f);
    color: #ece6dc;
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QLabel { color: #f4f0ea; }
QSplitter::handle { background-color: #57333f; }
QSplitter::handle:hover { background-color: #7a4a58; }
QSplitter#connectPanelSplitter::handle:vertical,
QSplitter#diagCardsSplitter::handle:vertical,
QSplitter#fieldMainSplitter::handle:vertical {
    height: 10px;
    margin: 3px 12px;
}
QSplitter#connectPanelSplitter::handle:vertical:hover,
QSplitter#diagCardsSplitter::handle:vertical:hover,
QSplitter#fieldMainSplitter::handle:vertical:hover {
    background-color: #c9a227;
}
QWidget#surveyMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a2a31, stop:1 #2a1d22);
    border-bottom: 1px solid #7a5a2d;
    min-height: 0;
    max-height: 40px;
}
QWidget#surveyTopBarTrack {
    min-width: 0;
}
QWidget#surveyMenuBar QToolButton {
    background: transparent;
    border: none;
    padding: 2px 10px;
    color: #f6eee0;
    font-weight: 600;
}
QWidget#surveyMenuBar QToolButton:hover { background-color: #5f3643; }
QWidget#surveyMenuBar QToolButton::menu-indicator { image: none; width: 0; }
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {
    font-weight: 500; font-size: 9pt; padding: 2px 7px;
}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {
    background-color: #5f3643; color: #ffe2a1;
}
QFrame#surveyBarSep { color: #7a5a2d; max-height: 18px; margin: 0 4px; }
QFrame#topBarChip {
    border: 1px solid #7a5a2d;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.04);
    margin: 1px 0;
}
QFrame#topBarChip:hover { border-color: #c9a227; background-color: rgba(201, 162, 39, 0.08); }
QFrame#topBarChip[dragging="true"] {
    border-color: #d4af37;
    background-color: rgba(212, 175, 55, 0.14);
}
QFrame#topBarChip[compact="true"] {
    min-width: 36px;
}
QFrame#topBarChip[compact="true"] QToolButton {
    font-weight: 700;
    font-size: 10pt;
    padding: 0 4px;
    min-width: 0;
}
QLabel#topBarDragGrip {
    color: #7a6a5a;
    font-size: 7pt;
    padding: 0;
    min-width: 12px;
    max-width: 14px;
}
QWidget#topBarResizeEdge {
    background: transparent;
    min-width: 5px;
    max-width: 5px;
}
QWidget#topBarResizeEdge:hover {
    background-color: rgba(212, 175, 55, 0.35);
}
QFrame#topBarDropLine { background-color: #d4af37; border: none; max-width: 2px; }
QWidget#surveyMenuBar QFrame#topBarChip QToolButton {
    border: none;
    padding: 2px 6px;
    margin: 0;
    min-width: 0;
    qproperty-toolButtonStyle: ToolButtonTextOnly;
}
QWidget#surveyMenuBar QFrame#topBarChip QLabel#topBarDragGrip:hover {
    color: #d4af37;
}
QMenu { background-color: #3a2a31; color: #f6eee0; border: 1px solid #7a5a2d; }
QMenu::item:selected { background-color: #5f3643; color: #ffe2a1; }
QPlainTextEdit#logView {
    background-color: #161214; color: #ece6dc; border: none;
    font-family: Consolas, "Cascadia Mono", monospace; font-size: 9.5pt;
}
QFrame#controlStrip { background-color: #2f2329; border-top: 1px solid #7a5a2d; }
QLabel#intentHint[intentCompact="true"] {
    background-color: #352c32;
    border-left: 3px solid #c9a227;
    margin: 0 2px;
}
QPushButton#btnStart { background-color: #d4af37; border: 1px solid #f1d483; min-height: 28px; color: #3a1f13; font-weight: 700; }
QPushButton#btnStop { background-color: #6b3643; border: 1px solid #b47a88; min-height: 28px; color: #f6eee0; }
QPushButton#btnStart:hover { background-color: #e0be56; border-color: #ffe7b0; }
QPushButton#btnStop:hover { background-color: #7b4150; border-color: #c78f9b; }
QLabel#statusLine { font-weight: 600; color: #f4f0ea; padding: 0; }
QStatusBar { background: #2a1d22; color: #e0d6c8; border-top: 1px solid #7a5a2d; }
QStatusBar QLabel { color: #f4f0ea; }
QStatusBar::item {
    border: 1px solid #5a5048;
    border-radius: 4px;
    background-color: #3a3238;
    padding: 1px 6px;
}
QStatusBar QLabel {
    padding: 0;
    margin: 0;
}
QPlainTextEdit#sendEdit {
    background-color: #1b1418; color: #f2e7d2; border: 1px solid #7a5a2d;
    font-family: Consolas, monospace; font-size: 9pt;
}
QGroupBox { border: 1px solid #7a5a2d; color: #f4f0ea; }
QGroupBox::title { color: #e8dcc8; font-weight: 600; }
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a3d4c, stop:1 #4a2a36);
    color: #f4f0ea; border: 1px solid #8d6a34;
}
QPushButton:hover { background-color: #6b3a4a; }
QLineEdit { background-color: #2a1d22; color: #f4f0ea; border: 1px solid #8d6a34; }
QLineEdit:focus { border: 1px solid #c9a227; }
QCheckBox { color: #f0ebe4; }
"""
    + _CALLOUT_DARK
    + _TAB_PAGE_DARK
    + _ROUND_CONNECT_ROWS_DARK
    + _APPLE_ROUND_DARK
)

# First-run / dev UI layout picker (modal dialog)
UI_PICKER_STYLESHEET = """
QDialog#UiPickerDialog {
    background-color: #e8e4de;
    color: #1a1a1a;
}
QDialog#UiPickerDialog QLabel { color: #1a1a1a; }
QDialog#UiPickerDialog QLabel#pickerLayoutHint {
    color: #4a4a4a;
    font-size: 9pt;
}
QDialog#UiPickerDialog QRadioButton { color: #1a1a1a; font-weight: 600; }
QDialog#UiPickerDialog QCheckBox { color: #1a1a1a; }
QDialog#UiPickerDialog QToolButton#pickerDisclosure {
    background: transparent;
    border: none;
    color: #4a202a;
    font-size: 9pt;
    padding: 2px 4px;
    text-align: left;
}
QDialog#UiPickerDialog QToolButton#pickerDisclosure:hover {
    color: #1a1a1a;
    background-color: #ddd5c8;
}
QDialog#UiPickerDialog QDialogButtonBox QPushButton {
    background-color: #f0ebe3;
    color: #1a1a1a;
    border: 1px solid #6b3643;
    border-radius: 4px;
    padding: 6px 18px;
    min-width: 76px;
    font-weight: 600;
}
QDialog#UiPickerDialog QDialogButtonBox QPushButton:hover {
    background-color: #e3cfab;
}
QDialog#UiPickerDialog QDialogButtonBox QPushButton#pickerBtnOk {
    background-color: #6b3643;
    color: #f8f4ec;
    border: 1px solid #4a202a;
}
QDialog#UiPickerDialog QDialogButtonBox QPushButton#pickerBtnOk:hover {
    background-color: #7b4150;
}
QDialog#UiPickerDialog QDialogButtonBox QPushButton#pickerBtnCancel {
    background-color: #d8d0c4;
    color: #1a1a1a;
}

QDialog#SurveyHudLayoutDialog {
    background-color: #241a1f;
    color: #f6eee0;
}
QFrame#layoutDialogHeader {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6b3643, stop:1 #241a1f);
    border-radius: 0px;
    border-bottom: 1px solid #7a5a2d;
}
QLabel#layoutDialogTitle {
    font-size: 14pt;
    font-weight: bold;
    color: #ffe2a1;
}
QLabel#layoutDialogSub {
    font-size: 9pt;
    color: #ead9b7;
}
QDialog#SurveyHudLayoutDialog QGroupBox {
    border: 1px solid #7a5a2d;
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px;
    color: #f6eee0;
}
QDialog#SurveyHudLayoutDialog QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    color: #d4af37;
    top: -8px;
    left: 8px;
}
QDialog#SurveyHudLayoutDialog QCheckBox,
QDialog#SurveyHudLayoutDialog QLabel {
    color: #eadcc8;
}
QDialog#SurveyHudLayoutDialog QPushButton {
    background-color: #5a3240;
    color: #f6eee0;
    border: 1px solid #8d6a34;
    border-radius: 6px;
    padding: 6px 12px;
}
QDialog#SurveyHudLayoutDialog QPushButton:hover { background-color: #6a3d4c; }
"""

# Presenter product demo (teleprompter-style)
PRODUCT_DEMO_STYLESHEET = """
QDialog#ProductDemoDialog {
    background-color: #1e1619;
    color: #f6eee0;
}
QDialog#ProductDemoDialog QLabel#demoTitleBar {
    color: #e8dcc8;
    font-size: 11pt;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QDialog#ProductDemoDialog QLabel#demoPhaseChip {
    color: #c9b896;
    font-size: 9pt;
    font-weight: 600;
    padding: 2px 8px;
    background-color: rgba(107, 54, 67, 0.55);
    border-radius: 10px;
}
QDialog#ProductDemoDialog QLabel#demoStepIndex {
    color: #a89880;
    font-size: 10pt;
    font-weight: 600;
}
QDialog#ProductDemoDialog QLabel#demoStepTitle {
    color: #ffe2a1;
    font-size: 20pt;
    font-weight: 700;
}
QDialog#ProductDemoDialog QLabel#demoCountdown {
    color: #d4c4a0;
    font-size: 11pt;
    font-weight: 600;
}
QDialog#ProductDemoDialog QLabel#demoCue {
    color: #9fd4a8;
    font-size: 12pt;
    font-weight: 600;
}
QDialog#ProductDemoDialog QTextEdit#demoNarration {
    color: #e8e0d4;
    font-size: 13pt;
    background: transparent;
}
QDialog#ProductDemoDialog QProgressBar#demoProgress {
    border: 1px solid #4a3038;
    border-radius: 4px;
    background-color: #2a1d22;
    text-align: center;
    color: #e8dcc8;
    min-height: 14px;
    max-height: 14px;
}
QDialog#ProductDemoDialog QProgressBar#demoProgress::chunk {
    background-color: #6b3643;
    border-radius: 3px;
}
QDialog#ProductDemoDialog QListWidget#demoStepList {
    background-color: #241a1f;
    border: 1px solid #4a3038;
    border-radius: 6px;
    color: #d8cfc0;
    font-size: 10pt;
    outline: none;
}
QDialog#ProductDemoDialog QListWidget#demoStepList::item {
    padding: 5px 8px;
    border-radius: 3px;
}
QDialog#ProductDemoDialog QListWidget#demoStepList::item:selected {
    background-color: #6b3643;
    color: #fff8ee;
}
QDialog#ProductDemoDialog QListWidget#demoStepList::item:hover:!selected {
    background-color: rgba(107, 54, 67, 0.35);
}
QDialog#ProductDemoDialog QFrame#demoPresentCard {
    background-color: #2a1d22;
    border: 1px solid #5a3844;
    border-radius: 8px;
}
QDialog#ProductDemoDialog QPushButton#demoBtnStop {
    background-color: #6b3643;
    color: #f8f4ec;
    border: 1px solid #4a202a;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QDialog#ProductDemoDialog QPushButton#demoBtnStop:hover {
    background-color: #7b4150;
}
QDialog#ProductDemoDialog QPushButton#demoBtnNext {
    background-color: #5a9e62;
    color: #0f1a10;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 11pt;
    font-weight: 700;
    min-height: 20px;
}
QDialog#ProductDemoDialog QPushButton#demoBtnNext:hover {
    background-color: #72b87a;
}
QDialog#ProductDemoDialog QPushButton#demoBtnNext:disabled {
    background-color: #3d5240;
    color: #8a9a8c;
}
QDialog#ProductDemoDialog QPushButton#demoBtnPrev,
QDialog#ProductDemoDialog QPushButton#demoBtnStep,
QDialog#ProductDemoDialog QPushButton#demoBtnRunAuto,
QDialog#ProductDemoDialog QPushButton#demoBtnClose {
    background-color: transparent;
    color: #d8cfc0;
    border: 1px solid #5a3844;
    border-radius: 6px;
    padding: 8px 14px;
}
QDialog#ProductDemoDialog QPushButton#demoBtnPrev:hover,
QDialog#ProductDemoDialog QPushButton#demoBtnStep:hover,
QDialog#ProductDemoDialog QPushButton#demoBtnRunAuto:hover,
QDialog#ProductDemoDialog QPushButton#demoBtnClose:hover {
    background-color: rgba(107, 54, 67, 0.4);
    color: #fff8ee;
}
QDialog#ProductDemoDialog QPushButton#demoBtnRun {
    background-color: transparent;
    color: #c9b896;
    border: 1px dashed #5a3844;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 10pt;
}
QDialog#ProductDemoDialog QPushButton#demoBtnRun:hover {
    background-color: rgba(107, 54, 67, 0.35);
    color: #fff8ee;
    border-style: solid;
}
QDialog#ProductDemoDialog QCheckBox#demoPinTop {
    color: #c9b896;
    spacing: 6px;
}
"""

# Detached stats window (no BridgeRoot — applied in SurveyStatsPopout)
SURVEY_STATS_POPOUT_STYLESHEET = """
QWidget#SurveyStatsPopout {
    background-color: #241a1f;
    color: #f6eee0;
    font-family: "Segoe UI", sans-serif;
}
QWidget#surveyHudChromeBar {
    background-color: #241a1f;
    border: none;
}
QToolButton#surveyHudCapBtn {
    color: #e1cfac;
    background: transparent;
    border: none;
    font-family: "Segoe UI", sans-serif;
    font-size: 11pt;
    padding: 0px;
}
QToolButton#surveyHudCapBtn:hover {
    color: #ffe2a1;
    background-color: rgba(255, 226, 161, 0.08);
}
QWidget#surveyHudSectionsHost { background: transparent; }
QLabel#surveyHudWindowTitle {
    color: #e5d2b0;
    font-size: 9pt;
    font-weight: 600;
}
QFrame#surveyHudSection {
    background-color: rgba(78, 46, 56, 0.62);
    border-radius: 3px;
    border: none;
}
QFrame#surveyHudSection[collapsed="true"] {
    background-color: rgba(78, 46, 56, 0.45);
    border-radius: 2px;
}
QFrame#surveyHudSection[collapsed="true"] QToolButton#surveyHudSectionToggle {
    padding: 0px;
    margin: 0px;
    font-size: 8pt;
}
QLabel#surveyHudSectionHead {
    color: #e8dcc8;
    font-size: 8pt;
    font-weight: 600;
    padding-bottom: 0px;
}
QToolButton#surveyHudSectionToggle {
    color: #f4f0ea;
    font-size: 9pt;
    font-weight: 600;
    padding: 0px 2px;
    border: none;
    text-align: left;
}
QToolButton#surveyHudSectionToggle:hover {
    color: #ffe2a1;
    background-color: rgba(212, 175, 55, 0.15);
    border-radius: 2px;
}
QPushButton#surveyHudLayoutBtn {
    background-color: #5a3240;
    color: #f6eee0;
    border: 1px solid rgba(141, 106, 52, 0.8);
    border-radius: 2px;
    padding: 1px 6px;
    min-height: 0px;
}
QPushButton#surveyHudLayoutBtn:hover { background-color: #6a3d4c; }
QLabel#surveyHudDragHandle {
    color: #a9854e;
    font-size: 9pt;
    font-weight: bold;
}
QLabel#surveyHudDragHandle:hover { color: #ffd68f; }
QCheckBox#surveyHudRow,
QCheckBox#surveyHudPin,
QCheckBox#surveyHudSub,
QCheckBox#surveyHudLog,
QCheckBox#surveyHudLock {
    color: #d9c5a4;
    font-size: 8pt;
}
QFrame#surveyHudMetric, QFrame#surveyHudMetricHero {
    background-color: rgba(45, 30, 36, 0.52);
    border: none;
    border-radius: 3px;
}
QFrame#surveyHudMetric:hover, QFrame#surveyHudMetricHero:hover {
    background-color: rgba(212, 175, 55, 0.16);
}
QFrame#surveyHudMetric[alert="true"], QFrame#surveyHudMetricHero[alert="true"] {
    background-color: rgba(180, 90, 100, 0.22);
}
QLabel#surveyHudMetricTitle {
    color: #f0ebe4;
    font-size: 9pt;
    font-weight: 600;
}
QLabel#surveyHudMetricSub {
    color: #d0c4b0;
    font-size: 7pt;
}
QLabel#surveyHudMetricValueHero {
    color: #faf6f0;
    font-size: 22pt;
    font-weight: bold;
    font-family: Consolas, "Cascadia Mono", monospace;
}
QLabel#surveyHudMetricValue {
    color: #f4f0ea;
    font-size: 14pt;
    font-weight: bold;
    font-family: Consolas, "Cascadia Mono", monospace;
}
QFrame#surveyHudFootPanel,
QFrame#surveyHudNmeaPanel {
    background-color: rgba(39, 25, 31, 0.52);
    border-radius: 2px;
    border: none;
}
QPlainTextEdit#surveyHudNmeaLog {
    background-color: rgba(26, 18, 22, 0.95);
    color: #ece6dc;
    border: 1px solid rgba(141, 106, 52, 0.75);
    border-radius: 2px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 8pt;
}
QLabel#surveyHudFootLine {
    color: #d9c5a4;
    font-size: 8pt;
}
QCheckBox#surveyHudPin::indicator {
    width: 12px;
    height: 12px;
}
"""

THEME_LABELS = {
    "maroon_classic": "Maroon & Gold",
    "ocean_survey": "Ocean Survey",
    "field_slate": "Field Slate",
    "forest_night": "Forest Night",
    "sunset_copper": "Sunset Copper",
    "random_current": "Randomized (current)",
    "random_favorite": "Favorite random",
}


def bridge_stylesheet(ui_mode: str, theme_id: str) -> str:
    from ui.theme_choice import _normalize_theme_id
    from ui.theme_palette import apply_theme_colors

    theme_id = _normalize_theme_id(theme_id)
    base = {
        "standard": BRIDGE_STYLESHEET_STANDARD,
        "minimal": BRIDGE_STYLESHEET_MINIMAL,
        "logfirst": BRIDGE_STYLESHEET_LOGFIRST,
        "field": BRIDGE_STYLESHEET_LOGFIRST,
    }.get(ui_mode, BRIDGE_STYLESHEET_STANDARD)
    return apply_theme_colors(base, theme_id)


def hud_stylesheet(theme_id: str) -> str:
    from ui.theme_choice import _normalize_theme_id
    from ui.theme_palette import apply_theme_colors

    return apply_theme_colors(SURVEY_STATS_POPOUT_STYLESHEET, _normalize_theme_id(theme_id))
