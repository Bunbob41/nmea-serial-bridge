"""Survey Map tab ? Leaflet map in Qt WebEngine (controls live in survey_map.html)."""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from PySide6 import QtCore, QtWidgets

try:
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    _HAS_WEBENGINE = True
except ImportError:
    QWebChannel = None  # type: ignore[misc, assignment]
    QWebEngineSettings = None  # type: ignore[misc, assignment]
    QWebEngineView = None  # type: ignore[misc, assignment]
    _HAS_WEBENGINE = False

_DEFAULT_SURVEY_MAP_DEPTH_MAX_M = 200.0
_JS_REFRESH_LAYOUT = (
    "(function(){"
    "if(typeof window.refreshMapLayout==='function'){window.refreshMapLayout();}"
    "})();"
)
_JS_INIT_OVERLAYS = (
    "(function(){"
    "if(typeof initSurveyMapOverlays==='function'){initSurveyMapOverlays();}"
    "else if(typeof resetSurveyMapOverlays==='function'){resetSurveyMapOverlays();}"
    "})();"
)
_SURVEY_MAP_PAGE_QUERY = "v=1.49.0"


def _static_survey_map_html() -> Optional[str]:
    try:
        from web_api import resolve_static_dir
    except ImportError:
        return None
    static = resolve_static_dir()
    if static is None:
        return None
    html = static / "survey_map.html"
    return str(html.resolve()) if html.is_file() else None


def _survey_map_page_url(win: Any) -> Optional[str]:
    if _static_survey_map_html() is None:
        return None
    ensure = getattr(win, "_ensure_web_server_running", None)
    local_url = getattr(win, "_web_dashboard_local_url", None)
    if callable(ensure) and callable(local_url):
        try:
            ensure()
            base = str(local_url()).rstrip("/")
            return f"{base}/static/survey_map.html?{_SURVEY_MAP_PAGE_QUERY}"
        except Exception:
            pass
    from pathlib import Path

    path = _static_survey_map_html()
    return Path(path).as_uri() if path else None


def _configure_web_view(view: QWebEngineView) -> None:
    if QWebEngineSettings is None:
        return
    settings = view.settings()
    for attr in (
        QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
        QWebEngineSettings.WebAttribute.JavascriptEnabled,
        QWebEngineSettings.WebAttribute.LocalStorageEnabled,
    ):
        settings.setAttribute(attr, True)


