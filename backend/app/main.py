"""
MailGuard FastAPI application.

Entry point for the MailGuard backend.

Run from the backend directory with:

    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyze import router as analyze_router
from app.api.cases import router as cases_router
from app.api.report import router as report_router
from app.api.origin import router as origin_router
from app.api.integrations.gmail import router as gmail_router


# ---------------------------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MailGuard API",
    description=(
        "Email security analysis backend for MailGuard."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],

    allow_credentials=True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# ---------------------------------------------------------------------------
# ANALYSIS API
# ---------------------------------------------------------------------------

app.include_router(
    analyze_router,
    prefix="/api",
    tags=[
        "Email Analysis",
    ],
)


# ---------------------------------------------------------------------------
# CASES / HISTORY API
# ---------------------------------------------------------------------------

app.include_router(
    cases_router,
    prefix="/api",
    tags=[
        "Cases",
    ],
)


# ---------------------------------------------------------------------------
# REPORTING API
# ---------------------------------------------------------------------------

app.include_router(
    report_router,
    prefix="/api",
    tags=[
        "Reporting",
    ],
)


# ---------------------------------------------------------------------------
# GMAIL INTEGRATION API
# ---------------------------------------------------------------------------

app.include_router(
    gmail_router,
    prefix="/api",
    tags=[
        "Gmail Integration",
    ],
)


# ---------------------------------------------------------------------------
# ORIGIN INTELLIGENCE API
# ---------------------------------------------------------------------------

app.include_router(
    origin_router,
    prefix="/api",
    tags=[
        "Origin Intelligence",
    ],
)


# ---------------------------------------------------------------------------
# HEALTH / STATUS
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "MailGuard API",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mailguard",
        "analyzer": "enabled",
    }


@app.get("/api/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "mailguard",
        "analyzer": "enabled",
    }
