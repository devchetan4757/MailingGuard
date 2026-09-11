# metadata_forensics.py
#
# Document Information dictionary ("/Info") forensics.
#
# Two independent signals live here:
#
#   1. Producer/Creator fingerprinting -- phishing kits overwhelmingly
#      churn out their payload PDFs through a small set of scriptable,
#      headless generation libraries (wkhtmltopdf, ReportLab, TCPDF,
#      FPDF, jsPDF, mPDF, Skia in "print to PDF" mode, ...) rather than
#      a document actually being authored in Word/Acrobat/Pages and
#      exported. None of these libraries are malicious by themselves
#      -- plenty of legitimate systems (invoicing SaaS, ticket
#      systems) use them too -- but seeing one behind a "secure
#      document" / "invoice" / "voicemail" credential-phishing pretext
#      is a meaningfully different prior than seeing "Microsoft Word"
#      or "Acrobat Distiller" there. Treated as a soft signal, folded
#      into the score, never a standalone verdict.
#
#   2. CreationDate / ModDate anomalies -- the PDF spec has no
#      mechanism that enforces ModDate >= CreationDate, and mainstream
#      authoring tools never produce the reverse. A ModDate that
#      predates the CreationDate, or a CreationDate sitting in the
#      future relative to "now", means the /Info dictionary was
#      hand-set (directly, or by a generation library that copies a
#      stale/fixed timestamp from a template) rather than produced
#      naturally by a save/export pipeline.
#
# Both checks operate purely on the /Info dictionary already read by
# analyzer.py (doc.metadata) -- no additional parsing pass needed.

import re
from datetime import datetime, timezone

# ============================================================
# KNOWN GENERATOR SIGNATURES
# ============================================================
# Substring match (case-insensitive) against the Producer and/or
# Creator fields. Descriptions explain *why* the tool shows up in
# phishing-kit output specifically, not just "this tool exists".

KNOWN_PHISHING_KIT_GENERATORS = {
    "wkhtmltopdf": (
        "Headless HTML-to-PDF renderer commonly used by phishing kits "
        "to turn a cloned login-page template into a PDF 'secure "
        "document' or 'invoice' lure"
    ),
    "reportlab": (
        "Python PDF-generation library frequently used to mass-produce "
        "templated fake-invoice/fake-voicemail phishing PDFs at scale"
    ),
    "tcpdf": (
        "PHP PDF library commonly bundled into off-the-shelf phishing "
        "kits for on-the-fly PDF lure generation"
    ),
    "fpdf": (
        "Lightweight PDF library often seen in automated/scripted "
        "phishing PDF generation rather than human document authoring"
    ),
    "mpdf": (
        "PHP HTML-to-PDF library with the same phishing-kit usage "
        "pattern as wkhtmltopdf/TCPDF"
    ),
    "jspdf": (
        "Client-side JavaScript PDF library; its appearance in an "
        "emailed document is unusual outside of automated/kit-driven "
        "generation"
    ),
    "dompdf": (
        "PHP HTML-to-PDF library commonly used by phishing kits to "
        "render a cloned page as a PDF attachment"
    ),
    "html2pdf": (
        "Generic HTML-to-PDF conversion tool; consistent with a cloned "
        "phishing page rendered straight to PDF rather than authored"
    ),
    "pdfkit": (
        "Node.js PDF-generation library associated with the same "
        "scripted-lure pattern as wkhtmltopdf/jsPDF"
    ),
}

# PDF "D:" date format, e.g. D:20230114153045+00'00' or D:20230114153045Z
PDF_DATE_PATTERN = re.compile(
    r"^D:(\d{4})(\d{2})(\d{2})"
    r"(\d{2})?(\d{2})?(\d{2})?"
    r"([+\-Zz])?"
    r"(\d{2})?'?(\d{2})?'?"
)


def parse_pdf_date(value):
    """
    Parse a PDF /Info date string ("D:YYYYMMDDHHmmSS+HH'mm'") into a
    timezone-aware datetime. Returns None for anything missing,
    malformed, or not actually a PDF date string -- callers treat
    "couldn't parse" as "can't check", not as an anomaly on its own,
    since plenty of legitimate PDFs carry incomplete or nonstandard
    date strings.
    """

    if not value:
        return None

    value = str(value).strip()

    match = PDF_DATE_PATTERN.match(value)

    if not match:
        return None

    year, month, day, hour, minute, second, tz_sign, tz_hour, tz_min = (
        match.groups()
    )

    try:

        naive = datetime(
            int(year),
            int(month or 1),
            int(day or 1),
            int(hour or 0),
            int(minute or 0),
            int(second or 0)
        )

    except ValueError:
        # Out-of-range component (month 13, day 32, ...) -- malformed
        # rather than a real timestamp we can compare.
        return None

    if tz_sign in ("+", "-") and tz_hour:

        offset_minutes = int(tz_hour) * 60 + int(tz_min or 0)

        if tz_sign == "-":
            offset_minutes = -offset_minutes

        tz = timezone(
            timedelta_minutes(offset_minutes)
        )

        return naive.replace(tzinfo=tz)

    # "Z"/"z" or no offset at all -- treat as UTC.
    return naive.replace(tzinfo=timezone.utc)


