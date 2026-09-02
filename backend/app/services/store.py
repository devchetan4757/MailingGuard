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

# Raw .eml bytes keyed by caseId, kept only so the "deep analyze this
# attachment" button on an existing case can re-extract the exact
# attachment bytes without asking the user to re-upload the file.
# Same in-memory-only lifetime/caveats as _STORE above.
_RAW_EML: dict[str, bytes] = {}


def add_case(record: dict) -> None:
    _STORE.append(record)


def save_raw_eml(case_id: str, content: bytes) -> None:
    _RAW_EML[case_id] = content


def get_raw_eml(case_id: str) -> bytes | None:
    return _RAW_EML.get(case_id)


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
