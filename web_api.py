"""FastAPI REST surface for bridge status/config/commands and static dashboard."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from web_facade_types import WebCommandResult

if TYPE_CHECKING:
    from app_facade import BridgeAppFacade

try:
    from fastapi import FastAPI, Header, HTTPException, Request
    from fastapi.responses import FileResponse, Response
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    from starlette.responses import Response as StarletteResponse
except ImportError:  # pragma: no cover - optional dependency
    FastAPI = None  # type: ignore[misc, assignment]
    BaseModel = object  # type: ignore[misc, assignment]


class ConfigPatch(BaseModel):
    com_port: Optional[str] = None
    baud: Optional[int] = None
    udp_listen_host: Optional[str] = None
    udp_listen_port: Optional[int] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    nmea_mode: Optional[str] = None
    hub_device_id: Optional[str] = None
    manual_override: Optional[bool] = None
    network_mode: Optional[str] = None


class HealthResponse(BaseModel):
    ok: bool
    version: str


class ApiIndexResponse(BaseModel):
    service: str
    docs: str
    status: str
    config: str
    discovery: str
    meta: str
    logs: str = "/logs"


class LogLineResponse(BaseModel):
    seq: int
    text: str
    kind: str
    mono: float


class LogsResponse(BaseModel):
    lines: List[LogLineResponse]
    latest_seq: int
    paused: bool
    paused_dropped: int = 0


class MetaResponse(BaseModel):
    version: str
    lan_bind: bool
    token_required: bool
    commands_ready: bool = True
    headless: bool = False
    platform: str = "unknown"
    config_path: Optional[str] = None
    config_writable: bool = False


class DashboardLayoutResponse(BaseModel):
    layout_mode: str = "gridstack"
    local_storage: dict[str, str] = {}


class DashboardLayoutPatch(BaseModel):
    layout_mode: Optional[str] = None
    local_storage: Optional[dict[str, str]] = None


class StatusResponse(BaseModel):
    running: bool
    com_port: str
    configured_com_port: str = ""
    baud: int
    udp_listen_host: str
    udp_listen_port: int
    nmea_mode: str
    hz_net_to_com: Optional[float] = None
    hz_com_to_net: Optional[float] = None
    hz_inject: Optional[float] = None
    drops: int
    rejects: int
    drops_net_to_com: int = 0
    drops_com_to_net: int = 0
    rejects_net_to_com: int = 0
    rejects_com_to_net: int = 0
    queue_net_to_com: int = 0
    queue_com_to_net: int = 0
    lines_net_to_com: int = 0
    lines_com_to_net: int = 0
    transport_ok: bool = True
    gnss_summary: str = ""
    gnss_fix: str = ""
    gnss_sats: Optional[int] = None
    gnss_hdop: Optional[float] = None
    gnss_stale: bool = False
    gnss_quality: Optional[int] = None
    gnss_stream_idle: bool = False
    position_lat: Optional[float] = None
    position_lon: Optional[float] = None
    position_lat_ddm: str = ""
    position_lon_ddm: str = ""
    position_source: str = ""
    position_stale: bool = True
    last_error: Optional[str] = None
    com_port_available: Optional[bool] = None
    com_port_lock_reason: str = ""
    com_lock_checking: bool = False
    updated_mono: float
    session_running_s: float = 0.0
    com_active_total_s: float = 0.0
    last_com_to_net_age_s: Optional[float] = None
    serial_link_state: str = "closed"
    udp_peer_count: int = 0
    udp_peer_newest_in_s: Optional[float] = None
    udp_peer_stale: bool = False
    udp_peer_details: list[dict[str, Any]] = []
    net_mode: str = ""
    depth_enabled: bool = False
    depth_port: str = ""
    depth_rate_hz: float = 0.0
    last_depth_m: Optional[float] = None
    last_sounding_stale: bool = False
    sounding_count: int = 0
    sounding_stale_count: int = 0
    soundings_recent: list[dict[str, Any]] = []


class ConfigResponse(BaseModel):
    com_port: str
    baud: int
    udp_listen_host: str
    udp_listen_port: int
    nmea_mode: str
    hub_device_id: Optional[str] = None
    manual_override: bool
    network_mode: str
    remote_host: str = ""
    remote_port: int = 10110


class SerialDeviceResponse(BaseModel):
    device_id: str
    port: str
    description: str
    manufacturer: str
    match_keyword: str
    status: str


class NetworkCardResponse(BaseModel):
    device_id: str
    label: str
    mode_hint: str
    host: str
    port: int
    port_available: bool
    peer_count: int
    status: str
    discovery_source: str


class DiscoveryResponse(BaseModel):
    updated_mono: float
    scan_note: str
    scan_busy: bool
    serial_devices: List[SerialDeviceResponse]
    network_cards: List[NetworkCardResponse]
    errors: List[str]


class ProbePortRequest(BaseModel):
    com_port: str


class CommandResponse(BaseModel):
    ok: bool
    message: str
    error_code: Optional[str] = None
    state: str = "stopped"
    config: Optional[ConfigResponse] = None


class _DevStaticFiles(StaticFiles):
    """Avoid stale dashboard.js in browsers during grid/standard UI iteration."""

    async def get_response(self, path: str, scope) -> StarletteResponse:
        response = await super().get_response(path, scope)
        if path.endswith((".js", ".css", ".html")):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


def resolve_static_dir() -> Optional[Path]:
    """Dashboard assets (dev tree or PyInstaller ``web/static`` under ``_MEIPASS``)."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass))
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir)
        candidates.append(exe_dir / "_internal")
    else:
        candidates.append(Path(__file__).resolve().parent)
    seen: set[str] = set()
    for base in candidates:
        key = str(base).lower()
        if key in seen:
            continue
        seen.add(key)
        p = base / "web" / "static"
        if p.is_dir():
            return p
    return None


