"""
GET /api/cases and GET /api/cases/:caseId — Epic 4 owner.

Reads from the shared in-memory store in app/services/store.py (written to
by analyze.py). Swap store.py's internals for a real database later —
this file doesn't need to change when that happens.
"""

from fastapi import APIRouter, HTTPException

from app.services import store
from app.models.schemas import CaseSummary, AnalyzeResponse

router = APIRouter()


@router.get("/cases", response_model=list[CaseSummary])
def list_cases():
    return [
        {
            "caseId": record["caseId"],
            "riskScore": record["response"]["riskScore"],
            "severity": record["response"]["severity"],
            "analyzedAt": record["analyzedAt"],
        }
        for record in store.all_cases()
    ]


@router.get("/cases/{case_id}", response_model=AnalyzeResponse)
def get_case(case_id: str):
    record = store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found.")
    return record["response"]
