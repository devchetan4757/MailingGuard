"""
MailGuard analyzer adapter.

This file contains the actual email-analysis implementation integrated from
the backend analyzer project.

Public API:
    parse_email(file_path)

The parser reads an .eml file from a temporary path and returns structured
data that MailGuard's parsing/scoring/API layers can consume.
"""

from __future__ import annotations

import os
import re
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# HEADER HELPERS
# ---------------------------------------------------------------------------

def decode_mime_header(value):
    """Decode an email header into normal readable text."""
    if not value:
        return None

    try:
        return str(make_header(decode_header(value)))
    except (TypeError, ValueError):
        return str(value)


def extract_email_address(value):
    """Extract the email address portion from a header."""
    if not value:
        return None

    match = re.search(
        r"<([^<>@\s]+@[^<>@\s]+)>",
        value,
    )

    if match:
        return match.group(1)

    match = re.search(
        r"\b([^@\s<>]+@[^@\s<>]+)\b",
        value,
    )

    if match:
        return match.group(1)

    return None


# ---------------------------------------------------------------------------
# URL ANALYSIS
# ---------------------------------------------------------------------------

def extract_urls(text):
    """Extract unique HTTP/HTTPS URLs from email content."""
    if not text:
        return []

    matches = re.findall(
        r"https?://[^\s<>'\"()]+",
        text,
    )

    urls = []

    for url in matches:
        url = url.rstrip(
            ".,;:!?)]}"
        )

        try:
            parsed = urlparse(url)

            if (
                parsed.scheme in ("http", "https")
                and parsed.netloc
                and url not in urls
            ):
                urls.append(url)

        except ValueError:
            continue

    return urls


# ---------------------------------------------------------------------------
# ATTACHMENT ANALYSIS
# ---------------------------------------------------------------------------

def analyze_attachment(
    filename,
    content_type,
):
    """Return basic security signals for an attachment."""

    extension = os.path.splitext(
        filename or ""
    )[1].lower()

    suspicious_extensions = {
        ".exe",
        ".dll",
        ".scr",
        ".com",
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
        ".js",
        ".jse",
        ".wsf",
        ".wsh",
        ".msi",
        ".jar",
    }

    if extension in suspicious_extensions:
        return {
            "extension": extension,
            "suspicious": True,
            "reason": "Executable or script file",
        }

    if extension in {
        ".zip",
        ".rar",
        ".7z",
    }:
        return {
            "extension": extension,
            "suspicious": True,
            "reason": "Archive file requires further inspection",
        }

    return {
        "extension": extension,
        "suspicious": False,
        "reason": None,
    }


def extract_attachment_bytes(content, index):
    """
    Re-walk a raw .eml (given as bytes) and return the decoded payload for
    the attachment at `index`, using the exact same walk order/condition
    (`disposition == "attachment" or filename`) as parse_email() uses to
    build the `attachments` list -- so index N here always lines up with
    index N of that list.

    Returns (filename, content_type, payload_bytes) or None if there's no
    attachment at that index.

    Used by the "deep analyze this attachment" button on an already-parsed
    case: the API layer doesn't retain raw attachment bytes in the stored
    case record (only filename/size/etc.), so this re-derives them on
    demand from the raw .eml bytes kept in app.services.store.
    """

    message = BytesParser(
        policy=policy.default
    ).parsebytes(content)

    if not message.is_multipart():
        return None

    position = 0

    for part in message.walk():

        if part.is_multipart():
            continue

        content_type = part.get_content_type()
        disposition = part.get_content_disposition()
        filename = part.get_filename()

        if disposition == "attachment" or filename:

            if position == index:
                payload = part.get_payload(decode=True) or b""
                decoded_filename = decode_mime_header(filename)
                return decoded_filename, content_type, payload

            position += 1

    return None


# ---------------------------------------------------------------------------
# HEADER RELATIONSHIPS
# ---------------------------------------------------------------------------

