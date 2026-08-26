"""
sanitize.py
-----------
Backend + frontend security rule (Project Master Doc, section 5 & 9):
"Escape all email-derived text before inserting it into the PDF export."
"Treat all displayed email content as untrusted — always plain text,
never raw HTML, no exceptions."

Why this matters: the whole point of this platform is analysing emails
written by ATTACKERS. A malicious sender could put a <script> tag or
HTML in the subject/body specifically hoping our dashboard or PDF
renders it. This module is the one place all of that gets neutralised
before it reaches a browser or a PDF library.

Standard-library only (html.escape) — no new dependency added to
requirements.txt.
"""

import html
import re


# Characters/sequences that indicate someone tried to sneak in markup or
# a script, even after basic HTML-escaping. Used only for flagging in
# logs/UI ("this email attempted a markup injection") — escaping below is
# what actually neutralises it, this is just visibility.
SUSPICIOUS_PATTERNS = (
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),   # onclick=, onerror=, etc.
    re.compile(r"<\s*iframe", re.IGNORECASE),
)


def sanitize_for_display(text: str) -> str:
    """
    Make email-derived text safe to insert into the frontend (as text
    content, e.g. React {variable} interpolation — which already escapes,
    but this is the belt-and-braces version for anywhere raw strings get
    concatenated, e.g. into a title attribute or a non-React template).

    Never returns HTML — always plain, escaped text.
    """
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def sanitize_for_pdf(text: str) -> str:
    """
    Escape email-derived text before it goes into the PDF case file.
    Most PDF libraries (reportlab, fpdf2, weasyprint-from-html) either
    use XML/HTML-like markup internally or are vulnerable to control
    characters breaking layout — escaping covers both cases safely.
    """
    if text is None:
        return ""
    escaped = html.escape(str(text), quote=True)
    # Strip control characters (except newline/tab) that could corrupt
    # PDF structure or terminal-style injection in some renderers.
    escaped = "".join(
        ch for ch in escaped if ch in ("\n", "\t") or ord(ch) >= 32
    )
    return escaped


def contains_injection_attempt(text: str) -> bool:
    """
    Flag (does NOT block) content that looks like it's trying to inject
    markup/scripts. Useful as an extra AI-risk-engine signal — e.g. "this
    email attempted a markup injection" can bump the fraud score, since
    legitimate senders never do this.
    """
    if not text:
        return False
    return any(pattern.search(text) for pattern in SUSPICIOUS_PATTERNS)


def sanitize_case_record(case: dict, text_fields: list[str]) -> dict:
    """
    Convenience helper: given a case record dict and a list of keys that
    hold raw email-derived text (e.g. ["subject", "senderDisplayName",
    "bodySummary"]), return a NEW dict with those fields sanitized for
    display. Does not mutate the input.
    """
    sanitized = dict(case)
    for field in text_fields:
        if field in sanitized:
            sanitized[field] = sanitize_for_display(sanitized[field])
    return sanitized


if __name__ == "__main__":
    # Quick self-test — run: python -m app.utils.sanitize
    malicious = '<script>alert("stolen cookies")</script> Urgent: reset your password'
    print("Display-safe:", sanitize_for_display(malicious))
    print("PDF-safe:", sanitize_for_pdf(malicious))
    print("Injection attempt detected?", contains_injection_attempt(malicious))
    print("Clean text flagged?", contains_injection_attempt("Please review the attached invoice."))
