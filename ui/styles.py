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

_CONNECT_SHARED_DARK = """
QWidget#connectPanelHost,
QWidget#connectSectionBody {
    background: transparent;
    color: #f6eee0;
}
QScrollArea#connectSectionScroll,
QWidget#connectSectionScrollViewport {
    background: transparent;
}
QWidget#connectSerialNetRow QGroupBox#connectGroupBox {
    margin-top: 8px;
}
QGroupBox#connectGroupBox {
    background-color: rgba(36, 26, 31, 0.55);
    border: 1px solid #6f8d63;
    border-radius: 10px;
    margin-top: 12px;
    padding: 10px;
    color: #f4f0ea;
}
QGroupBox#connectGroupBox::title {
    color: #d8e8d0;
    font-weight: 600;
}
QSpinBox#webPortSpin {
    min-height: 32px;
    min-width: 152px;
    padding: 4px 10px;
    background-color: #2a1d22;
    border: 1px solid #4a5568;
    border-radius: 8px;
}
QSpinBox#webPortSpin[portLocked="true"] {
    color: #b8b0a8;
}
QFrame#phoneDashboardCard {
    background-color: rgba(32, 28, 34, 0.92);
    border: 1px solid #4a5568;
    border-radius: 10px;
}
QLabel#phoneCardTitle {
    color: #e8e4de;
    font-size: 10pt;
    font-weight: 600;
    padding-bottom: 2px;
}
QLabel#webPortStatus {
    color: #9aa3b0;
    font-size: 9pt;
    min-width: 72px;
}
QLabel#webPortStatus[statusKind="open"] {
    color: #7eb8e8;
}
QLabel#webListenStatus {
    color: #8a919c;
    font-size: 9pt;
    padding: 0;
    min-height: 0;
}
QFrame#phoneDashboardCard QCheckBox {
    margin: 0;
    padding: 0;
    spacing: 6px;
}
QToolButton#webPortLockBtn {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 2px;
    border: 1px solid #4a5568;
    border-radius: 8px;
    background-color: #322830;
}
QToolButton#webPortLockBtn:hover {
    background-color: #3d4858;
    border-color: #5b8fd4;
}
QToolButton#webPortLockBtn:checked {
    background-color: rgba(91, 143, 212, 0.22);
    border-color: #5b8fd4;
}
QToolButton#webInlineBtn {
    padding: 2px;
    border: 1px solid #4a5568;
    border-radius: 0;
    background-color: #322830;
}
QToolButton#webInlineBtn:hover {
    background-color: #3d4858;
    border-color: #5b8fd4;
}
QToolButton#webInlineBtn:pressed {
    background-color: #2a2430;
}
QToolButton#webInlineActionBar QToolButton#webInlineBtn:first-child {
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
}
QToolButton#webInlineActionBar QToolButton#webInlineBtn:last-child {
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QPushButton#webPrimaryBtn {
    background-color: #3d5a80;
    color: #f4f8fc;
    border: 1px solid #5b8fd4;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
    min-height: 30px;
}
QPushButton#webPrimaryBtn:hover {
    background-color: #4a6f9c;
    border-color: #7eb8e8;
}
QPushButton#webPrimaryBtn:pressed {
    background-color: #2f4666;
}
QLabel#webTokenQr {
    background-color: #1e181c;
    border: 1px solid #4a5568;
    border-radius: 10px;
}
QComboBox#connectComCombo,
QComboBox#connectBaudCombo {
    min-height: 30px;
    padding: 4px 28px 4px 10px;
}
QComboBox#connectComCombo::drop-down,
QComboBox#connectBaudCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
}
"""
_CONNECT_ROW_VARIANTS_DARK = """
/* Default (pill) when connectRowStyle is not yet set on first paint */
QWidget#connectPanelHost QWidget#connectPanelRow {
    border: 1px solid #7f9a73;
    border-radius: 14px;
    background-color: rgba(24, 34, 26, 0.52);
    margin: 5px 6px;
    padding: 2px;
}
QWidget#connectPanelHost QToolButton#connectPanelDisclosure {
    border: 1px solid #6f8d63;
    border-radius: 12px;
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(62, 88, 64, 0.92), stop:1 rgba(48, 68, 50, 0.9));
    color: #f2f6ed;
    font-weight: 600;
    text-align: left;
    padding: 8px 13px;
    margin: 4px 7px;
}
QWidget#connectPanelHost QToolButton#connectPanelDisclosure:hover {
    border-color: #9fc092;
    background-color: rgba(70, 100, 74, 0.95);
}
QWidget#connectPanelHost QToolButton#connectPanelDisclosure:checked {
    border-color: #b8d4ae;
    background-color: rgba(96, 139, 102, 0.95);
    color: #f7fbf4;
}
QWidget#connectPanelHost[connectRowStyle="pill"] QWidget#connectPanelRow {
    border: 1px solid #7f9a73;
    border-radius: 14px;
    background-color: rgba(24, 34, 26, 0.52);
    margin: 5px 6px;
    padding: 2px;
}
QWidget#connectPanelHost[connectRowStyle="pill"] QToolButton#connectPanelDisclosure {
    border: 1px solid #6f8d63;
    border-radius: 12px;
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(62, 88, 64, 0.92), stop:1 rgba(48, 68, 50, 0.9));
    color: #f2f6ed;
    font-weight: 600;
    text-align: left;
    padding: 8px 13px;
    margin: 4px 7px;
}
QWidget#connectPanelHost[connectRowStyle="pill"] QToolButton#connectPanelDisclosure:hover {
    border-color: #9fc092;
    background-color: rgba(70, 100, 74, 0.95);
}
QWidget#connectPanelHost[connectRowStyle="pill"] QToolButton#connectPanelDisclosure:checked {
    border-color: #b8d4ae;
    background-color: rgba(96, 139, 102, 0.95);
    color: #f7fbf4;
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QWidget#connectPanelRow {
    border: none;
    border-radius: 0;
    background: transparent;
    margin: 0;
    padding: 0;
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QToolButton#connectPanelDisclosure {
    border: none;
    border-bottom: 1px solid rgba(127, 154, 115, 0.38);
    border-radius: 0;
    background-color: rgba(48, 68, 50, 0.55);
    color: #f2f6ed;
    font-weight: 600;
    text-align: left;
    padding: 10px 10px;
    margin: 0;
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(70, 100, 74, 0.72);
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QToolButton#connectPanelDisclosure:checked {
    background-color: rgba(62, 88, 64, 0.85);
    color: #f7fbf4;
}
QWidget#connectPanelHost[connectRowStyle="outline"] QWidget#connectPanelRow {
    border: none;
    background: transparent;
    margin: 2px 0;
    padding: 0;
}
QWidget#connectPanelHost[connectRowStyle="outline"] QToolButton#connectPanelDisclosure {
    border: 1px solid rgba(127, 154, 115, 0.45);
    border-radius: 8px;
    background-color: transparent;
    color: #f2f6ed;
    font-weight: 600;
    text-align: left;
    padding: 9px 12px;
    margin: 3px 5px;
}
QWidget#connectPanelHost[connectRowStyle="outline"] QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(48, 68, 50, 0.45);
}
QWidget#connectPanelHost[connectRowStyle="outline"] QToolButton#connectPanelDisclosure:checked {
    border-color: rgba(184, 212, 174, 0.75);
    background-color: rgba(62, 88, 64, 0.55);
}
QWidget#connectPanelHost[connectRowStyle="accent"] QWidget#connectPanelRow {
    border: none;
    background: transparent;
    margin: 1px 0;
    padding: 0;
}
QWidget#connectPanelHost[connectRowStyle="accent"] QToolButton#connectPanelDisclosure {
    border: none;
    border-left: 4px solid #6f8d63;
    border-radius: 0;
    background-color: rgba(48, 68, 50, 0.42);
    color: #f2f6ed;
    font-weight: 600;
    text-align: left;
    padding: 10px 10px 10px 12px;
    margin: 2px 4px;
}
QWidget#connectPanelHost[connectRowStyle="accent"] QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(70, 100, 74, 0.62);
    border-left-color: #9fc092;
}
QWidget#connectPanelHost[connectRowStyle="accent"] QToolButton#connectPanelDisclosure:checked {
    background-color: rgba(62, 88, 64, 0.78);
    border-left-color: #b8d4ae;
    color: #f7fbf4;
}
"""

