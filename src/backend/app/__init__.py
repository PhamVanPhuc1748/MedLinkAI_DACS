from __future__ import annotations

import logging
import time
from typing import Any

# ── Logger cho toàn bộ API ────────────────────────────────────────────────────
_api_logger = logging.getLogger("MedLink_API")
if not _api_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "\033[96m%(asctime)s\033[0m | \033[1m%(name)s\033[0m | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    _api_logger.addHandler(_handler)
_api_logger.setLevel(logging.INFO)


def create_app() -> Any:
    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    from starlette.middleware.base import BaseHTTPMiddleware

    from .api import router as api_router
    from .database import init_db

    app = FastAPI(
        title="Drug-Disease AI API",
        version="1.0.0",
        description="API du doan lien ket Thuoc - Benh voi GCN va quan tri du lieu.",
    )

    # ── Middleware ghi log toàn bộ request/response ───────────────────────────
    class APILoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            start = time.perf_counter()
            method = request.method
            path = request.url.path
            query = str(request.url.query) if request.url.query else ""
            client_ip = request.client.host if request.client else "unknown"
            full_path = f"{path}?{query}" if query else path

            _api_logger.info(
                ">>> \033[93m%s\033[0m \033[97m%s\033[0m  (client: %s)",
                method, full_path, client_ip,
            )

            try:
                response = await call_next(request)
            except Exception as exc:
                duration = (time.perf_counter() - start) * 1000
                _api_logger.error(
                    "<<< \033[91m500 ERROR\033[0m  %s %s  [%.1fms]  %s",
                    method, full_path, duration, str(exc)[:200],
                )
                raise

            duration = (time.perf_counter() - start) * 1000
            status_code = response.status_code

            # Màu theo status code
            if status_code < 300:
                color = "\033[92m"   # xanh lá
            elif status_code < 400:
                color = "\033[93m"   # vàng
            elif status_code < 500:
                color = "\033[91m"   # đỏ nhạt
            else:
                color = "\033[31m"   # đỏ đậm

            _api_logger.info(
                "<<< %s%d\033[0m  %s %s  [\033[96m%.1fms\033[0m]",
                color, status_code, method, full_path, duration,
            )

            return response

    app.add_middleware(APILoggingMiddleware)

    @app.on_event("startup")
    def _startup() -> None:
        _api_logger.info("=" * 60)
        _api_logger.info("  🚀 MedLink AI — FastAPI Backend đang khởi động...")
        _api_logger.info("=" * 60)
        init_db()
        _api_logger.info("  ✅ Database đã sẵn sàng. API đang lắng nghe request...")
        _api_logger.info("=" * 60)

    app.include_router(api_router)
    return app


try:
    app = create_app()
except ModuleNotFoundError:
    # Allow non-API tooling to import this package even when FastAPI is absent.
    app = None
except Exception:  # noqa: BLE001
    _api_logger.exception("Failed to create FastAPI app")
    raise
