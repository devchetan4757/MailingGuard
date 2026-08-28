"""
Epic 5 — Security & integrity.

Owner: whoever is assigned Epic 5 in OWNERSHIP.md.
You edit this file freely. Other files import these two functions —
keep their names and argument shapes stable once someone else depends on them.

CONTRACT:
    validate_upload(filename: str, content: bytes) -> None
        Raises ValueError with a clear message if the file should be rejected.
        Must never raise an unhandled exception - the api layer expects
        ValueError specifically for "bad upload" cases.

    escape_for_report(text: str) -> str
        Used before any email-derived text is inserted into the PDF export
        (see master doc, section 5, "Escape all email-derived text").
"""

from app.core.config import settings


def validate_upload(filename: str, content: bytes) -> None:
    # TODO (Epic 5): real validation.
    # - reject anything not shaped like a valid .eml (check headers, not just extension)
    # - reject over settings.MAX_UPLOAD_BYTES
    # - never let this raise anything other than ValueError
    if not filename.lower().endswith(".eml"):
        raise ValueError("Only .eml files are accepted.")

    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise ValueError("File is too large (max 2MB).")


def escape_for_report(text: str) -> str:
    # TODO (Epic 5): proper escaping for whatever the PDF renderer needs
    # (reportlab Paragraph uses a small XML-like markup - escape <, >, & at least).
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
