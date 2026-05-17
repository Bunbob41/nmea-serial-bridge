"""Qt stylesheets per UI variant — maroon / gold surfaces."""

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
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background-color: #6b3a4a;
    color: #ffe2a1;
}
QTabBar::tab:hover:!selected { background-color: #5a3543; }
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport,
QWidget#toolTabScrollHost {
    background-color: #2f2329;
    color: #f6eee0;
}
QLabel#tabHint { color: #ffe2a1; font-size: 10pt; padding-bottom: 4px; }
QLabel#tabNote { color: #d9c5a4; font-size: 9pt; }
QCheckBox { color: #eadcc8; }
QRadioButton { color: #eadcc8; }
QFrame#iosCard {
    background-color: rgba(68, 44, 52, 0.55);
    border: 1px solid #7a5a2d;
    border-radius: 12px;
}
QToolButton#iosCardToggle {
    color: #ffe2a1;
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
QTabWidget { background-color: #f3ecdf; }
QTabWidget::pane {
    background-color: #f7f1e6;
    border: 1px solid #b28a42;
    top: -1px;
}
QTabBar { background-color: #e7dcc9; }
QTabBar::tab {
    background-color: #d9c6a1;
    color: #4a202a;
    padding: 6px 12px;
}
QTabBar::tab:selected { background-color: #f7f1e6; color: #4a202a; }
QScrollArea#toolTabScroll,
QWidget#toolTabScrollViewport,
QWidget#toolTabScrollHost {
    background-color: #f7f1e6;
    color: #4a202a;
}
QLabel#tabHint { color: #5a2a33; font-size: 10pt; }
QLabel#tabNote { color: #7a5a2d; font-size: 9pt; }
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
    background-color: #2f2329;
    color: #f6eee0;
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QSplitter::handle { background-color: #57333f; }
QSplitter::handle:hover { background-color: #7a4a58; }
QMenuBar {
    background-color: #3a2a31;
    color: #f6eee0;
    border-bottom: 1px solid #7a5a2d;
    padding: 2px 4px;
}
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected { background-color: #5f3643; color: #ffe2a1; }
QMenu { background-color: #3a2a31; color: #f6eee0; border: 1px solid #7a5a2d; }
QMenu::item:selected { background-color: #5f3643; color: #ffe2a1; }
QLabel#appTitle { font-size: 15pt; font-weight: 600; color: #ffe2a1; }
QLabel#appSubtitle {
    color: #1f1408;
    font-size: 9pt;
    font-weight: 600;
    background-color: #d4af37;
    border: 1px solid #b28a42;
    border-radius: 4px;
    padding: 4px 6px;
}
QFrame#statusBanner {
    border-radius: 8px; padding: 10px 12px;
    border: 1px solid #7a5a2d; background-color: #3a2a31;
}
QFrame#statusBanner[state="running"] { background-color: #4c2d37; border-color: #d4af37; }
QFrame#statusBanner[state="starting"] { background-color: #4a3a24; border-color: #d4af37; }
QFrame#statusBanner[state="failed"] { background-color: #4a3038; border-color: #d08080; }
QLabel#statusBannerText { font-size: 12pt; font-weight: 600; color: #ffe9b9; }
QLabel#intentHint {
    color: #1f1408;
    background-color: #d4af37;
    border: 1px solid #b28a42;
    border-radius: 4px;
    padding: 6px 8px;
    font-weight: 600;
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
    background-color: #241a1f; color: #f2e7d2; border: 1px solid #7a5a2d;
    font-family: Consolas, monospace; font-size: 9pt;
}
QPlainTextEdit#sendEdit {
    background-color: #241a1f; color: #f6eee0; border: 1px solid #8d6a34;
    border-radius: 4px; font-family: Consolas, monospace; font-size: 9pt;
}
QStatusBar { background: #2a1d22; color: #ead9b7; border-top: 1px solid #7a5a2d; font-weight: 500; }
QStatusBar QLabel { color: #f6eee0; }
QStatusBar::item {
    border: 1px solid #b28a42;
    border-radius: 4px;
    background-color: #7a5a2d;
    padding: 0px 6px;
}
QGroupBox {
    border: 1px solid #7a5a2d; border-radius: 6px; margin-top: 12px;
    padding: 10px; color: #f6eee0;
}
QGroupBox::title { color: #d4af37; }
QPushButton {
    background-color: #5a3240; color: #f6eee0;
    border: 1px solid #8d6a34; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background-color: #6a3d4c; }
QPushButton:pressed { background-color: #4a2a36; }
QComboBox, QLineEdit, QSpinBox {
    background-color: #2a1d22; color: #f6eee0; border: 1px solid #8d6a34; padding: 4px 6px;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border: 1px solid #f1d483; }
"""
    + _TAB_PAGE_DARK
)

BRIDGE_STYLESHEET_MINIMAL = (
    """
QWidget#BridgeRoot {
    background-color: #f3ecdf;
    color: #4a202a;
    font-family: "Segoe UI", sans-serif;
    font-size: 9pt;
}
QSplitter::handle { background-color: #ccb993; }
QSplitter::handle:hover { background-color: #b79b69; }
QMenuBar {
    background-color: #e7dcc9;
    color: #4a202a;
    border-bottom: 1px solid #b28a42;
    padding: 2px 4px;
}
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected { background-color: #d9c6a1; color: #4a202a; }
QMenu { background-color: #f7f1e6; color: #4a202a; border: 1px solid #b28a42; }
QMenu::item:selected { background-color: #e3cfab; color: #4a202a; }
QLabel#statusLine { font-weight: 600; padding: 4px 0; }
QLabel#statusLine[state="running"] { color: #6b3643; }
QLabel#statusLine[state="starting"] { color: #7a5a2d; }
QLabel#statusLine[state="failed"] { color: #a02020; }
QLabel#statusLine[state="stopped"] { color: #5a2a33; }
QPlainTextEdit {
    background-color: #fffaf2; color: #4a202a; border: 1px solid #b28a42;
    font-family: Consolas, monospace; font-size: 9pt;
}
QPlainTextEdit#sendEdit {
    background-color: #fffaf2; color: #4a202a; border: 1px solid #b28a42;
    font-family: Consolas, monospace; font-size: 9pt;
}
QPushButton#btnStart { background-color: #d4af37; border: 1px solid #b28a42; min-height: 32px; font-weight: 700; color: #3a1f13; }
QPushButton#btnStop { background-color: #cfa0ab; border: 1px solid #9b6a73; min-height: 32px; color: #4a202a; }
QPushButton#btnStart:hover { background-color: #e0be56; }
QPushButton#btnStop:hover { background-color: #d9b0b8; }
QGroupBox { border: 1px solid #b28a42; margin-top: 8px; padding: 8px; color: #4a202a; }
QStatusBar { background: #e7dcc9; color: #5a2a33; border-top: 1px solid #b28a42; font-weight: 500; }
QLabel#intentHint {
    color: #1f1408;
    background-color: #d4af37;
    border: 1px solid #9b6a18;
    border-radius: 4px;
    padding: 6px 8px;
    font-weight: 600;
}
QStatusBar::item {
    border: 1px solid #9b6a18;
    border-radius: 4px;
    background-color: #d4af37;
    padding: 0px 6px;
}
QPushButton { background-color: #d9c6a1; color: #4a202a; border: 1px solid #b28a42; border-radius: 6px; }
QPushButton:hover { background-color: #e3cfab; }
QComboBox, QLineEdit, QSpinBox {
    background-color: #fffaf2; color: #4a202a; border: 1px solid #b28a42; padding: 4px 6px;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border: 1px solid #8d6a34; }
"""
    + _TAB_PAGE_LIGHT
)

BRIDGE_STYLESHEET_LOGFIRST = (
    """
QWidget#BridgeRoot {
    background-color: #241a1f;
    color: #f2e7d2;
    font-family: "Segoe UI", sans-serif;
    font-size: 9pt;
}
QSplitter::handle { background-color: #57333f; }
QSplitter::handle:hover { background-color: #7a4a58; }
QMenuBar {
    background-color: #3a2a31;
    color: #f6eee0;
    border-bottom: 1px solid #7a5a2d;
    padding: 2px 4px;
}
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected { background-color: #5f3643; color: #ffe2a1; }
QMenu { background-color: #3a2a31; color: #f6eee0; border: 1px solid #7a5a2d; }
QMenu::item:selected { background-color: #5f3643; color: #ffe2a1; }
QPlainTextEdit#logView {
    background-color: #1b1418; color: #f0dfc0; border: none;
    font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt;
}
QFrame#controlStrip { background-color: #2f2329; border-top: 1px solid #7a5a2d; }
QPushButton#btnStart { background-color: #d4af37; border: 1px solid #f1d483; min-height: 28px; color: #3a1f13; font-weight: 700; }
QPushButton#btnStop { background-color: #6b3643; border: 1px solid #b47a88; min-height: 28px; color: #f6eee0; }
QPushButton#btnStart:hover { background-color: #e0be56; border-color: #ffe7b0; }
QPushButton#btnStop:hover { background-color: #7b4150; border-color: #c78f9b; }
QLabel#statusLine { font-weight: 600; color: #ffe2a1; }
QStatusBar { background: #2a1d22; color: #d7c3a0; border-top: 1px solid #7a5a2d; }
QStatusBar QLabel { color: #f6eee0; }
QStatusBar::item {
    border: 1px solid #b28a42;
    border-radius: 4px;
    background-color: #7a5a2d;
    padding: 0px 6px;
}
QPlainTextEdit#sendEdit {
    background-color: #1b1418; color: #f2e7d2; border: 1px solid #7a5a2d;
    font-family: Consolas, monospace; font-size: 9pt;
}
QGroupBox { border: 1px solid #7a5a2d; color: #f6eee0; }
QPushButton { background-color: #5a3240; color: #f6eee0; border: 1px solid #8d6a34; }
QPushButton:hover { background-color: #6a3d4c; }
QLineEdit { background-color: #2a1d22; color: #f6eee0; border: 1px solid #8d6a34; }
QLineEdit:focus { border: 1px solid #f1d483; }
QCheckBox { color: #eadcc8; }
"""
    + _TAB_PAGE_DARK
)

# First-run / dev UI layout picker (modal dialog)
UI_PICKER_STYLESHEET = """
QDialog#UiPickerDialog {
    background-color: #f7f1e6;
    color: #4a202a;
}
QDialog#UiPickerDialog QLabel { color: #4a202a; }
QDialog#UiPickerDialog QRadioButton { color: #4a202a; }
QDialog#UiPickerDialog QCheckBox { color: #4a202a; }

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
    color: #d4af37;
    font-size: 8pt;
    font-weight: 600;
    padding-bottom: 0px;
}
QToolButton#surveyHudSectionToggle {
    color: #f0dfc0;
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
    color: #f2e7d2;
    font-size: 9pt;
    font-weight: 600;
}
QLabel#surveyHudMetricSub {
    color: #c8ad84;
    font-size: 7pt;
}
QLabel#surveyHudMetricValueHero {
    color: #ffe2a1;
    font-size: 22pt;
    font-weight: bold;
    font-family: Consolas, "Cascadia Mono", monospace;
}
QLabel#surveyHudMetricValue {
    color: #f6eee0;
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
    color: #f0dfc0;
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
}


def bridge_stylesheet(ui_mode: str, theme_id: str) -> str:
    from ui.theme_choice import _normalize_theme_id
    from ui.theme_palette import apply_theme_colors

    theme_id = _normalize_theme_id(theme_id)
    base = {
        "standard": BRIDGE_STYLESHEET_STANDARD,
        "minimal": BRIDGE_STYLESHEET_MINIMAL,
        "logfirst": BRIDGE_STYLESHEET_LOGFIRST,
    }.get(ui_mode, BRIDGE_STYLESHEET_STANDARD)
    return apply_theme_colors(base, theme_id)


def hud_stylesheet(theme_id: str) -> str:
    from ui.theme_choice import _normalize_theme_id
    from ui.theme_palette import apply_theme_colors

    return apply_theme_colors(SURVEY_STATS_POPOUT_STYLESHEET, _normalize_theme_id(theme_id))
