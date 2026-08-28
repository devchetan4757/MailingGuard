"""
Router aggregator — integrator owned.

New endpoint file? Add one line here. Don't add routes directly in main.py.
"""

from fastapi import APIRouter

from app.api import analyze, cases, report
from app.api.integrations import gmail

api_router = APIRouter(prefix="/api")

api_router.include_router(analyze.router, tags=["analyze"])
api_router.include_router(cases.router, tags=["cases"])
api_router.include_router(report.router, tags=["report"])
api_router.include_router(gmail.router, tags=["gmail"])
