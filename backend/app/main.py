"""
App entrypoint — integrator owned.

Keep this file thin: CORS setup + mounting the api_router. Feature logic
belongs in services/, endpoint definitions belong in api/.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "project": "MailingGuard",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }
