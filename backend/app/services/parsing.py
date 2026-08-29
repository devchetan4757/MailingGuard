"""
MailGuard parser adapter.

Integrates the real analyzer from backend.zip with MailGuard's existing
PARSED_SHAPE contract.

The analyzer provides:
    - decoded metadata
    - authentication results
    - body text/html
    - URLs
    - attachments
    - Received chain
    - header relationship findings

MailGuard's downstream services continue consuming the original fields,
while the additional fields are retained for scoring, storage and the
dashboard.
"""

from __future__ import annotations

import re
import tempfile
import os

from app.services.email_parser import parse_email


PARSED_SHAPE = {
    "from_display_name": None,
    "from_domain": None,
    "reply_to_domain": None,
    "received_chain": [],
    "origin_ip": None,
    "spf": "none",
    "dkim": "none",
    "dmarc": "none",
    "subject": None,
    "body_text": "",

    # Additional analyzer data.
    "from": None,
    "to": None,
    "cc": None,
    "bcc": None,
    "date": None,
    "reply_to": None,
    "message_id": None,
    "return_path": None,

    "body_html": "",

    "urls": [],
    "attachments": [],
    "header_findings": [],

    "authentication": {},
    "metadata": {},
}


_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b"
)

_IP_RE = re.compile(
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
)

_PRIVATE_IP_PREFIXES = (
    "10.",
    "127.",
    "192.168.",
    "169.254.",
)


def _copy_shape() -> dict:
    """
    Create a fresh result without sharing mutable lists between calls.
    """

    result = dict(PARSED_SHAPE)

    result["received_chain"] = []
    result["urls"] = []
    result["attachments"] = []
    result["header_findings"] = []
    result["authentication"] = {}
    result["metadata"] = {}

    return result


def _domain_of(value):
    """
    Extract a domain from an email address/header.
    """

    if not value:
        return None

    match = _EMAIL_RE.search(
        str(value)
    )

    if not match:
        return None

    address = match.group(0)

    try:
        return address.rsplit(
            "@",
            1,
        )[1].lower()
    except IndexError:
        return None


def _first_public_ip(
    received_chain,
):
    """
    Find the first non-private IPv4 address in the earliest-first
    Received chain.
    """

    for hop in received_chain or []:

        for candidate in _IP_RE.findall(
            str(hop)
        ):

            if not candidate.startswith(
                _PRIVATE_IP_PREFIXES
            ):
                return candidate

    return None


def _authentication_result(
    authentication,
    name,
):
    """
    Convert the analyzer's authentication object into MailGuard's
    existing pass/fail/none contract.
    """

    item = (
        authentication.get(name)
        if isinstance(
            authentication,
            dict,
        )
        else None
    )

    if isinstance(
        item,
        dict,
    ):
        value = str(
            item.get(
                "result",
                "unknown",
            )
            or "unknown"
        ).lower()

    else:
        value = str(
            item or "unknown"
        ).lower()

    if value == "pass":
        return "pass"

    if value in {
        "fail",
        "softfail",
        "permerror",
        "temperror",
    }:
        return "fail"

    return "none"


def _normalise_urls(urls):
    """
    Keep the analyzer's URLs while making sure the API receives a
    predictable list.
    """

    if not isinstance(
        urls,
        list,
    ):
        return []

    return [
        str(url)
        for url in urls
        if url
    ]


def _normalise_attachments(
    attachments,
):
    """
    Preserve the real attachment findings produced by the analyzer.
    """

    if not isinstance(
        attachments,
        list,
    ):
        return []

    result = []

    for attachment in attachments:

        if not isinstance(
            attachment,
            dict,
        ):
            continue

        result.append(
            {
                "filename": attachment.get(
                    "filename"
                ),
                "content_type": attachment.get(
                    "content_type"
                ),
                "size": int(
                    attachment.get(
                        "size",
                        0,
                    )
                    or 0
                ),
                "extension": attachment.get(
                    "extension"
                ),
                "suspicious": bool(
                    attachment.get(
                        "suspicious",
                        False,
                    )
                ),
                "reason": attachment.get(
                    "reason"
                ),
            }
        )

    return result


def _normalise_header_findings(
    findings,
):
    """
    Preserve the analyzer's header relationship findings.
    """

    if not isinstance(
        findings,
        list,
    ):
        return []

    result = []

    for finding in findings:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        result.append(
            {
                "type": finding.get(
                    "type",
                    "header_anomaly",
                ),
                "severity": finding.get(
                    "severity",
                    "low",
                ),
                "message": finding.get(
                    "message",
                    "Header anomaly detected.",
                ),
            }
        )

    return result


