"""FastAPI REST surface for bridge status/config/commands."""
from __future__ import annotations

from typing import Any, Optional

from app_facade import BridgeAppFacade, WebCommandResult

try:
    from fastapi import FastAPI, Header, HTTPException, Request
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - optional dependency
    FastAPI = None  # type: ignore[misc, assignment]


class ConfigPatch(BaseModel):
    com_port: Optional[str] = None
    baud: Optional[int] = None
    udp_listen_host: Optional[str] = None
    udp_listen_port: Optional[int] = None
    nmea_mode: Optional[str] = None
    hub_device_id: Optional[str] = None
    manual_override: Optional[bool] = None
    network_mode: Optional[str] = None


def _auth_ok(request: Request, token: Optional[str]) -> bool:
    if not token:
        return True
    header = request.headers.get("x-bridge-token") or request.headers.get("X-Bridge-Token")
    return header == token


def create_app(
    facade: BridgeAppFacade,
    *,
    version: str,
    lan_token: Optional[str] = None,
) -> Any:
    if FastAPI is None:
        raise RuntimeError("fastapi is not installed; pip install -r requirements-web.txt")

    app = FastAPI(title="NMEA Serial Bridge Web Control", version=version)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "version": version}

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "nmea-serial-bridge",
            "docs": "/docs",
            "status": "/status",
            "config": "/config",
        }

    @app.get("/status")
    def status() -> dict[str, Any]:
        return facade.get_status().to_dict()

    @app.get("/config")
    def get_config() -> dict[str, Any]:
        return facade.get_config().to_dict()

    @app.patch("/config")
    def patch_config(
        body: ConfigPatch,
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        patch = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        if not patch:
            return {"ok": True, "message": "No changes", "config": facade.get_config().to_dict()}
        result = facade.apply_config(patch)
        return _as_http_payload(result, facade, include_config=True)

    @app.post("/bridge/start")
    def bridge_start(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_http_payload(facade.request_start(), facade)

    @app.post("/bridge/stop")
    def bridge_stop(
        request: Request,
        x_bridge_token: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        if not _auth_ok(request, lan_token):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")
        return _as_http_payload(facade.request_stop(), facade)

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


def _as_http_payload(
    result: WebCommandResult,
    facade: BridgeAppFacade,
    *,
    include_config: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = result.to_dict()
    if include_config and result.ok:
        body["config"] = facade.get_config().to_dict()
    if not result.ok:
        raise HTTPException(status_code=_http_status_for(result), detail=body)
    return body
