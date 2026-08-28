"""
Epic 1 — Email upload & parsing (Layer 1, reused/adapted tech).

Basic version: uses Python's stdlib `email` module to pull headers,
auth results, and body text directly, so the pipeline works end to end
without pulling in the external EML-Parser library yet. Swap in a more
thorough parser later without changing PARSED_SHAPE.

CONTRACT:
    parse_eml(content: bytes) -> dict
        Must always return a dict shaped like PARSED_SHAPE below, even on a
        partially-broken email - fill fields you can't determine with None
        rather than raising, so scoring.py always has something to read.
        Only raise for validate_upload()'s ValueError case, handled upstream.
"""

import re
from email import message_from_bytes
from email.utils import parseaddr

PARSED_SHAPE = {
    "from_display_name": None,   # str | None
    "from_domain": None,         # str | None
    "reply_to_domain": None,     # str | None
    "received_chain": [],        # list[str], earliest hop first
    "origin_ip": None,           # str | None - earliest likely-real hop
    "spf": "none",               # "pass" | "fail" | "none"
    "dkim": "none",              # "pass" | "fail" | "none"
    "dmarc": "none",             # "pass" | "fail" | "none"
    "subject": None,             # str | None
    "body_text": "",             # str, plain text only - never render as HTML
}

_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_PRIVATE_IP_PREFIXES = ("10.", "127.", "192.168.", "169.254.")


def _domain_of(header_value):
    if not header_value:
        return None
    _, addr = parseaddr(header_value)
    if "@" not in addr:
        return None
    domain = addr.rsplit("@", 1)[-1].strip().lower()
    return domain or None


def _auth_result(auth_header, mechanism):
    if not auth_header:
        return "none"
    match = re.search(rf"{mechanism}=(\w+)", auth_header, re.IGNORECASE)
    if not match:
        return "none"
    value = match.group(1).lower()
    if value == "pass":
        return "pass"
    if value in ("fail", "softfail", "permerror", "temperror"):
        return "fail"
    return "none"


def _first_public_ip(received_headers_earliest_first):
    for hop in received_headers_earliest_first:
        for candidate in _IP_RE.findall(hop):
            if not candidate.startswith(_PRIVATE_IP_PREFIXES):
                return candidate
    return None


def _body_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    payload = part.get_payload(decode=True)
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    continue
        return ""

    if msg.get_content_type() == "text/plain":
        try:
            payload = msg.get_payload(decode=True)
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            return ""

    return ""


def parse_eml(content: bytes) -> dict:
    result = dict(PARSED_SHAPE)
    result["received_chain"] = []

    try:
        msg = message_from_bytes(content)
    except Exception:
        return result

    from_header = msg.get("From")
    if from_header:
        display_name, _ = parseaddr(from_header)
        result["from_display_name"] = display_name or None
        result["from_domain"] = _domain_of(from_header)

    reply_to_header = msg.get("Reply-To")
    result["reply_to_domain"] = (
        _domain_of(reply_to_header) if reply_to_header else result["from_domain"]
    )

    result["subject"] = msg.get("Subject")

    auth_results = msg.get("Authentication-Results")
    result["spf"] = _auth_result(auth_results, "spf")
    result["dkim"] = _auth_result(auth_results, "dkim")
    result["dmarc"] = _auth_result(auth_results, "dmarc")

    # Received headers are newest-first in a raw message; reverse so the
    # earliest hop (closest to the true origin) comes first.
    received_headers = list(reversed(msg.get_all("Received") or []))
    result["received_chain"] = received_headers
    result["origin_ip"] = _first_public_ip(received_headers)

    result["body_text"] = _body_text(msg)

    return result
