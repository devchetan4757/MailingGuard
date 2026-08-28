"""
Shared case store — temporary in-memory persistence.

Both analyze.py (writes) and cases.py (reads) import this so a case
uploaded via POST /api/analyze immediately shows up in GET /api/cases.
Swap this for a real database later without changing the function
names/shapes other files depend on.

CONTRACT:
    add_case(record: dict) -> None
        `record` must include: caseId, analyzedAt (ISO string), response
        (dict shaped like schemas.AnalyzeResponse), plus the raw parsed
        fields needed for similarity matching (from_domain, origin_ip,
        body_text, ...).
    all_cases() -> list[dict]
        Every stored record, oldest first.
    get_case(case_id: str) -> dict | None
    last_case_hash() -> str | None
"""

_STORE: list[dict] = []


def add_case(record: dict) -> None:
    _STORE.append(record)


def all_cases() -> list[dict]:
    return list(_STORE)


def get_case(case_id: str) -> dict | None:
    for record in _STORE:
        if record.get("caseId") == case_id:
            return record
    return None


def last_case_hash() -> str | None:
    if not _STORE:
        return None
    return _STORE[-1]["response"].get("caseHash")