def timedelta_minutes(minutes):
    from datetime import timedelta
    return timedelta(minutes=minutes)


def check_generator_signatures(metadata):
    """
    Check Producer and Creator fields against known scripted/phishing-
    kit generation libraries. Returns a list of anomaly dicts.
    """

    findings = []
    already_flagged = set()

    for field_name in ("producer", "creator"):

        field_value = metadata.get(field_name)

        if not field_value:
            continue

        field_lower = str(field_value).lower()

        for signature, reason in KNOWN_PHISHING_KIT_GENERATORS.items():

            if signature not in field_lower:
                continue

            # Same underlying tool often shows up in both Producer and
            # Creator (some libraries set both) -- report it once.
            if signature in already_flagged:
                continue

            already_flagged.add(signature)

            findings.append({
                "type": "known_generator_signature",
                "severity": "low",
                "field": field_name,
                "value": str(field_value),
                "signature": signature,
                "description": (
                    f"{field_name.capitalize()} field contains "
                    f"'{signature}' -- {reason}."
                )
            })

    return findings


def check_date_anomalies(metadata):
    """
    Compare CreationDate and ModDate (and both against "now"). Returns
    a list of anomaly dicts. Each check independently no-ops if the
    relevant date string is missing or unparseable.
    """

    findings = []

    creation_raw = metadata.get("creationDate")
    mod_raw = metadata.get("modDate")

    creation_dt = parse_pdf_date(creation_raw)
    mod_dt = parse_pdf_date(mod_raw)

    now = datetime.now(timezone.utc)

    # ---- ModDate before CreationDate ----
    #
    # No legitimate save/export pipeline produces a "last modified"
    # timestamp earlier than the document's own creation timestamp --
    # this only happens when the /Info dictionary was set by hand or
    # copied wholesale from a stale template.

    if creation_dt is not None and mod_dt is not None:

        if mod_dt < creation_dt:

            findings.append({
                "type": "moddate_before_creationdate",
                "severity": "high",
                "creation_date": creation_raw,
                "mod_date": mod_raw,
                "description": (
                    f"ModDate ({mod_raw}) predates CreationDate "
                    f"({creation_raw}) -- the /Info dictionary was "
                    f"hand-set or copied from a template rather than "
                    f"produced naturally by a save/export pipeline."
                )
            })

    # ---- CreationDate in the future ----
    #
    # A small amount of clock skew is normal; this only fires on a
    # clearly future date (>1 day ahead) to avoid flagging ordinary
    # timezone-handling noise.

    if creation_dt is not None and (creation_dt - now).days >= 1:

        findings.append({
            "type": "creationdate_in_future",
            "severity": "medium",
            "creation_date": creation_raw,
            "description": (
                f"CreationDate ({creation_raw}) is in the future "
                f"relative to the current time -- consistent with a "
                f"fixed/incorrect timestamp baked into a phishing-kit "
                f"template rather than a real authoring date."
            )
        })

    # ---- ModDate in the future ----

    if mod_dt is not None and (mod_dt - now).days >= 1:

        findings.append({
            "type": "moddate_in_future",
            "severity": "medium",
            "mod_date": mod_raw,
            "description": (
                f"ModDate ({mod_raw}) is in the future relative to "
                f"the current time -- consistent with a fixed/"
                f"incorrect timestamp baked into a phishing-kit "
                f"template rather than a real save time."
            )
        })

    return findings


def analyze_metadata(metadata):
    """
    Run every metadata-forensics check against the already-extracted
    /Info dictionary (analyzer.py's result["metadata"], i.e.
    doc.metadata with empty values dropped -- keys are pymupdf's
    lowerCamelCase: producer, creator, creationDate, modDate, ...).

    Returns a result dict with a flat "anomalies" list, matching the
    shape structure_checks.analyze_structure() already returns, so the
    caller can fold it into the overall indicator score and, for
    high-severity findings, into a forced verdict override the same
    way a confirmed VirusTotal hit or CVE-trigger JS call is.
    """

    metadata = metadata or {}

    anomalies = []

    anomalies.extend(check_generator_signatures(metadata))
    anomalies.extend(check_date_anomalies(metadata))

    high_severity_detected = any(
        anomaly.get("severity") == "high"
        for anomaly in anomalies
    )

    return {
        "producer": metadata.get("producer", ""),
        "creator": metadata.get("creator", ""),
        "creation_date": metadata.get("creationDate", ""),
        "mod_date": metadata.get("modDate", ""),

        "anomaly_count": len(anomalies),
        "high_severity_detected": high_severity_detected,

        "anomalies": anomalies
    }