_CONNECT_SHARED_LIGHT = """
QWidget#connectPanelHost,
QWidget#connectSectionBody {
    background: transparent;
    color: #1a1a1a;
}
QScrollArea#connectSectionScroll,
QWidget#connectSectionScrollViewport {
    background: transparent;
}
QWidget#connectSerialNetRow QGroupBox#connectGroupBox {
    margin-top: 8px;
}
QGroupBox#connectGroupBox {
    background-color: rgba(238, 245, 234, 0.95);
    border: 1px solid #96aa86;
    border-radius: 10px;
    margin-top: 12px;
    padding: 10px;
    color: #1a1a1a;
}
QGroupBox#connectGroupBox::title {
    color: #253025;
    font-weight: 600;
}
QSpinBox#webPortSpin {
    min-height: 32px;
    min-width: 152px;
    padding: 4px 10px;
    background-color: #f8faf6;
    border: 1px solid #a8b4c4;
    border-radius: 8px;
}
QSpinBox#webPortSpin[portLocked="true"] {
    color: #6a6560;
}
QFrame#phoneDashboardCard {
    background-color: rgba(248, 250, 252, 0.98);
    border: 1px solid #c5ced8;
    border-radius: 10px;
}
QLabel#phoneCardTitle {
    color: #1e2834;
    font-size: 10pt;
    font-weight: 600;
    padding-bottom: 2px;
}
QLabel#webPortStatus {
    color: #5a6472;
    font-size: 9pt;
    min-width: 72px;
}
QLabel#webPortStatus[statusKind="open"] {
    color: #2f6fad;
}
QLabel#webListenStatus {
    color: #5a6472;
    font-size: 9pt;
    padding: 0;
    min-height: 0;
}
QFrame#phoneDashboardCard QCheckBox {
    margin: 0;
    padding: 0;
    spacing: 6px;
}
QToolButton#webPortLockBtn {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 2px;
    border: 1px solid #c5ced8;
    border-radius: 8px;
    background-color: #eef2f6;
}
QToolButton#webPortLockBtn:hover {
    background-color: #e0eaf4;
    border-color: #4a8fd4;
}
QToolButton#webPortLockBtn:checked {
    background-color: rgba(74, 143, 212, 0.14);
    border-color: #4a8fd4;
}
QToolButton#webInlineBtn {
    padding: 2px;
    border: 1px solid #c5ced8;
    border-radius: 0;
    background-color: #eef2f6;
}
QToolButton#webInlineBtn:hover {
    background-color: #e0eaf4;
    border-color: #4a8fd4;
    color: #1a3d66;
}
QToolButton#webInlineBtn:pressed {
    background-color: #d8e2ec;
}
QPushButton#webPrimaryBtn {
    background-color: #3d6ea8;
    color: #ffffff;
    border: 1px solid #4a8fd4;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
    min-height: 30px;
}
QPushButton#webPrimaryBtn:hover {
    background-color: #4a7fb8;
    border-color: #2f6fad;
}
QPushButton#webPrimaryBtn:pressed {
    background-color: #2f5580;
}
QLabel#webTokenQr {
    background-color: #ffffff;
    border: 1px solid #c5ced8;
    border-radius: 10px;
}
QComboBox#connectComCombo,
QComboBox#connectBaudCombo {
    min-height: 30px;
    padding: 4px 28px 4px 10px;
}
QComboBox#connectComCombo::drop-down,
QComboBox#connectBaudCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
}
"""
_CONNECT_ROW_VARIANTS_LIGHT = """
QWidget#connectPanelHost QWidget#connectPanelRow {
    border: 1px solid #a7b59c;
    border-radius: 14px;
    background-color: rgba(238, 245, 234, 0.95);
    margin: 5px 6px;
    padding: 2px;
}
QWidget#connectPanelHost QToolButton#connectPanelDisclosure {
    border: 1px solid #96aa86;
    border-radius: 12px;
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(228, 238, 220, 0.98), stop:1 rgba(214, 228, 204, 0.98));
    color: #253025;
    font-weight: 600;
    text-align: left;
    padding: 8px 13px;
    margin: 4px 7px;
}
QWidget#connectPanelHost QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(214, 228, 204, 0.98);
    border-color: #7f9a73;
}
QWidget#connectPanelHost QToolButton#connectPanelDisclosure:checked {
    background-color: rgba(198, 218, 188, 0.98);
    border-color: #6f8d63;
    color: #1d281d;
}
QWidget#connectPanelHost[connectRowStyle="pill"] QWidget#connectPanelRow {
    border: 1px solid #a7b59c;
    border-radius: 14px;
    background-color: rgba(238, 245, 234, 0.95);
    margin: 5px 6px;
    padding: 2px;
}
QWidget#connectPanelHost[connectRowStyle="pill"] QToolButton#connectPanelDisclosure {
    border: 1px solid #96aa86;
    border-radius: 12px;
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(228, 238, 220, 0.98), stop:1 rgba(214, 228, 204, 0.98));
    color: #253025;
    font-weight: 600;
    text-align: left;
    padding: 8px 13px;
    margin: 4px 7px;
}
QWidget#connectPanelHost[connectRowStyle="pill"] QToolButton#connectPanelDisclosure:hover {
    border-color: #7f9a70;
    background-color: rgba(206, 224, 196, 0.99);
}
QWidget#connectPanelHost[connectRowStyle="pill"] QToolButton#connectPanelDisclosure:checked {
    border-color: #67865a;
    background-color: rgba(190, 214, 178, 0.99);
    color: #1d281d;
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QWidget#connectPanelRow {
    border: none;
    border-radius: 0;
    background: transparent;
    margin: 0;
    padding: 0;
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QToolButton#connectPanelDisclosure {
    border: none;
    border-bottom: 1px solid rgba(151, 170, 134, 0.55);
    border-radius: 0;
    background-color: rgba(220, 232, 210, 0.85);
    color: #253025;
    font-weight: 600;
    text-align: left;
    padding: 10px 10px;
    margin: 0;
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(206, 224, 196, 0.95);
}
QWidget#connectPanelHost[connectRowStyle="seamless"] QToolButton#connectPanelDisclosure:checked {
    background-color: rgba(190, 214, 178, 0.98);
    color: #1d281d;
}
QWidget#connectPanelHost[connectRowStyle="outline"] QWidget#connectPanelRow {
    border: none;
    background: transparent;
    margin: 2px 0;
    padding: 0;
}
QWidget#connectPanelHost[connectRowStyle="outline"] QToolButton#connectPanelDisclosure {
    border: 1px solid rgba(151, 170, 134, 0.65);
    border-radius: 8px;
    background-color: transparent;
    color: #253025;
    font-weight: 600;
    text-align: left;
    padding: 9px 12px;
    margin: 3px 5px;
}
QWidget#connectPanelHost[connectRowStyle="outline"] QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(220, 232, 210, 0.75);
}
QWidget#connectPanelHost[connectRowStyle="outline"] QToolButton#connectPanelDisclosure:checked {
    border-color: #67865a;
    background-color: rgba(190, 214, 178, 0.65);
}
QWidget#connectPanelHost[connectRowStyle="accent"] QWidget#connectPanelRow {
    border: none;
    background: transparent;
    margin: 1px 0;
    padding: 0;
}
QWidget#connectPanelHost[connectRowStyle="accent"] QToolButton#connectPanelDisclosure {
    border: none;
    border-left: 4px solid #96aa86;
    border-radius: 0;
    background-color: rgba(220, 232, 210, 0.65);
    color: #253025;
    font-weight: 600;
    text-align: left;
    padding: 10px 10px 10px 12px;
    margin: 2px 4px;
}
QWidget#connectPanelHost[connectRowStyle="accent"] QToolButton#connectPanelDisclosure:hover {
    background-color: rgba(206, 224, 196, 0.9);
    border-left-color: #7f9a70;
}
QWidget#connectPanelHost[connectRowStyle="accent"] QToolButton#connectPanelDisclosure:checked {
    background-color: rgba(190, 214, 178, 0.95);
    border-left-color: #67865a;
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
QWidget#toolTabScrollHost,
QScrollArea#connectMainScroll,
QWidget#connectMainScrollViewport,
QWidget#connectMainScrollHost {
    background-color: #2f2329;
    color: #f6eee0;
}
QSplitter#connectPageSplitter::handle:horizontal {
    width: 6px;
    margin: 4px 0;
    background-color: rgba(127, 154, 115, 0.35);
}
QSplitter#connectPageSplitter::handle:horizontal:hover {
    background-color: rgba(201, 162, 39, 0.65);
}
QFrame#connectQrFloat {
    background-color: rgba(32, 40, 36, 0.92);
    border: 1px solid rgba(127, 154, 115, 0.45);
    border-radius: 8px;
}
QLabel#connectQrImage {
    background-color: #ffffff;
    padding: 4px;
    border: none;
}
QLabel#connectQrCaption {
    color: #d8e8d0;
    font-size: 9pt;
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
QDialog#UiEditorDialog QScrollArea#uiEditorScroll {
    background-color: #1e181c;
    border: 1px solid #7a5a2d;
    border-radius: 6px;
}
QDialog#UiEditorDialog QWidget#uiEditorListHost {
    background-color: #1e181c;
}
QDialog#UiEditorDialog QFrame#uiEditorRow {
    background-color: rgba(36, 28, 32, 0.55);
    border: 1px solid #57333f;
    border-radius: 6px;
}
QDialog#UiEditorDialog QLabel#uiEditorRowTitle {
    color: #f0ebe4;
    font-weight: 600;
}
QDialog#UiEditorDialog QToolButton {
    min-width: 28px;
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
QListWidget#toolsNavList {
    background-color: #1e181c;
    border: none;
    border-right: 1px solid #7a5a2d;
    outline: none;
}
QListWidget#toolsNavList::item {
    padding: 8px 10px;
    color: #f0ebe4;
    border-radius: 0;
}
QListWidget#toolsNavList::item:selected {
    background-color: #6b3a4a;
    color: #fff8ec;
    font-weight: 600;
}
QListWidget#toolsNavList::item:hover:!selected {
    background-color: #3a2a31;
}
QTabWidget#guideTabWidget::pane {
    border: 1px solid #5a3a2a;
    background: transparent;
}
QTabWidget#guideTabWidget > QTabBar::tab {
    padding: 5px 14px;
    color: #c8b89a;
    background: #2a1e18;
    border: 1px solid #5a3a2a;
    border-bottom: none;
    margin-right: 2px;
    border-radius: 4px 4px 0 0;
}
QTabWidget#guideTabWidget > QTabBar::tab:selected {
    background: #4a2a1e;
    color: #fff8ec;
    font-weight: 600;
}
QTextBrowser#guideTextBrowser {
    background: transparent;
    color: #e8ddd0;
    border: none;
    selection-background-color: #6b3a4a;
}
QDialog#operatorDocDialog {
    background-color: #2f2329;
}
QTextBrowser#docViewerBrowser {
    background-color: #f5ecd8;
    color: #2a1e18;
    border: 1px solid #6b3a4a;
    border-radius: 4px;
    selection-background-color: #d4af37;
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
QWidget#toolTabScrollHost,
QScrollArea#connectMainScroll,
QWidget#connectMainScrollViewport,
QWidget#connectMainScrollHost {
    background-color: #f0ece6;
    color: #1a1a1a;
}
QSplitter#connectPageSplitter::handle:horizontal {
    width: 6px;
    margin: 4px 0;
    background-color: rgba(151, 170, 134, 0.45);
}
QSplitter#connectPageSplitter::handle:horizontal:hover {
    background-color: rgba(200, 166, 104, 0.75);
}
QFrame#connectQrFloat {
    background-color: rgba(236, 228, 214, 0.95);
    border: 1px solid rgba(151, 170, 134, 0.55);
    border-radius: 8px;
}
QLabel#connectQrImage {
    background-color: #ffffff;
    padding: 4px;
    border: none;
}
QLabel#connectQrCaption {
    color: #3a1f13;
    font-size: 9pt;
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
QDialog#UiEditorDialog QScrollArea#uiEditorScroll {
    background-color: #f5f2ec;
    border: 1px solid #a09888;
    border-radius: 6px;
}
QDialog#UiEditorDialog QWidget#uiEditorListHost {
    background-color: #f5f2ec;
}
QDialog#UiEditorDialog QFrame#uiEditorRow {
    background-color: rgba(255, 252, 246, 0.95);
    border: 1px solid #c8a668;
    border-radius: 6px;
}
QDialog#UiEditorDialog QLabel#uiEditorRowTitle {
    color: #1a1a1a;
    font-weight: 600;
}
QDialog#UiEditorDialog QToolButton {
    min-width: 28px;
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
QListWidget#toolsNavList {
    background-color: #e8e0d4;
    border: none;
    border-right: 1px solid #a09888;
    outline: none;
}
QListWidget#toolsNavList::item {
    padding: 8px 10px;
    color: #1a1a1a;
    border-radius: 0;
}
QListWidget#toolsNavList::item:selected {
    background-color: #d4af37;
    color: #3a1f13;
    font-weight: 600;
}
QListWidget#toolsNavList::item:hover:!selected {
    background-color: #d0cbc4;
}
QTabWidget#guideTabWidget::pane {
    border: 1px solid #a09888;
    background: transparent;
}
QTabWidget#guideTabWidget > QTabBar::tab {
    padding: 5px 14px;
    color: #4a3a2a;
    background: #ddd6cc;
    border: 1px solid #a09888;
    border-bottom: none;
    margin-right: 2px;
    border-radius: 4px 4px 0 0;
}
QTabWidget#guideTabWidget > QTabBar::tab:selected {
    background: #f5ecd8;
    color: #3a1f13;
    font-weight: 600;
}
QTextBrowser#guideTextBrowser {
    background: transparent;
    color: #2a1e18;
    border: none;
    selection-background-color: #d4af37;
}
QDialog#operatorDocDialog {
    background-color: #f0ece6;
}
QTextBrowser#docViewerBrowser {
    background-color: #f5ecd8;
    color: #2a1e18;
    border: 1px solid #a09888;
    border-radius: 4px;
    selection-background-color: #d4af37;
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
QSplitter#connectionHubSplitter::handle:vertical,
QSplitter#diagCardsSplitter::handle:vertical,
QSplitter#fieldMainSplitter::handle:vertical {
    height: 10px;
    margin: 3px 12px;
}
QSplitter#connectPanelSplitter::handle:vertical:hover,
QSplitter#connectionHubSplitter::handle:vertical:hover,
QSplitter#diagCardsSplitter::handle:vertical:hover,
QSplitter#fieldMainSplitter::handle:vertical:hover {
    background-color: #c9a227;
}
QSplitter#connectPageSplitter::handle:horizontal {
    width: 6px;
    margin: 4px 0;
}
QWidget#surveyMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a2a31, stop:1 #2a1d22);
    border-bottom: 1px solid #7a5a2d;
    min-height: 0;
}
QWidget#surveyTopBarTrack {
    min-width: 0;
}
QWidget#surveyMenuBar QToolButton {
    background: transparent;
    border: none;
    padding: 5px 10px;
    color: #f6eee0;
    font-weight: 600;
}
QWidget#surveyMenuBar QToolButton:hover { background-color: #5f3643; }
QWidget#surveyMenuBar QToolButton::menu-indicator { image: none; width: 0; }
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {
    font-weight: 500; font-size: 9pt; padding: 5px 7px;
}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {
    background-color: #5f3643; color: #ffe2a1;
}
QFrame#surveyBarSep { color: #7a5a2d; max-height: 18px; margin: 0 4px; }
QFrame#topBarChip {
    border: 1px solid #7a5a2d;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.04);
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
    padding: 5px 8px;
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
    border-radius: 4px; padding: 4px 8px;
    max-height: 56px;
    border: 1px solid #7a5a2d; background-color: #3a2a31;
}
QFrame#statusBanner[state="running"] { background-color: #4c2d37; border-color: #d4af37; }
QFrame#statusBanner[state="starting"] { background-color: #4a3a24; border-color: #d4af37; }
QFrame#statusBanner[state="failed"] { background-color: #4a3038; border-color: #d08080; }
QLabel#statusBannerText {
    font-size: 9pt; font-weight: 600; color: #faf6f0;
    padding: 0; margin: 0;
}
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
    + _CONNECT_SHARED_DARK
    + _CONNECT_ROW_VARIANTS_DARK
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
}
QWidget#surveyMenuBar QToolButton {
    background: transparent;
    border: none;
    padding: 5px 10px;
    color: #4a202a;
    font-weight: 600;
}
QWidget#surveyMenuBar QToolButton:hover { background-color: #d9c6a1; }
QWidget#surveyMenuBar QToolButton::menu-indicator { image: none; width: 0; }
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {
    font-weight: 500; font-size: 9pt; padding: 5px 7px;
}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {
    background-color: #d9c6a1; color: #4a202a;
}
QFrame#surveyBarSep { color: #b28a42; max-height: 18px; margin: 0 4px; }
QFrame#topBarChip {
    border: 1px solid #b28a42;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.35);
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
    padding: 5px 8px;
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
    + _CONNECT_SHARED_LIGHT
    + _CONNECT_ROW_VARIANTS_LIGHT
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
QSplitter#connectionHubSplitter::handle:vertical,
QSplitter#diagCardsSplitter::handle:vertical,
QSplitter#fieldMainSplitter::handle:vertical {
    height: 10px;
    margin: 3px 12px;
}
QSplitter#connectPanelSplitter::handle:vertical:hover,
QSplitter#connectionHubSplitter::handle:vertical:hover,
QSplitter#diagCardsSplitter::handle:vertical:hover,
QSplitter#fieldMainSplitter::handle:vertical:hover {
    background-color: #c9a227;
}
QSplitter#connectPageSplitter::handle:horizontal {
    width: 6px;
    margin: 4px 0;
}
QWidget#surveyMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a2a31, stop:1 #2a1d22);
    border-bottom: 1px solid #7a5a2d;
    min-height: 0;
}
QWidget#surveyTopBarTrack {
    min-width: 0;
}
QWidget#surveyMenuBar QToolButton {
    background: transparent;
    border: none;
    padding: 5px 10px;
    color: #f6eee0;
    font-weight: 600;
}
QWidget#surveyMenuBar QToolButton:hover { background-color: #5f3643; }
QWidget#surveyMenuBar QToolButton::menu-indicator { image: none; width: 0; }
QWidget#surveyMenuBar QToolButton#surveyQuickBtn {
    font-weight: 500; font-size: 9pt; padding: 5px 7px;
}
QWidget#surveyMenuBar QToolButton#surveyQuickBtn:checked {
    background-color: #5f3643; color: #ffe2a1;
}
QFrame#surveyBarSep { color: #7a5a2d; max-height: 18px; margin: 0 4px; }
QFrame#topBarChip {
    border: 1px solid #7a5a2d;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.04);
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
    padding: 5px 8px;
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
    + _CONNECT_SHARED_DARK
    + _CONNECT_ROW_VARIANTS_DARK
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
    "midnight_teal": "Midnight Teal",
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


GLOBAL_CONTRAST_GUARD_STYLESHEET = """
QToolTip {
    background-color: #1b1418;
    color: #f4f0ea;
    border: 1px solid #8d6a34;
    padding: 4px 6px;
}
QMessageBox, QErrorMessage {
    background-color: #241a1f;
    color: #f4f0ea;
}
QMessageBox QLabel, QErrorMessage QLabel {
    background: transparent;
    color: #f4f0ea;
}
QMessageBox QPushButton, QErrorMessage QPushButton {
    background-color: #5a3240;
    color: #f4f0ea;
    border: 1px solid #8d6a34;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 84px;
}
QMessageBox QPushButton:hover, QErrorMessage QPushButton:hover {
    background-color: #6b3a4a;
}
QMessageBox QPlainTextEdit,
QMessageBox QTextEdit,
QErrorMessage QPlainTextEdit,
QErrorMessage QTextEdit {
    background-color: #1e181c;
    color: #ece6dc;
    border: 1px solid #7a5a2d;
}
"""


def apply_global_contrast_guard(app: object | None) -> None:
    """Apply high-contrast dialog/tool-tip rules across the whole app."""
    if app is None or not hasattr(app, "styleSheet"):
        return
    marker = "/* BRIDGE_GLOBAL_CONTRAST_GUARD */"
    base_prop = "_bridge_base_stylesheet"
    stored_base = None
    if hasattr(app, "property"):
        stored_base = app.property(base_prop)
    if isinstance(stored_base, str):
        base = stored_base
    else:
        base = str(app.styleSheet() or "")
        if hasattr(app, "setProperty"):
            app.setProperty(base_prop, base)
    merged = f"{base}\n{marker}\n{GLOBAL_CONTRAST_GUARD_STYLESHEET}"
    app.setStyleSheet(merged)
