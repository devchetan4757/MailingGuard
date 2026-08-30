"""
GET /api/cases/:caseId/report          — Epic 4 owner. Attachment download.
GET /api/cases/:caseId/report/preview  — Epic 4 owner. Inline preview (same
                                          PDF, rendered in-browser instead of
                                          forcing a save dialog) for the
                                          "download interface" screen.

Both look up the case in the shared store, build a PDF via
services/pdf_export.build_case_pdf(), and stream it back.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services import store
from app.services.pdf_export import build_case_pdf

router = APIRouter()


def _previous_hash_for(case_id: str) -> str | None:
    """
    Walk the store in insertion order and return the caseHash of the
    record immediately before this one — the store doesn't persist
    previousHash directly, but the chain order is preserved by
    store.all_cases().
    """
    cases = store.all_cases()
    for index, record in enumerate(cases):
        if record.get("caseId") == case_id:
            if index == 0:
                return None
            return cases[index - 1].get("response", {}).get("caseHash")
    return None


def _build_pdf_for_case(case_id: str) -> bytes:
    record = store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found.")

    # build_case_pdf expects an AnalyzeResponse-shaped dict, plus a
    # couple of convenience keys (analyzedAt, previousHash) that live
    # outside AnalyzeResponse but are needed for the report header.
    case = dict(record.get("response") or {})
    case["analyzedAt"] = record.get("analyzedAt", "")
    case["previousHash"] = _previous_hash_for(case_id)

    try:
        return build_case_pdf(case)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {exc}",
        ) from exc


@router.get("/cases/{case_id}/report")
def get_case_report(case_id: str):
    pdf_bytes = _build_pdf_for_case(case_id)
    filename = f"{case_id}-mailguard-report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases/{case_id}/report/preview")
def get_case_report_preview(case_id: str):
    """
    Same PDF as the download route, but with an `inline` disposition so it
    can be dropped straight into an <iframe>/<embed> for a live preview
    instead of triggering a browser download prompt.
    """
    pdf_bytes = _build_pdf_for_case(case_id)
    filename = f"{case_id}-mailguard-report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
