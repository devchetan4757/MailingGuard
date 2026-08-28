"""
MailGuard dashboard aggregation service.

Converts the normalized analyzer + scoring output into dashboard-ready
datasets.

The frontend should consume these values instead of calculating security
metrics itself.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _severity_bucket(
    score: int,
) -> str:
    if score >= 70:
        return "high"

    if score >= 35:
        return "medium"

    return "low"


# ---------------------------------------------------------------------------
# RISK DISTRIBUTION
# ---------------------------------------------------------------------------

def build_risk_distribution(
    risk_score: int,
) -> list[dict[str, Any]]:
    """
    Build the values used by the dashboard risk chart.
    """

    score = max(
        0,
        min(
            100,
            _safe_int(risk_score),
        ),
    )

    return [
        {
            "name": "Safe",
            "value": max(
                0,
                100 - score,
            ),
        },
        {
            "name": "Risk",
            "value": score,
        },
    ]


# ---------------------------------------------------------------------------
# AUTHENTICATION CHART
# ---------------------------------------------------------------------------

def build_authentication_chart(
    analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build SPF/DKIM/DMARC chart data.
    """

    data = []

    for name in (
        "spf",
        "dkim",
        "dmarc",
    ):

        result = str(
            analysis.get(
                name,
                "unknown",
            )
            or "unknown"
        ).lower()

        if result in {
            "pass",
            "passed",
        }:
            status = "pass"

        elif result in {
            "fail",
            "failed",
            "softfail",
            "permerror",
        }:
            status = "fail"

        else:
            status = "unknown"

        data.append(
            {
                "name": name.upper(),
                "result": result,
                "status": status,
                "value": (
                    1
                    if status == "pass"
                    else 0
                ),
            }
        )

    return data


# ---------------------------------------------------------------------------
# THREAT CATEGORY CHART
# ---------------------------------------------------------------------------

def build_threat_categories(
    scoring: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Group findings by security category.
    """

    findings = (
        scoring.get(
            "findings"
        )
        or []
    )

    counter = Counter()

    for finding in findings:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        category = str(
            finding.get(
                "category",
                "other",
            )
        ).lower()

        counter[category] += 1

    return [
        {
            "name": category.replace(
                "_",
                " ",
            ).title(),

            "value": count,
        }
        for category, count
        in counter.items()
    ]


# ---------------------------------------------------------------------------
# FINDING SEVERITY CHART
# ---------------------------------------------------------------------------

def build_finding_severity(
    scoring: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Count low/medium/high findings.
    """

    counter = Counter(
        {
            "low": 0,
            "medium": 0,
            "high": 0,
        }
    )

    findings = (
        scoring.get(
            "findings"
        )
        or []
    )

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

        if severity not in counter:
            severity = "low"

        counter[severity] += 1

    return [
        {
            "name": "Low",
            "value": counter["low"],
        },
        {
            "name": "Medium",
            "value": counter["medium"],
        },
        {
            "name": "High",
            "value": counter["high"],
        },
    ]


# ---------------------------------------------------------------------------
# URL / ATTACHMENT SUMMARY
# ---------------------------------------------------------------------------

def build_content_risk(
    analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build URL and attachment risk data.
    """

    metrics = (
        analysis.get(
            "metrics"
        )
        or {}
    )

    return [
        {
            "name": "URLs",
            "total": _safe_int(
                metrics.get(
                    "urlCount"
                )
            ),
            "suspicious": _safe_int(
                metrics.get(
                    "suspiciousUrlCount"
                )
            ),
        },
        {
            "name": "Attachments",
            "total": _safe_int(
                metrics.get(
                    "attachmentCount"
                )
            ),
            "suspicious": _safe_int(
                metrics.get(
                    "suspiciousAttachmentCount"
                )
            ),
        },
        {
            "name": "Headers",
            "total": _safe_int(
                metrics.get(
                    "headerFindingCount"
                )
            ),
            "suspicious": _safe_int(
                metrics.get(
                    "headerFindingCount"
                )
            ),
        },
    ]


# ---------------------------------------------------------------------------
# DASHBOARD SUMMARY
# ---------------------------------------------------------------------------

def build_dashboard_data(
    analysis: dict[str, Any],
    scoring: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the complete dashboard dataset for one analyzed email.
    """

    risk_score = _safe_int(
        scoring.get(
            "riskScore"
        )
    )

    metrics = (
        scoring.get(
            "metrics"
        )
        or analysis.get(
            "metrics"
        )
        or {}
    )

    findings = (
        scoring.get(
            "findings"
        )
        or []
    )

    high_findings = [
        finding
        for finding in findings
        if isinstance(
            finding,
            dict,
        )
        and str(
            finding.get(
                "severity",
                "",
            )
        ).lower()
        == "high"
    ]

    return {
        "risk": {
            "score": risk_score,

            "level": _severity_bucket(
                risk_score
            ),

            "distribution": (
                build_risk_distribution(
                    risk_score
                )
            ),
        },

        "authentication": (
            build_authentication_chart(
                analysis
            )
        ),

        "threatCategories": (
            build_threat_categories(
                scoring
            )
        ),

        "findingSeverity": (
            build_finding_severity(
                scoring
            )
        ),

        "contentRisk": (
            build_content_risk(
                analysis
            )
        ),

        "metrics": {
            "urls": _safe_int(
                metrics.get(
                    "urlCount"
                )
            ),

            "suspiciousUrls": _safe_int(
                metrics.get(
                    "suspiciousUrlCount"
                )
            ),

            "attachments": _safe_int(
                metrics.get(
                    "attachmentCount"
                )
            ),

            "suspiciousAttachments": _safe_int(
                metrics.get(
                    "suspiciousAttachmentCount"
                )
            ),

            "headerFindings": _safe_int(
                metrics.get(
                    "headerFindingCount"
                )
            ),

            "authenticationFailures": _safe_int(
                metrics.get(
                    "authenticationFailureCount"
                )
            ),

            "totalFindings": _safe_int(
                metrics.get(
                    "totalFindingCount"
                )
            ),

            "highRiskFindings": len(
                high_findings
            ),
        },

        "findings": findings,
    }
