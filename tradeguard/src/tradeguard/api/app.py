"""Main FastAPI application for TradeGuard."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from tradeguard.api.routes_auth import router as auth_router
from tradeguard.api.routes_ml import router as ml_router
from tradeguard.api.routes_payments import router as payments_router
from tradeguard.api.routes_review import router as review_router
from tradeguard.api.routes_shipments import router as shipments_router
from tradeguard.core.config import settings
from tradeguard.db.session import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Cargo Document Intelligence + Risk-Gated Payment Escrow Platform",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize tables
    init_db()

    # Mount API routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(shipments_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(review_router, prefix="/api/v1")
    app.include_router(ml_router, prefix="/api/v1")

    # Locate frontend dashboard
    frontend_index = Path(__file__).resolve().parents[3] / "frontend" / "index.html"
    if not frontend_index.exists():
        # Fallback to local project path
        frontend_index = Path("./tradeguard/frontend/index.html").resolve()

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
        }

    @app.get("/metrics")
    def metrics():
        return {
            "service": "tradeguard-api",
            "t_low": settings.RISK_THRESHOLD_LOW,
            "t_high": settings.RISK_THRESHOLD_HIGH,
            "ocr_gate": settings.OCR_CONFIDENCE_GATE,
        }

    @app.get("/", response_class=FileResponse)
    def index():
        if frontend_index.exists():
            return FileResponse(frontend_index)
        return HTMLResponse("<h1>TradeGuard API is running. Visit /docs for Swagger UI</h1>")

    @app.get("/dashboard", response_class=FileResponse)
    def dashboard():
        if frontend_index.exists():
            return FileResponse(frontend_index)
        return HTMLResponse("<h1>TradeGuard Dashboard file not found</h1>")

    return app


app = create_app()