def _static_dir() -> Optional[Path]:
    return resolve_static_dir()


def _auth_ok(request: Request, token: Optional[str]) -> bool:
    if not token:
        return True
    header = request.headers.get("x-bridge-token") or request.headers.get("X-Bridge-Token")
    return header == token


def _discovery_row(item: Any) -> dict[str, Any]:
    """Accept DTO objects or plain dicts (headless facade snapshot round-trip)."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return dict(item)


def create_app(
    facade: BridgeAppFacade,
    *,
    version: str,
    lan_token: Optional[str] = None,
    headless: bool = False,
    config_path: Optional[str] = None,
    config_writable: bool = False,
) -> Any:
    if FastAPI is None:
        raise RuntimeError("fastapi is not installed; pip install -r requirements-web.txt")

    app = FastAPI(title="Serial Link Web Control", version=version)

    # ------------------------------------------------------------------ health
    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(ok=True, version=version)

    # ------------------------------------------------------------------ meta
    @app.get("/meta", response_model=MetaResponse)
    def meta() -> MetaResponse:
        lan = lan_token is not None
        token_req = lan_token is not None
        if not token_req:
            try:
                from ui.ui_prefs import load_web_ui_prefs

                prefs = load_web_ui_prefs()
                lan = bool(prefs.get("lan_bind"))
                token_req = lan and bool(prefs.get("token"))
            except Exception:
                lan = False
                token_req = False
        return MetaResponse(
            version=version,
            lan_bind=lan,
            token_required=token_req,
            commands_ready=facade.commands_ready(),
            headless=headless,
            platform=sys.platform,
            config_path=config_path,
            config_writable=bool(config_writable and config_path),
        )

    # ------------------------------------------------------------------ api index (old /)
    @app.get("/token-qr", include_in_schema=False)
    def token_qr(request: Request) -> Response:
        try:
            from ui.ui_prefs import load_web_ui_prefs

            prefs = load_web_ui_prefs()
            token = prefs.get("token")
        except Exception:
            token = None
        if not token:
            raise HTTPException(status_code=404, detail="No API token configured")
        qp = request.query_params
        use_setup = qp.get("setup") in ("1", "true", "yes")
        if use_setup:
            from web.token_setup import build_setup_url

            base = (qp.get("base_url") or "").strip()
            if not base:
                host = request.headers.get("host", "127.0.0.1:8765")
                base = f"http://{host}"
            payload = build_setup_url(base, str(token))
        else:
            payload = str(token)
        try:
            import io

            import qrcode
            import qrcode.image.svg

            factory = qrcode.image.svg.SvgPathImage
            img = qrcode.make(payload, image_factory=factory)
            buf = io.BytesIO()
            img.save(buf)
            svg = buf.getvalue().decode("utf-8")
        except Exception:
            from web.qr_svg import token_to_svg

            svg = token_to_svg(str(token))
        return Response(content=svg, media_type="image/svg+xml")

    @app.get("/api", response_model=ApiIndexResponse)
    def api_index() -> ApiIndexResponse:
        return ApiIndexResponse(
            service="serial-link",
            docs="/docs",
            status="/status",
            config="/config",
            discovery="/discovery",
            meta="/meta",
        )

    # ------------------------------------------------------------------ status / config
    @app.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return StatusResponse(**facade.get_status().to_dict())

    @app.get("/logs", response_model=LogsResponse)
    def logs(after: int = 0, limit: int = 150) -> LogsResponse:
        payload = facade.get_logs(after_seq=max(0, after), limit=limit)
        return LogsResponse(**payload.to_dict())

    @app.get("/config", response_model=ConfigResponse)
    def get_config() -> ConfigResponse:
        return ConfigResponse(**facade.get_config().to_dict())

    @app.patch("/config", response_model=CommandResponse)
    def patch_config(
        body: ConfigPatch,
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        patch = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        if not patch:
            cfg = facade.get_config().to_dict()
            return CommandResponse(ok=True, message="No changes", config=ConfigResponse(**cfg))
        result = facade.apply_config(patch)
        return _as_command_response(result, facade, include_config=True)

    @app.post("/config/persist", response_model=CommandResponse)
    def persist_site_config(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not headless:
            raise HTTPException(status_code=404, detail="Site config persist is headless-only")
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        persist = getattr(facade, "persist_site_config", None)
        if persist is None:
            raise HTTPException(status_code=404, detail="Site config persist not available")
        result = persist()
        return _as_command_response(result, facade)

    # ------------------------------------------------------------------ bridge commands
    @app.post("/bridge/start", response_model=CommandResponse)
    def bridge_start(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_command_response(facade.request_start(), facade)

    @app.post("/bridge/stop", response_model=CommandResponse)
    def bridge_stop(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_command_response(facade.request_stop(), facade)

    # ------------------------------------------------------------------ discovery
    @app.get("/discovery", response_model=DiscoveryResponse)
    def get_discovery() -> DiscoveryResponse:
        d = facade.get_discovery()
        return DiscoveryResponse(
            updated_mono=d.updated_mono,
            scan_note=d.scan_note,
            scan_busy=d.scan_busy,
            serial_devices=[SerialDeviceResponse(**_discovery_row(s)) for s in d.serial_devices],
            network_cards=[NetworkCardResponse(**_discovery_row(c)) for c in d.network_cards],
            errors=list(d.errors),
        )

    @app.post("/discovery/refresh", response_model=CommandResponse)
    def discovery_refresh(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_command_response(facade.request_refresh_discovery(), facade)

    # ------------------------------------------------------------------ ports
    @app.post("/ports/refresh", response_model=CommandResponse)
    def ports_refresh(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_command_response(facade.request_refresh_serial_ports(), facade)

    @app.post("/ports/unlock", response_model=CommandResponse)
    def ports_unlock(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_command_response(facade.request_unlock_ports(), facade)

    @app.post("/ports/probe", response_model=CommandResponse)
    def ports_probe(
        body: ProbePortRequest,
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> CommandResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_command_response(facade.request_probe_com_port(body.com_port), facade)

    # ------------------------------------------------------------------ dashboard layout (product defaults)
    @app.get("/dashboard-layout", response_model=DashboardLayoutResponse)
    def get_dashboard_layout() -> DashboardLayoutResponse:
        try:
            from ui.ui_prefs import load_web_dashboard_layout

            payload = load_web_dashboard_layout()
        except Exception:
            payload = {"layout_mode": "gridstack", "local_storage": {}}
        return DashboardLayoutResponse(**payload)

    @app.put("/dashboard-layout", response_model=DashboardLayoutResponse)
    def put_dashboard_layout(
        body: DashboardLayoutPatch,
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> DashboardLayoutResponse:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        try:
            from ui.ui_prefs import load_web_dashboard_layout, save_web_dashboard_layout
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        prev = load_web_dashboard_layout()
        mode = body.layout_mode if body.layout_mode is not None else prev["layout_mode"]
        storage = (
            body.local_storage
            if body.local_storage is not None
            else prev["local_storage"]
        )
        save_web_dashboard_layout(layout_mode=str(mode), local_storage=dict(storage or {}))
        updated = load_web_dashboard_layout()
        return DashboardLayoutResponse(**updated)

    # ------------------------------------------------------------------ static dashboard
    static = _static_dir()
    if static is not None:
        repo_root = Path(__file__).resolve().parent
        fonts_dir = repo_root / "assets" / "fonts"
        if fonts_dir.is_dir():
            app.mount(
                "/static/fonts",
                StaticFiles(directory=str(fonts_dir)),
                name="bundle-fonts",
            )

        for icon_name in ("app-icon.ico", "app-icon.png"):
            icon_path = repo_root / "assets" / icon_name
            if icon_path.is_file():
                _favicon_path = icon_path
                break
        else:
            _favicon_path = None

        if _favicon_path is not None:

            @app.get("/favicon.ico", include_in_schema=False)
            def favicon() -> FileResponse:
                return FileResponse(str(_favicon_path))

        app.mount(
            "/static",
            _DevStaticFiles(directory=str(static), html=True),
            name="static",
        )

        grid_index = static / "layouts" / "gridstack" / "index.html"

        @app.get("/", include_in_schema=False)
        def dashboard() -> FileResponse:
            # Default operator UI: customizable grid; classic single-page layout at /static/index.html
            path = grid_index if grid_index.is_file() else static / "index.html"
            return FileResponse(
                str(path),
                media_type="text/html",
                headers={"Cache-Control": "no-store, must-revalidate"},
            )
    else:
        @app.get("/", response_model=ApiIndexResponse)
        def root() -> ApiIndexResponse:
            return ApiIndexResponse(
                service="serial-link",
                docs="/docs",
                status="/status",
                config="/config",
                discovery="/discovery",
                meta="/meta",
            )

    return app


def _http_status_for(result: WebCommandResult) -> int:
    if result.ok:
        return 200
    code = result.error_code or "error"
    if code == "validation":
        return 400
    if code in ("running_guard", "busy"):
        return 409
    if code == "unsupported":
        return 501
    if code == "unavailable":
        return 503
    return 400


def _as_command_response(
    result: WebCommandResult,
    facade: BridgeAppFacade,
    *,
    include_config: bool = False,
) -> CommandResponse:
    cfg: Optional[ConfigResponse] = None
    if include_config and result.ok:
        cfg = ConfigResponse(**facade.get_config().to_dict())
    body = CommandResponse(
        ok=result.ok,
        message=result.message,
        error_code=result.error_code,
        state=result.state,
        config=cfg,
    )
    if not result.ok:
        raise HTTPException(status_code=_http_status_for(result), detail=body.model_dump())
    return body
