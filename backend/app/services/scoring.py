"""
MailGuard risk scoring engine.

Consumes the normalized result from parsing.py.

The original MailGuard scoring contract is preserved:

    score_email(parsed) -> {
        riskScore,
        severity,
        urgencyLanguage,
        impersonationScore,
        summary
    }

Additional analyzer findings contribute to the rule-based score.
"""

from __future__ import annotations

import re


SCORE_SHAPE = {
    "riskScore": 0,
    "severity": "green",
    "urgencyLanguage": "low",
    "impersonationScore": 0.0,
    "summary": "",
}


def _contains_any(
    text: str,
    phrases: tuple[str, ...],
) -> bool:
    text = (
        text or ""
    ).lower()

    return any(
        phrase in text
        for phrase in phrases
    )


def _count_urgency_terms(
    text: str,
) -> int:
    terms = (
        "urgent",
        "immediately",
        "action required",
        "verify your account",
        "account suspended",
        "account locked",
        "payment required",
        "click now",
        "confirm now",
        "respond immediately",
        "final notice",
        "security alert",
    )

    text = (
        text or ""
    ).lower()

    return sum(
        1
        for term in terms
        if term in text
    )


def _suspicious_url_count(
    parsed: dict,
) -> int:
    """
    The imported analyzer extracts URLs but deliberately does not perform
    external URL reputation checks.

    Here we identify obvious URL-level warning signals locally without
    making network requests.
    """

    urls = parsed.get(
        "urls"
    ) or []

    suspicious = 0

    for url in urls:

        value = str(
            url
        ).lower()

        if (
            "@" in value.split(
                "://",
                1,
            )[-1].split(
                "/",
                1,
            )[0]
        ):
            suspicious += 1
            continue

        suspicious_terms = (
            "login",
            "verify",
            "signin",
            "secure",
            "account",
            "password",
            "confirm",
            "wallet",
            "payment",
        )

        if any(
            term in value
            for term in suspicious_terms
        ):
            suspicious += 1

    return suspicious


def _attachment_risk_points(
    parsed: dict,
) -> tuple[int, int]:
    attachments = (
        parsed.get(
            "attachments"
        )
        or []
    )

    suspicious = sum(
        1
        for attachment in attachments
        if isinstance(
            attachment,
            dict,
        )
        and attachment.get(
            "suspicious",
            False,
        )
    )

    if suspicious == 0:
        return 0, 0

    return (
        min(
            suspicious * 20,
            40,
        ),
        suspicious,
    )


def _header_finding_points(
    parsed: dict,
) -> tuple[int, int]:
    findings = (
        parsed.get(
            "header_findings"
        )
        or []
    )

    points = 0

    for finding in findings:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        severity = str(
            finding.get(
                "severity",
                "low",
            )
        ).lower()

        if severity == "high":
            points += 20

        elif severity == "medium":
            points += 15

        else:
            points += 8

    return (
        min(points, 35),
        len(findings),
    )


def rule_based_score(
    parsed: dict,
) -> int:
    """
    Calculate the deterministic security floor.

    This score can never be reduced by the AI/content layer.
    """

    score = 0

    # ---------------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------------

    if parsed.get("spf") == "fail":
        score += 25

    if parsed.get("dkim") == "fail":
        score += 25

    if parsed.get("dmarc") == "fail":
        score += 25

    # ---------------------------------------------------------------
    # Sender / Reply-To mismatch
    # ---------------------------------------------------------------

    from_domain = (
        parsed.get(
            "from_domain"
        )
        or ""
    ).lower()

    reply_domain = (
        parsed.get(
            "reply_to_domain"
        )
        or ""
    ).lower()

    if (
        from_domain
        and reply_domain
        and from_domain != reply_domain
    ):
        score += 20

    # ---------------------------------------------------------------
    # Header findings from the real analyzer
    # ---------------------------------------------------------------

    header_points, _ = (
        _header_finding_points(
            parsed
        )
    )

    score += header_points

    # ---------------------------------------------------------------
    # Suspicious attachments
    # ---------------------------------------------------------------

    attachment_points, _ = (
        _attachment_risk_points(
            parsed
        )
    )

    score += attachment_points

    # ---------------------------------------------------------------
    # Suspicious-looking URLs
    # ---------------------------------------------------------------

    suspicious_urls = (
        _suspicious_url_count(
            parsed
        )
    )

    score += min(
        suspicious_urls * 8,
        25,
    )

    return min(
        score,
        100,
    )