def parse_eml(
    content: bytes,
) -> dict:
    """
    Parse an uploaded .eml using the real analyzer.

    The analyzer expects a filesystem path, therefore the bytes are written
    only to a temporary file for the duration of the analysis.
    """

    result = _copy_shape()

    if not content:
        return result

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".eml",
            prefix="mailguard_",
            delete=False,
        ) as temporary_file:

            temporary_file.write(
                content
            )

            temporary_path = (
                temporary_file.name
            )

        analyzed = parse_email(
            temporary_path
        )

    except Exception:
        # MailGuard's original contract requires a safe partial result
        # rather than breaking the complete analysis pipeline.
        return result

    finally:
        if (
            temporary_path
            and os.path.exists(
                temporary_path
            )
        ):
            try:
                os.remove(
                    temporary_path
                )
            except OSError:
                pass

    if not isinstance(
        analyzed,
        dict,
    ):
        return result

    metadata = (
        analyzed.get(
            "metadata"
        )
        or {}
    )

    authentication = (
        analyzed.get(
            "authentication"
        )
        or {}
    )

    body = (
        analyzed.get(
            "body"
        )
        or {}
    )

    received_chain = (
        analyzed.get(
            "received_chain"
        )
        or []
    )

    urls = _normalise_urls(
        analyzed.get(
            "urls"
        )
    )

    attachments = (
        _normalise_attachments(
            analyzed.get(
                "attachments"
            )
        )
    )

    header_findings = (
        _normalise_header_findings(
            analyzed.get(
                "header_findings"
            )
        )
    )

    from_value = metadata.get(
        "from"
    )

    reply_to_value = metadata.get(
        "reply_to"
    )

    # ---------------------------------------------------------------
    # Original MailGuard fields
    # ---------------------------------------------------------------

    result["from_display_name"] = (
        _extract_display_name(
            from_value
        )
    )

    result["from_domain"] = (
        _domain_of(
            from_value
        )
    )

    result["reply_to_domain"] = (
        _domain_of(
            reply_to_value
        )
        if reply_to_value
        else result["from_domain"]
    )

    result["received_chain"] = [
        str(item)
        for item in received_chain
        if item
    ]

    result["origin_ip"] = (
        _first_public_ip(
            result["received_chain"]
        )
        or _extract_ip_from_header(
            metadata.get(
                "x_originating_ip"
            )
        )
    )

    result["spf"] = (
        _authentication_result(
            authentication,
            "spf",
        )
    )

    result["dkim"] = (
        _authentication_result(
            authentication,
            "dkim",
        )
    )

    result["dmarc"] = (
        _authentication_result(
            authentication,
            "dmarc",
        )
    )

    result["subject"] = metadata.get(
        "subject"
    )

    result["body_text"] = (
        body.get(
            "text"
        )
        or ""
    )

    # ---------------------------------------------------------------
    # Additional real analyzer data
    # ---------------------------------------------------------------

    result["from"] = from_value

    result["to"] = metadata.get(
        "to"
    )

    result["cc"] = metadata.get(
        "cc"
    )

    result["bcc"] = metadata.get(
        "bcc"
    )

    result["date"] = metadata.get(
        "date"
    )

    result["reply_to"] = reply_to_value

    result["message_id"] = metadata.get(
        "message_id"
    )

    result["return_path"] = metadata.get(
        "return_path"
    )

    result["body_html"] = (
        body.get(
            "html"
        )
        or ""
    )

    result["urls"] = urls

    result["attachments"] = attachments

    result["header_findings"] = (
        header_findings
    )

    result["authentication"] = (
        authentication
    )

    result["metadata"] = metadata

    return result


def _extract_display_name(
    value,
):
    """
    Extract the display-name portion of a From header.
    """

    if not value:
        return None

    text = str(value).strip()

    match = re.match(
        r"^\s*(.*?)\s*<[^<>]+>\s*$",
        text,
    )

    if match:
        name = match.group(1).strip(
            "\"'"
        )

        return name or None

    email_match = _EMAIL_RE.search(
        text
    )

    if email_match:
        before = text[
            : email_match.start()
        ].strip(
            " <>\"'"
        )

        return before or None

    return None


def _extract_ip_from_header(
    value,
):
    """
    Extract an IPv4 address from X-Originating-IP.
    """

    if not value:
        return None

    match = _IP_RE.search(
        str(value)
    )

    return (
        match.group(0)
        if match
        else None
    )
