"""
case_store.py
-------------
Minimal in-memory ledger of sealed case records, ordered oldest -> newest.

This is intentionally a plain Python list behind a small interface, so it
can be swapped for a real database later (Mongo, Postgres, etc.) without
any of app/api/security_routes.py needing to change — every method here
just needs to keep returning/accepting the same shapes.

NOT thread-safe / multi-process safe. Fine for a single dev server or demo;
replace with a real datastore before this goes anywhere near production.
"""

from threading import Lock
from typing import List

_lock = Lock()
_ledger: List[dict] = []


def all_cases() -> List[dict]:
    """Return every sealed case, oldest first."""
    with _lock:
        return list(_ledger)


def append_case(sealed_case: dict) -> None:
    """Add a newly sealed case to the end of the ledger."""
    with _lock:
        _ledger.append(sealed_case)


def clear() -> None:
    """Wipe the ledger. Used by the demo 'reset' action only."""
    with _lock:
        _ledger.clear()


def tamper_with_case(case_id: str, new_risk_score: int) -> bool:
    """
    Demo-only helper: deliberately mutate a stored case's riskScore
    WITHOUT resealing it, so the UI can demonstrate verify_chain()
    catching real tampering. Returns True if a matching case was found.
    """
    with _lock:
        for case in _ledger:
            if case.get("caseId") == case_id:
                case["riskScore"] = new_risk_score
                return True
        return False
