"""
Epic 4 — reporting: downloadable PDF case file.

Owner: whoever is assigned Epic 4 in OWNERSHIP.md.
Remember to run any email-derived text through
`app.core.security.escape_for_report` before it goes into the PDF.

CONTRACT:
    build_case_pdf(case: dict) -> bytes
        `case` is shaped like schemas.AnalyzeResponse (see
        app/models/schemas.py). Returns raw PDF bytes.
"""

from app.core.security import escape_for_report


def build_case_pdf(case: dict) -> bytes:
    # TODO (Epic 4): use reportlab (see /mnt/skills/public/pdf/SKILL.md style
    # patterns) to render: score + severity, header checklist, AI summary,
    # origin trace, related cases, and the caseHash - escape any raw email
    # text first with escape_for_report().
    _ = escape_for_report(case.get("aiSignals", {}).get("summary", ""))
    return b""