def analyze_header_relationships(metadata):
    """
    Identify potentially suspicious relationships between email headers.
    """

    findings = []

    from_value = metadata.get("from")
    reply_to = metadata.get("reply_to")
    return_path = metadata.get("return_path")

    if from_value and reply_to:
        from_address = extract_email_address(
            from_value
        )

        reply_to_address = extract_email_address(
            reply_to
        )

        if (
            from_address
            and reply_to_address
            and from_address.lower()
            != reply_to_address.lower()
        ):
            findings.append({
                "type": "reply_to_mismatch",
                "severity": "medium",
                "message": (
                    "Reply-To address differs "
                    "from the From address."
                ),
            })

    if from_value and return_path:
        from_address = extract_email_address(
            from_value
        )

        return_path_address = extract_email_address(
            return_path
        )

        if (
            from_address
            and return_path_address
            and from_address.lower()
            != return_path_address.lower()
        ):
            findings.append({
                "type": "return_path_mismatch",
                "severity": "low",
                "message": (
                    "Return-Path address differs "
                    "from the From address."
                ),
            })

    return findings


# ---------------------------------------------------------------------------
# AUTHENTICATION ANALYSIS
# ---------------------------------------------------------------------------

def extract_authentication_result(
    authentication_results,
    received_spf,
):
    """Extract and normalize the SPF authentication result."""

    if authentication_results:
        match = re.search(
            r"\bspf=(pass|fail|softfail|neutral|none|"
            r"temperror|permerror)\b",
            authentication_results,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).lower()

    if received_spf:
        match = re.match(
            r"\s*(pass|fail|softfail|neutral|none|"
            r"temperror|permerror)\b",
            received_spf,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).lower()

    return "unknown"


def extract_dkim_result(
    authentication_results,
):
    """Extract and normalize the DKIM result."""

    if not authentication_results:
        return "unknown"

    match = re.search(
        r"\bdkim=(pass|fail|neutral|none|"
        r"temperror|permerror)\b",
        authentication_results,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).lower()

    return "unknown"


def extract_dmarc_result(
    authentication_results,
):
    """Extract and normalize the DMARC result."""

    if not authentication_results:
        return "unknown"

    match = re.search(
        r"\bdmarc=(pass|fail|neutral|none|"
        r"temperror|permerror)\b",
        authentication_results,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).lower()

    return "unknown"


def authentication_explanation(
    authentication_type,
    result,
):
    """Return a human-readable authentication explanation."""

    explanations = {
        "spf": {
            "pass": (
                "The sending server was authorized "
                "to send email for this domain."
            ),
            "fail": (
                "The sending server was not authorized "
                "to send email for this domain."
            ),
            "softfail": (
                "The sending server was probably not "
                "authorized to send email for this domain."
            ),
            "neutral": (
                "The domain did not make a clear "
                "SPF authorization statement."
            ),
            "none": (
                "No SPF record was found for this domain."
            ),
            "temperror": (
                "A temporary error occurred while checking SPF."
            ),
            "permerror": (
                "A permanent error occurred while checking SPF."
            ),
            "unknown": (
                "No SPF authentication result was found."
            ),
        },

        "dkim": {
            "pass": (
                "The email's DKIM signature "
                "was successfully verified."
            ),
            "fail": (
                "The email's DKIM signature "
                "could not be verified."
            ),
            "neutral": (
                "The DKIM check did not produce "
                "a definitive result."
            ),
            "none": (
                "No DKIM signature was found."
            ),
            "temperror": (
                "A temporary error occurred while checking DKIM."
            ),
            "permerror": (
                "A permanent error occurred while checking DKIM."
            ),
            "unknown": (
                "No DKIM authentication result was found."
            ),
        },

        "dmarc": {
            "pass": (
                "The email passed DMARC authentication."
            ),
            "fail": (
                "The email failed DMARC authentication."
            ),
            "neutral": (
                "The DMARC check did not produce "
                "a definitive result."
            ),
            "none": (
                "No DMARC authentication result was found."
            ),
            "temperror": (
                "A temporary error occurred while checking DMARC."
            ),
            "permerror": (
                "A permanent error occurred while checking DMARC."
            ),
            "unknown": (
                "No DMARC authentication result was found."
            ),
        },
    }

    return (
        explanations
        .get(authentication_type, {})
        .get(
            result,
            "No explanation is available "
            "for this authentication result.",
        )
    )


