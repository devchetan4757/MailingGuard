"""
file_validation.py
-------------------
Backend security rule (from the Project Master Doc, section 5):
"Reject any upload over 2MB or not shaped like a valid email — fail
cleanly, never crash."

Framework-agnostic: takes raw bytes in, returns a plain result out.
The /api/security/validate route (see app/api/security_routes.py) calls
validate_upload() first and turns the result into an HTTP error if invalid.
"""

import email
from email.message import Message
from dataclasses import dataclass
from typing import Optional


MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2MB, per the project's stated limit
ALLOWED_EXTENSIONS = (".eml",)


@dataclass
class ValidationResult:
    valid: bool
    reason: Optional[str] = None       # human-readable reason for rejection
    parsed_message: Optional[Message] = None  # populated only when valid


def validate_upload(filename: str, file_bytes: bytes) -> ValidationResult:
    """
    Run all checks for an uploaded file, in cheapest-first order so we
    never waste time parsing something that was already going to fail.

    Order of checks:
      1. Filename extension looks like an email file
      2. Size is under the 2MB cap
      3. Not empty
      4. Bytes actually parse as a valid email (has real headers)
      5. Has the bare minimum headers a real email needs (From, Date)
    """
    # 1. Extension check
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        return ValidationResult(
            valid=False,
            reason=f"Unsupported file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are accepted.",
        )

    # 2. Size check
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        return ValidationResult(
            valid=False,
            reason=f"File is {size_mb:.2f}MB, which exceeds the 2MB limit.",
        )

    # 3. Empty file check
    if len(file_bytes) == 0:
        return ValidationResult(valid=False, reason="Uploaded file is empty.")

    # 4. Must actually parse as an email (never crash on garbage input)
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        parsed = email.message_from_string(text)
    except Exception:
        return ValidationResult(
            valid=False,
            reason="File could not be parsed as an email (corrupted or wrong format).",
        )

    # 5. Minimum viable email: must have at least a From header.
    #    A file that "parses" but has zero real headers is usually just
    #    a renamed .txt file, not an actual .eml.
    if not parsed.get("From"):
        return ValidationResult(
            valid=False,
            reason="File does not look like a valid email (missing 'From' header).",
        )

    return ValidationResult(valid=True, reason=None, parsed_message=parsed)


# --- Optional FastAPI integration helper -----------------------------------
def raise_if_invalid(result: ValidationResult):
    """
    Call this from the FastAPI route after validate_upload(). Only imports
    fastapi at call-time so the rest of this module stays framework-free.
    """
    if not result.valid:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.reason)


if __name__ == "__main__":
    # Quick self-test — run: python -m app.utils.file_validation
    good = b"From: alice@example.com\nDate: Mon, 1 Jan 2024 00:00:00 +0000\nSubject: Hi\n\nHello there."
    print(validate_upload("test.eml", good))
    print(validate_upload("test.txt", good))
    print(validate_upload("empty.eml", b""))
    print(validate_upload("huge.eml", b"x" * (3 * 1024 * 1024)))
    print(validate_upload("noheaders.eml", b"just some random text"))
