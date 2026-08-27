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
from typing import Callable, List

# Must match hashchain.GENESIS_HASH exactly — kept as a separate constant
# here (rather than imported) so case_store has zero dependency on the
# hashchain module's internals, per this file's framework-agnostic design.
GENESIS_HASH = "0" * 64

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


def seal_and_append(seal_fn: Callable[[str], dict]) -> dict:
    """
    Atomically read the current last hash, seal a new case against it, and
    append it — all under one lock, so two near-simultaneous requests can
    never read the same 'last hash' and both chain onto it.

    seal_fn: a function that takes the current last hash (str) and returns
             the freshly sealed case dict (e.g. lambda h: seal_case(data, h)).
             It must NOT touch case_store itself — just build the sealed dict.

    Returns the sealed case that was appended.
    """
    with _lock:
        last_hash = _ledger[-1].get("caseHash") if _ledger else GENESIS_HASH
        sealed = seal_fn(last_hash)
        _ledger.append(sealed)
        return sealed


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
