"""
GET /api/cases/:caseId/report — Epic 4 owner.

Calls your own build_case_pdf() from services/pdf_export.py.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()


@router.get("/cases/{case_id}/report")
def get_case_report(case_id: str):
    # TODO (Epic 4): look up the case, then:
    # from app.services.pdf_export import build_case_pdf
    # pdf_bytes = build_case_pdf(case)
    # return Response(content=pdf_bytes, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="Case not found.")