class _SurveyMapBridge(QtCore.QObject):
    def __init__(self, panel: "SurveyMapPanel") -> None:
        super().__init__()
        self._panel = panel

    @QtCore.Slot(str)
    def setPrefsJson(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(data, dict):
            self._panel._prefs_cache.update(data)


class SurveyMapPanel(QtWidgets.QWidget):
    def __init__(self, win: Any, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._win = win
        self.setObjectName("modernSurveyMapPage")
        self._last_stats: dict[str, Any] = {}
        self._last = 0.0
        self._map_ready = False
        self._prefs_cache: dict[str, Any] = {}
        self._bridge: Optional[_SurveyMapBridge] = None
        self._layout_refresh_timer = QtCore.QTimer(self)
        self._layout_refresh_timer.setSingleShot(True)
        self._layout_refresh_timer.setInterval(200)
        self._layout_refresh_timer.timeout.connect(self._apply_map_layout_refresh)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._view: Optional[QWebEngineView] = None
        if _HAS_WEBENGINE and QWebEngineView is not None:
            self._view = QWebEngineView()
            self._view.setObjectName("modernSurveyMapWebView")
            _configure_web_view(self._view)
            self._bridge = _SurveyMapBridge(self)
            channel = QWebChannel(self)
            channel.registerObject("surveyBridge", self._bridge)
            self._view.page().setWebChannel(channel)
            self._view.loadFinished.connect(self._on_map_load_finished)
            root.addWidget(self._view, 1)
            QtCore.QTimer.singleShot(0, self._load_map_page)
        else:
            root.addWidget(QtWidgets.QLabel("Requires Qt WebEngine"), 1)

    def _depth_prefs_payload(self) -> dict[str, Any]:
        return {
            "baseLayer": self._prefs_cache.get("survey_map_base_layer", "satellite"),
            "showDepth": bool(self._prefs_cache.get("survey_map_show_depth", True)),
            "depthAuto": bool(self._prefs_cache.get("survey_map_depth_auto", True)),
            "depthMin": float(self._prefs_cache.get("survey_map_depth_min_m", 0.0)),
            "depthMax": float(
                self._prefs_cache.get(
                    "survey_map_depth_max_m", _DEFAULT_SURVEY_MAP_DEPTH_MAX_M
                )
            ),
        }

    def _run_map_js(self, script: str) -> None:
        if self._view:
            self._view.page().runJavaScript(script)

    def _push_prefs_to_map(self) -> None:
        if not self._view or not self._map_ready:
            return
        prefs = json.dumps(self._depth_prefs_payload())
        script = (
            "(function(p){"
            "if(typeof window.setSurveyMapPrefs==='function'){window.setSurveyMapPrefs(p);}"
            "})(" + prefs + ");"
        )
        self._run_map_js(script)
        self._run_map_js(
            "if(typeof window.ensureSurveyMap==='function'){window.ensureSurveyMap();}"
        )

    def _load_map_page(self) -> None:
        if not self._view:
            return
        url = _survey_map_page_url(self._win)
        if url:
            self._view.setUrl(QtCore.QUrl(url))

    def _on_map_load_finished(self, ok: bool) -> None:
        self._map_ready = bool(ok)
        if not ok or not self._view:
            return
        QtCore.QTimer.singleShot(0, self._push_prefs_to_map)
        self._run_map_js(_JS_INIT_OVERLAYS)
        self.refresh_map_layout()
        if self._last_stats:
            self._last = 0.0
            self.update_from_stats(self._last_stats)

    def showEvent(self, event: QtCore.QEvent) -> None:
        super().showEvent(event)
        self.refresh_map_layout()

    def refresh_map_layout(self) -> None:
        """Debounced Leaflet relayout when the Qt tab becomes visible."""
        if not self._view:
            return
        self._layout_refresh_timer.start()

    def _apply_map_layout_refresh(self) -> None:
        if self._view and self._map_ready:
            self._run_map_js(_JS_REFRESH_LAYOUT)

    def update_from_stats(self, stats: dict[str, Any]) -> None:
        self._last_stats = dict(stats)
        if (
            not self._view
            or not self._map_ready
            or not self.isVisible()
            or time.monotonic() - self._last < 1.0
        ):
            return
        self._last = time.monotonic()
        payload = {
            "position_lat": stats.get("position_lat"),
            "position_lon": stats.get("position_lon"),
            "position_stale": stats.get("position_stale"),
            "gnss_stream_idle": stats.get("gnss_stream_idle"),
            "soundings_recent": stats.get("soundings_recent") or [],
            "running": bool(stats.get("running")),
            "depth_rate_hz": stats.get("depth_rate_hz", stats.get("depth_hz")),
            "depth_enabled": bool(stats.get("depth_enabled")),
            "last_depth_m": stats.get("last_depth_m"),
            "last_depth_text": stats.get("last_depth_text") or "",
            "last_sounding_stale": bool(stats.get("last_sounding_stale")),
            **self._depth_prefs_payload(),
        }
        blob = json.dumps(payload)
        script = (
            "(function(p){"
            "if(typeof window.updateSurveyMap==='function'){window.updateSurveyMap(p);}"
            "})(" + blob + ");"
        )
        self._run_map_js(script)

    def collect_prefs(self) -> dict[str, Any]:
        return {
            "survey_map_show_depth": bool(
                self._prefs_cache.get("survey_map_show_depth", True)
            ),
            "survey_map_base_layer": str(
                self._prefs_cache.get("survey_map_base_layer", "satellite")
            ),
            "survey_map_depth_auto": bool(
                self._prefs_cache.get("survey_map_depth_auto", True)
            ),
            "survey_map_depth_min_m": float(
                self._prefs_cache.get("survey_map_depth_min_m", 0.0)
            ),
            "survey_map_depth_max_m": float(
                self._prefs_cache.get(
                    "survey_map_depth_max_m", _DEFAULT_SURVEY_MAP_DEPTH_MAX_M
                )
            ),
        }

    def restore_prefs(self, prefs: dict[str, Any]) -> None:
        self._prefs_cache = {
            "survey_map_show_depth": bool(prefs.get("survey_map_show_depth", True)),
            "survey_map_base_layer": str(prefs.get("survey_map_base_layer") or "satellite"),
            "survey_map_depth_auto": bool(prefs.get("survey_map_depth_auto", True)),
            "survey_map_depth_min_m": float(prefs.get("survey_map_depth_min_m", 0.0)),
            "survey_map_depth_max_m": float(
                prefs.get("survey_map_depth_max_m", _DEFAULT_SURVEY_MAP_DEPTH_MAX_M)
            ),
        }
        if self._view and self._map_ready:
            self._push_prefs_to_map()


def create_survey_map_tab(win: Any) -> SurveyMapPanel:
    panel = SurveyMapPanel(win)
    win.survey_map_panel = panel
    from ui.ui_prefs import load_budget_survey_prefs

    panel.restore_prefs(load_budget_survey_prefs())
    return panel
