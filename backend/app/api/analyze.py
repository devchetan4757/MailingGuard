"""
POST /api/analyze — integrator-owned.

This file just calls each teammate's service in order (master doc, section 5,
"core backend responsibilities"). If your feature needs different inputs
from this file, don't edit the orchestration here - change your own
function's internals to accept what you already get.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.security import validate_upload
from app.services.parsing import parse_eml
from app.services.scoring import score_email
from app.services.geolocation import locate_ip
from app.services.similarity import find_related_cases
from app.services.hashchain import compute_case_hash
from app.services import store
from app.models.schemas import AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_email(file: UploadFile = File(...)):
    content = await file.read()

    try:
        validate_upload(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    parsed = parse_eml(content)                       # Epic 1
    score = score_email(parsed)                        # Epic 2
    origin = locate_ip(parsed.get("origin_ip") or "")   # Epic 3
    related = find_related_cases(parsed, origin, store.all_cases())  # Epic 3

    case_id = f"case-{len(store.all_cases()) + 1}"
    previous_hash = store.last_case_hash()
    case_hash = compute_case_hash(parsed, previous_hash)  # Epic 5

    response = {
        "caseId": case_id,
        "riskScore": score["riskScore"],
        "severity": score["severity"],
        "headerChecks": {
            "spf": parsed["spf"],
            "dkim": parsed["dkim"],
            "dmarc": parsed["dmarc"],
            "senderDomainMismatch": parsed.get("from_domain") != parsed.get("reply_to_domain"),
        },
        "aiSignals": {
            "urgencyLanguage": score["urgencyLanguage"],
            "impersonationScore": score["impersonationScore"],
            "summary": score["summary"],
        },
        "origin": origin,
        "relatedCases": related,
        "caseHash": case_hash,
    }

    store.add_case({
        **parsed,
        "caseId": case_id,
        "analyzedAt": datetime.now(timezone.utc).isoformat(),
        "response": response,
    })

    return response

