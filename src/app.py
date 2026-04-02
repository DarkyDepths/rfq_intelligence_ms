"""
FastAPI application factory for rfq_intelligence_ms.

Creates the FastAPI app instance with:
- CORS middleware configuration
- Exception handlers (AppError → JSON, validation errors, unhandled)
- Route registration under /intelligence/v1 prefix
- Health-check endpoint at /health (via health_routes)
- OpenAPI metadata (title, version, description)

Entry point: create_app() returns the configured FastAPI instance.
Run with: uvicorn src.app:app --reload --port 8001
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from fastapi import APIRouter

from src.config.settings import settings
from src.utils.exceptions import AppError


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    App factory pattern.

    Tests can call create_app() with a different config
    (e.g. test database) without affecting the real app.
    """

    app = FastAPI(
        title="rfq_intelligence_ms",
        version="0.1.0",
        description="RFQ Intelligence Service — Analytical Microservice for RFQMGMT Platform",
    )

    # ── CORS Middleware ────────────────────────────────
    origins = [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global Exception Handler — AppError ───────────
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, error: AppError):
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.message},
        )

    # ── Validation Error Handler ──────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_msgs = []
        for err in exc.errors():
            loc = ".".join([str(x) for x in err["loc"]])
            msg = err["msg"]
            error_msgs.append(f"{loc}: {msg}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation failed: " + " | ".join(error_msgs),
            },
        )

    # ── Unhandled Exception Handler ───────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception during request", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ── Route Registration ────────────────────────────
    from src.routes.health_routes import router as health_router
    from src.routes.intelligence_routes import router as intelligence_router
    from src.routes.batch_seed_run_routes import router as batch_seed_run_router
    from src.routes.manual_lifecycle_routes import router as manual_lifecycle_router
    from src.routes.workbook_parser_routes import router as workbook_parser_router

    # Health is at root level (no prefix)
    app.include_router(health_router)

    # All intelligence endpoints under /intelligence/v1
    v1 = APIRouter(prefix="/intelligence/v1")
    v1.include_router(intelligence_router)
    v1.include_router(batch_seed_run_router)
    v1.include_router(manual_lifecycle_router)
    v1.include_router(workbook_parser_router)
    app.include_router(v1)

    return app


# ── Module-level app instance ─────────────────────────
# uvicorn looks for this: uvicorn src.app:app --reload --port 8001
app = create_app()
