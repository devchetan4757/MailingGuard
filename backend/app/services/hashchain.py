"""
hashchain.py
------------
Tamper-evidence for MailingGuard case records.

Idea: every analysed email becomes a "case record". Each new case stores
the SHA-256 hash of (its own data + the previous case's hash). This links
every case into a chain, exactly like a lightweight blockchain — NOT a
distributed network (we're honest about that in the project doc), just a
tamper-EVIDENT log for a single organisation's data.

If anyone edits a past case record after the fact, its hash no longer
matches what the next record expects, and verify_chain() catches it
immediately.

Zero dependency on FastAPI or the DB — only deals in plain dicts.
Called from app/api/security_routes.py and app/store/case_store.py.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional


GENESIS_HASH = "0" * 64  # the "previous hash" for the very first case ever created


def _canonical_json(data: dict) -> str:
    """
    Turn a dict into a single, deterministic string so the same data
    always produces the same hash, regardless of key ordering.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_case_hash(case_data: dict, previous_hash: str) -> str:
    """
    Compute this case's hash from its own data + the hash of the case
    before it. This is what makes it a CHAIN, not just a checksum per file.

    case_data: the case record WITHOUT the 'caseHash' field itself
               (e.g. caseId, riskScore, severity, headerChecks, aiSignals,
               origin, relatedCases, analyzedAt)
    previous_hash: the caseHash of the most recently created case
                   (use GENESIS_HASH for the first case ever)
    """
    payload = _canonical_json(case_data) + previous_hash
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def seal_case(case_data: dict, previous_hash: str) -> dict:
    """
    Given a fresh case record (before it's saved), attach:
      - caseHash: this case's own hash
      - previousHash: what it was chained to
      - sealedAt: timestamp of sealing

    Returns a NEW dict — does not mutate the input.
    Call this right before writing the case to storage.
    """
    case_hash = compute_case_hash(case_data, previous_hash)
    sealed = dict(case_data)
    sealed["previousHash"] = previous_hash
    sealed["caseHash"] = case_hash
    sealed["sealedAt"] = datetime.now(timezone.utc).isoformat()
    return sealed


def verify_case(sealed_case: dict) -> bool:
    """
    Re-derive the hash of a single sealed case and check it matches what
    was stored. Returns True if untampered, False if the data has changed
    since it was sealed.
    """
    stored_hash = sealed_case.get("caseHash")
    previous_hash = sealed_case.get("previousHash")
    if stored_hash is None or previous_hash is None:
        return False

    # Recompute over everything except the fields hashchain.py itself added
    original = {
        k: v for k, v in sealed_case.items()
        if k not in ("caseHash", "previousHash", "sealedAt")
    }
    recomputed = compute_case_hash(original, previous_hash)
    return recomputed == stored_hash


def verify_chain(sealed_cases: list[dict]) -> dict:
    """
    Verify an entire ordered list of sealed cases (oldest first).

    Checks two things per case:
      1. Its own hash is still correct (verify_case) -> data wasn't edited
      2. Its previousHash matches the actual caseHash of the case before it
         -> no case was deleted, reordered, or inserted

    Returns a report dict:
      {
        "valid": bool,
        "brokenAt": caseId or None,
        "reason": str or None
      }
    """
    expected_previous = GENESIS_HASH

    for case in sealed_cases:
        if not verify_case(case):
            return {
                "valid": False,
                "brokenAt": case.get("caseId"),
                "reason": "Case data does not match its stored hash (edited after sealing).",
            }

        if case.get("previousHash") != expected_previous:
            return {
                "valid": False,
                "brokenAt": case.get("caseId"),
                "reason": "Chain link broken (a case was deleted, reordered, or inserted).",
            }

        expected_previous = case.get("caseHash")

    return {"valid": True, "brokenAt": None, "reason": None}


def get_last_hash(sealed_cases: list[dict]) -> str:
    """
    Convenience helper: given all existing sealed cases (oldest first),
    return the hash to chain the NEXT new case onto.
    Use GENESIS_HASH if there are no cases yet.
    """
    if not sealed_cases:
        return GENESIS_HASH
    return sealed_cases[-1].get("caseHash", GENESIS_HASH)


if __name__ == "__main__":
    # Quick self-test / demo — run: python -m app.services.hashchain
    case1 = {"caseId": "c1", "riskScore": 82, "severity": "red"}
    case2 = {"caseId": "c2", "riskScore": 15, "severity": "green"}

    sealed1 = seal_case(case1, get_last_hash([]))
    sealed2 = seal_case(case2, get_last_hash([sealed1]))

    chain = [sealed1, sealed2]
    print("Chain valid?", verify_chain(chain))

    # Simulate tampering
    chain[0] = dict(chain[0])
    chain[0]["riskScore"] = 5  # someone secretly lowered a score
    print("After tampering:", verify_chain(chain))