def ai_score(
    parsed: dict,
) -> dict:
    """
    Local content-signal layer.

    This intentionally does not call an external AI service yet. It extracts
    deterministic content indicators from the analyzed message so the
    dashboard has meaningful results immediately.

    The AI interface remains isolated here, making a future LLM provider
    replaceable without changing the rest of MailGuard.
    """

    subject = str(
        parsed.get(
            "subject"
        )
        or ""
    )

    body = str(
        parsed.get(
            "body_text"
        )
        or ""
    )

    combined_text = (
        f"{subject}\n{body}"
    )

    urgency_hits = (
        _count_urgency_terms(
            combined_text
        )
    )

    if urgency_hits >= 3:
        urgency = "high"

    elif urgency_hits >= 1:
        urgency = "medium"

    else:
        urgency = "low"

    impersonation_score = 0.0

    signals = []

    from_domain = (
        parsed.get(
            "from_domain"
        )
        or ""
    ).lower()

    reply_domain = (
        parsed.get(
            "reply_to_domain"
        )
        or ""
    ).lower()

    if (
        from_domain
        and reply_domain
        and from_domain != reply_domain
    ):
        impersonation_score += 0.45
        signals.append(
            "sender/reply-to mismatch"
        )

    header_findings = (
        parsed.get(
            "header_findings"
        )
        or []
    )

    if header_findings:
        impersonation_score += 0.15

        signals.append(
            "header relationship anomaly"
        )

    suspicious_urls = (
        _suspicious_url_count(
            parsed
        )
    )

    if suspicious_urls:
        impersonation_score += 0.20

        signals.append(
            "suspicious-looking URL"
        )

    impersonation_score = min(
        impersonation_score,
        1.0,
    )

    # Content points remain deliberately modest because deterministic
    # authentication/security rules must remain the score floor.
    content_points = min(
        urgency_hits * 5,
        20,
    )

    if impersonation_score >= 0.6:
        content_points += 10

    content_points = min(
        content_points,
        30,
    )

    if signals:
        summary = (
            "Potentially risky indicators: "
            + ", ".join(signals)
            + "."
        )

    elif urgency_hits:
        summary = (
            "The message contains language "
            "associated with urgency or pressure."
        )

    else:
        summary = (
            "No strong content-level warning "
            "signals were detected."
        )

    return {
        "points": content_points,
        "urgencyLanguage": urgency,
        "impersonationScore": (
            round(
                impersonation_score,
                2,
            )
        ),
        "summary": summary,
    }


def combine_scores(
    rule_points: int,
    ai_result: dict,
) -> dict:
    """
    Combine deterministic and content scores.

    IMPORTANT:
    AI/content scoring can never lower the deterministic rule-based floor.
    """

    ai_points = int(
        ai_result.get(
            "points",
            0,
        )
        or 0
    )

    combined = max(
        rule_points,
        min(
            rule_points + ai_points,
            100,
        ),
    )

    if combined >= 70:
        severity = "red"

    elif combined >= 40:
        severity = "yellow"

    else:
        severity = "green"

    return {
        "riskScore": combined,

        "severity": severity,

        "urgencyLanguage": (
            ai_result.get(
                "urgencyLanguage",
                "low",
            )
        ),

        "impersonationScore": float(
            ai_result.get(
                "impersonationScore",
                0.0,
            )
            or 0.0
        ),

        "summary": ai_result.get(
            "summary",
            "",
        ),
    }


def _collect_findings(
    parsed: dict,
) -> list[dict]:
    """
    Normalize every rule-based signal into a flat findings list so the
    dashboard's threat-category and severity charts have something to
    group. Without this, `score_email()` never populated "findings" and
    those charts stayed empty no matter what the analyzer detected.
    """

    findings = []

    for finding in parsed.get("header_findings") or []:
        if not isinstance(finding, dict):
            continue

        findings.append(
            {
                "category": finding.get(
                    "type", "header_anomaly"
                ),
                "severity": finding.get(
                    "severity", "low"
                ),
                "message": finding.get(
                    "message",
                    "Header anomaly detected.",
                ),
            }
        )

    for key in ("spf", "dkim", "dmarc"):
        if parsed.get(key) == "fail":
            findings.append(
                {
                    "category": "authentication_failure",
                    "severity": "high",
                    "message": f"{key.upper()} authentication failed.",
                }
            )

    from_domain = (
        parsed.get("from_domain") or ""
    ).lower()

    reply_domain = (
        parsed.get("reply_to_domain") or ""
    ).lower()

    if (
        from_domain
        and reply_domain
        and from_domain != reply_domain
    ):
        findings.append(
            {
                "category": "sender_mismatch",
                "severity": "medium",
                "message": "Reply-To domain differs from the From domain.",
            }
        )

    for attachment in parsed.get("attachments") or []:
        if isinstance(attachment, dict) and attachment.get("suspicious"):
            findings.append(
                {
                    "category": "suspicious_attachment",
                    "severity": "high",
                    "message": attachment.get("reason")
                    or "Suspicious attachment type.",
                }
            )

    suspicious_urls = _suspicious_url_count(parsed)

    if suspicious_urls:
        findings.append(
            {
                "category": "suspicious_url",
                "severity": "medium",
                "message": f"{suspicious_urls} suspicious-looking URL(s) detected.",
            }
        )

    return findings


def score_email(
    parsed: dict,
) -> dict:
    """
    Public scoring entry point.
    """

    rule_points = rule_based_score(
        parsed
    )

    ai_result = ai_score(
        parsed
    )

    result = combine_scores(
        rule_points,
        ai_result,
    )

    result["findings"] = _collect_findings(
        parsed
    )

    return result
