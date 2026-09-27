from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.gateway import GatewayService
from app.schemas import AnalysisResponse, GenerateResponse, TextRequest
from app.services.gemini import GeminiError


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self.requests[key]
        while bucket and bucket[0] <= now - self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def create_app(
    settings: Settings | None = None,
    gateway_factory: Callable[[Settings], GatewayService] = GatewayService.build,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.gateway = None
        app.state.startup_error = None
        try:
            app.state.gateway = gateway_factory(settings)
        except Exception as exc:  # readiness exposes a safe summary, never a traceback
            app.state.startup_error = f"{type(exc).__name__}: {exc}"
        yield

    app = FastAPI(title="AI Security Gateway", version=settings.gateway_version, lifespan=lifespan)
    limiter = SlidingWindowRateLimiter(settings.rate_limit_per_minute)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            key = request.client.host if request.client else "unknown"
            if not limiter.allow(key):
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        return await call_next(request)

    def ready_gateway(request: Request) -> GatewayService:
        gateway = request.app.state.gateway
        if gateway is None:
            raise HTTPException(status_code=503, detail="Security detectors are not ready")
        return gateway

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(request: Request):
        if request.app.state.gateway is None:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "error": request.app.state.startup_error},
            )
        return {"status": "ready"}

    @app.get("/version")
    async def version(request: Request):
        return ready_gateway(request).versions()

    @app.post("/api/v1/analyze", response_model=AnalysisResponse)
    async def analyze(payload: TextRequest, request: Request):
        return ready_gateway(request).analyze(payload.text)

    @app.post("/api/v1/generate", response_model=GenerateResponse)
    async def generate(payload: TextRequest, request: Request):
        try:
            return await ready_gateway(request).generate(payload.text)
        except GeminiError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    static_dir = Path(settings.static_dir)
    if static_dir.is_dir():
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def frontend(path: str):
            requested = static_dir / path
            if path and requested.is_file() and static_dir.resolve() in requested.resolve().parents:
                return FileResponse(requested)
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()
