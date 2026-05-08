from __future__ import annotations

from typing import Any

def create_app() -> Any:
    from fastapi import FastAPI

    from .api import router as api_router
    from .database import init_db

    app = FastAPI(
        title="Drug-Disease AI API",
        version="1.0.0",
        description="API du doan lien ket Thuoc - Benh voi GCN va quan tri du lieu.",
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    app.include_router(api_router)
    return app


try:
    app = create_app()
except Exception:  # noqa: BLE001
    # Khong chan cac module AI/CLI khi moi truong chua cai FastAPI.
    app = None
