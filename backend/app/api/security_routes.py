"""
security_routes.py
-------------------
HTTP surface for the Security & Integrity module. Thin glue only — all
real logic stays in app/utils and app/services so it keeps working
outside of FastAPI (see the docstrings in those files).

Endpoints:
  POST /api/security/validate         -> upload an .eml, validate + seal it into the ledger
  GET  /api/security/ledger           -> list every sealed case (oldest first)
  GET  /api/security/verify-chain     -> run tamper-evidence check over the whole ledger
  POST /api/security/sanitize-preview -> sanitize arbitrary text, report injection attempts
  POST /api/security/demo/seed        -> add sample sealed cases (for an empty demo ledger)
  POST /api/security/demo/tamper      -> deliberately corrupt a case, to demonstrate detection
  POST /api/security/demo/reset       -> wipe the ledger back to empty
"""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.utils.file_validation import validate_upload
from app.utils.sanitize import sanitize_for_display, contains_injection_attempt
from app.services.hashchain import seal_case, verify_chain
from app.store import case_store


router = APIRouter(prefix="/api/security", tags=["security-integrity"])

# Demo-only routes (/demo/seed, /demo/tamper, /demo/reset) are destructive
# and have NO authentication. They must never be reachable outside a local
# demo/dev environment. Gated behind an explicit env var, defaulting ON for
# local development — set DEMO_MODE=false (or unset it) before any real
# deployment so these routes 404 instead of executing.
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


def _require_demo_mode():
    """Call at the top of every /demo/* route. Hides the route entirely
    (404, not 403) when DEMO_MODE is off, so its existence isn't even
    revealed to an unauthenticated caller."""
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")


class SanitizeRequest(BaseModel):
    text: str


class TamperRequest(BaseModel):
    caseId: str
    newRiskScore: int = 5


@router.post("/validate")
async def validate_email_upload(file: UploadFile = File(...)):
    """Validate an uploaded .eml file, then seal it into the tamper-evident ledger."""
    file_bytes = await file.read()
    result = validate_upload(file.filename, file_bytes)

    if not result.valid:
        return {"valid": False, "reason": result.reason, "case": None}

    subject = sanitize_for_display(result.parsed_message.get("Subject", "(no subject)"))
    sender = sanitize_for_display(result.parsed_message.get("From", "(unknown sender)"))
    flagged = contains_injection_attempt(subject) or contains_injection_attempt(sender)

    case_data = {
        "caseId": f"CASE-{uuid.uuid4().hex[:8].upper()}",
        "filename": file.filename,
        "subject": subject,
        "sender": sender,
        "sizeBytes": len(file_bytes),
        "injectionFlagged": flagged,
        "analyzedAt": datetime.now(timezone.utc).isoformat(),
    }

    # Atomic: reads the last hash and appends the newly sealed case under
    # one lock, so two near-simultaneous uploads can never chain onto the
    # same previous hash (see case_store.seal_and_append docstring).
    sealed = case_store.seal_and_append(lambda previous_hash: seal_case(case_data, previous_hash))

    return {"valid": True, "reason": None, "case": sealed}


@router.get("/ledger")
def get_ledger():
    """Return the full sealed-case ledger, oldest first."""
    return {"cases": case_store.all_cases()}


@router.get("/verify-chain")
def verify_ledger():
    """Run the tamper-evidence check across every sealed case."""
    return verify_chain(case_store.all_cases())


@router.post("/sanitize-preview")
def sanitize_preview(payload: SanitizeRequest):
    """Show raw vs. sanitized text side by side, and flag injection attempts."""
    return {
        "raw": payload.text,
        "sanitized": sanitize_for_display(payload.text),
        "injectionFlagged": contains_injection_attempt(payload.text),
    }


@router.post("/demo/seed")
def seed_demo_data():
    """Populate the ledger with a few sample sealed cases for demo purposes."""
    _require_demo_mode()
    samples = [
        {"filename": "invoice_review.eml", "subject": "Invoice #4471 overdue", "sender": "billing@vendor-co.com", "sizeBytes": 18320, "injectionFlagged": False},
        {"filename": "password_reset.eml", "subject": "Your account needs verification", "sender": "no-reply@secure-login-update.com", "sizeBytes": 24110, "injectionFlagged": True},
        {"filename": "quarterly_report.eml", "subject": "Q3 numbers attached", "sender": "priya.sharma@company.com", "sizeBytes": 9880, "injectionFlagged": False},
    ]
    for sample in samples:
        case_data = {
            "caseId": f"CASE-{uuid.uuid4().hex[:8].upper()}",
            "analyzedAt": datetime.now(timezone.utc).isoformat(),
            **sample,
        }
        case_store.seal_and_append(lambda previous_hash, cd=case_data: seal_case(cd, previous_hash))

    return {"cases": case_store.all_cases()}


@router.post("/demo/tamper")
def tamper_demo_case(payload: TamperRequest):
    """Deliberately corrupt a stored case without resealing it, to prove verify-chain catches it."""
    _require_demo_mode()
    found = case_store.tamper_with_case(payload.caseId, payload.newRiskScore)
    return {"tampered": found}


@router.post("/demo/reset")
def reset_ledger():
    """Wipe the ledger back to empty."""
    _require_demo_mode()
    case_store.clear()
    return {"cases": []}
