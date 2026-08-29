"""
Epic 5 — security & integrity: hash-chained case records.

Owner: whoever is assigned Epic 5 in OWNERSHIP.md.
This gives tamper-evidence for our own case records - it is not a
distributed blockchain, don't over-build it (see master doc, section 13).

CONTRACT:
    compute_case_hash(case_data: dict, previous_hash: str | None) -> str
        Deterministic hash of this case chained to the previous one.

    verify_chain(cases_in_order: list[dict]) -> bool
        Walks the chain and confirms no record's hash was tampered with.
"""

import hashlib
import json


def compute_case_hash(case_data: dict, previous_hash: str | None) -> str:
    payload = json.dumps(case_data, sort_keys=True, default=str)
    combined = f"{previous_hash or ''}:{payload}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def verify_chain(cases_in_order: list[dict]) -> bool:
    # TODO (Epic 5): recompute each hash from its stored data + the previous
    # record's hash and compare against what's stored. Return False on the
    # first mismatch.
    previous_hash = None
    for case in cases_in_order:
        expected = compute_case_hash(case.get("data", {}), previous_hash)
        if case.get("caseHash") != expected:
            return False
        previous_hash = case.get("caseHash")
    return True