# ---------------------------------------------------------------------------
# MAIN ANALYZER
# ---------------------------------------------------------------------------

def parse_email(file_path):
    """
    Parse an .eml file and return its complete structured analysis.

    The original email is only read. This function does not permanently
    store or modify the uploaded email.
    """

    with open(
        file_path,
        "rb",
    ) as email_file:

        message = BytesParser(
            policy=policy.default
        ).parse(email_file)

    metadata = {
        "from": decode_mime_header(
            message.get("From")
        ),
        "to": decode_mime_header(
            message.get("To")
        ),
        "cc": decode_mime_header(
            message.get("Cc")
        ),
        "bcc": decode_mime_header(
            message.get("Bcc")
        ),
        "subject": decode_mime_header(
            message.get("Subject")
        ),
        "date": decode_mime_header(
            message.get("Date")
        ),
        "reply_to": decode_mime_header(
            message.get("Reply-To")
        ),
        "message_id": decode_mime_header(
            message.get("Message-ID")
        ),
        "return_path": decode_mime_header(
            message.get("Return-Path")
        ),
        "authentication_results": decode_mime_header(
            message.get("Authentication-Results")
        ),
        "received_spf": decode_mime_header(
            message.get("Received-SPF")
        ),
        "dkim_signature": decode_mime_header(
            message.get("DKIM-Signature")
        ),
        "x_mailer": decode_mime_header(
            message.get("X-Mailer")
        ),
        "x_originating_ip": decode_mime_header(
            message.get("X-Originating-IP")
        ),
    }

    received_chain = [
        decode_mime_header(value)
        for value in message.get_all(
            "Received",
            [],
        )
    ]

    authentication_results = (
        metadata.get(
            "authentication_results"
        )
    )

    received_spf = metadata.get(
        "received_spf"
    )

    spf_result = extract_authentication_result(
        authentication_results,
        received_spf,
    )

    dkim_result = extract_dkim_result(
        authentication_results
    )

    dmarc_result = extract_dmarc_result(
        authentication_results
    )

    authentication = {
        "spf": {
            "result": spf_result,
            "explanation": authentication_explanation(
                "spf",
                spf_result,
            ),
        },

        "dkim": {
            "result": dkim_result,
            "explanation": authentication_explanation(
                "dkim",
                dkim_result,
            ),
        },

        "dmarc": {
            "result": dmarc_result,
            "explanation": authentication_explanation(
                "dmarc",
                dmarc_result,
            ),
        },
    }

    text_body = None
    html_body = None
    attachments = []

    if message.is_multipart():

        for part in message.walk():

            if part.is_multipart():
                continue

            content_type = (
                part.get_content_type()
            )

            disposition = (
                part.get_content_disposition()
            )

            filename = part.get_filename()

            if (
                disposition == "attachment"
                or filename
            ):

                payload = (
                    part.get_payload(
                        decode=True
                    )
                    or b""
                )

                decoded_filename = (
                    decode_mime_header(
                        filename
                    )
                )

                attachment_analysis = (
                    analyze_attachment(
                        decoded_filename,
                        content_type,
                    )
                )

                attachments.append({
                    "filename": decoded_filename,
                    "content_type": content_type,
                    "size": len(payload),
                    **attachment_analysis,
                })

                continue

            if (
                content_type == "text/plain"
                and text_body is None
            ):
                text_body = part.get_content()

            elif (
                content_type == "text/html"
                and html_body is None
            ):
                html_body = part.get_content()

    else:

        content_type = (
            message.get_content_type()
        )

        if content_type == "text/plain":
            text_body = message.get_content()

        elif content_type == "text/html":
            html_body = message.get_content()

    combined_body = "\n".join(
        body
        for body in (
            text_body,
            html_body,
        )
        if body
    )

    urls = extract_urls(
        combined_body
    )

    header_findings = (
        analyze_header_relationships(
            metadata
        )
    )

    return {
        "metadata": metadata,

        "body": {
            "text": text_body,
            "html": html_body,
        },

        "attachments": attachments,

        "urls": urls,

        "header_findings": header_findings,

        "received_chain": received_chain,

        "authentication": authentication,
    }
