"""
POST /api/analyze

MailGuard analysis orchestration.

Flow:

    uploaded .eml
          ↓
    integrated email analyzer
          ↓
    MailGuard scoring
          ↓
    origin / similarity / hash chain
          ↓
    dashboard aggregation
          ↓
    API response
"""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.security import validate_upload
from app.services.parsing import parse_eml
from app.services.scoring import score_email
from app.services.origin.config import load_config
from app.services.origin.service import OriginAnalysisService
from app.services.similarity import find_related_cases
from app.services.hashchain import compute_case_hash
from app.services import store
from app.models.schemas import AnalyzeResponse


router = APIRouter()

origin_service = OriginAnalysisService(
    load_config()
)


def _build_dashboard(
    parsed: dict,
    score: dict,
    detailed: dict,
) -> dict:
    """
    Convert real analyzer/scoring output into dashboard-ready data.
    """

    findings = (
        score.get("findings")
        or []
    )

    metrics = (
        score.get("metrics")
        or {}
    )

    # ---------------------------------------------------------------
    # Risk distribution
    # ---------------------------------------------------------------

    risk_score = int(
        score.get(
            "riskScore",
            0,
        )
        or 0
    )

    risk_score = max(
        0,
        min(
            100,
            risk_score,
        ),
    )

    # ---------------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------------

    authentication = []

    for name in (
        "spf",
        "dkim",
        "dmarc",
    ):
        result = parsed.get(
            name,
            "none",
        )

        authentication.append(
            {
                "name": name.upper(),
                "result": result,
                "status": (
                    "pass"
                    if result == "pass"
                    else "fail"
                    if result == "fail"
                    else "unknown"
                ),
                "value": (
                    1
                    if result == "pass"
                    else 0
                ),
            }
        )

    # ---------------------------------------------------------------
    # Threat categories
    # ---------------------------------------------------------------

    category_counts = {}

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
        )

        category_counts[category] = (
            category_counts.get(
                category,
                0,
            )
            + 1
        )

    threat_categories = [
        {
            "name": category.replace(
                "_",
                " ",
            ).title(),

            "value": count,
        }
        for category, count
        in category_counts.items()
    ]

    # ---------------------------------------------------------------
    # Finding severity
    # ---------------------------------------------------------------

    severity_counts = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
    }

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
            severity_counts["High"] += 1

        elif severity == "medium":
            severity_counts["Medium"] += 1

        else:
            severity_counts["Low"] += 1

    finding_severity = [
        {
            "name": name,
            "value": value,
        }
        for name, value
        in severity_counts.items()
    ]

    # ---------------------------------------------------------------
    # Content risk
    # ---------------------------------------------------------------

    attachments = (
        detailed.get(
            "attachments"
        )
        or []
    )

    urls = (
        detailed.get(
            "urls"
        )
        or []
    )

    suspicious_attachments = sum(
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

    suspicious_urls = sum(
        1
        for url in urls
        if isinstance(
            url,
            dict,
        )
        and url.get(
            "suspicious",
            False,
        )
    )

    # The standalone analyzer currently returns URLs as strings.
    # Keep the metric at zero when no explicit URL reputation signal
    # exists rather than pretending every URL is malicious.
    if suspicious_urls == 0:
        suspicious_urls = int(
            metrics.get(
                "suspiciousUrlCount",
                0,
            )
            or 0
        )

    content_risk = [
        {
            "name": "URLs",
            "total": len(urls),
            "suspicious": suspicious_urls,
        },
        {
            "name": "Attachments",
            "total": len(attachments),
            "suspicious": suspicious_attachments,
        },
        {
            "name": "Header Findings",
            "total": len(
                detailed.get(
                    "header_findings"
                )
                or []
            ),
            "suspicious": len(
                detailed.get(
                    "header_findings"
                )
                or []
            ),
        },
    ]

    # ---------------------------------------------------------------
    # Dashboard metrics
    # ---------------------------------------------------------------

    dashboard_metrics = {
        "urlCount": int(
            metrics.get(
                "urlCount",
                len(urls),
            )
            or 0
        ),

        "suspiciousUrlCount": suspicious_urls,

        "attachmentCount": int(
            metrics.get(
                "attachmentCount",
                len(attachments),
            )
            or 0
        ),

        "suspiciousAttachmentCount": (
            suspicious_attachments
        ),

        "headerFindingCount": int(
            metrics.get(
                "headerFindingCount",
                len(
                    detailed.get(
                        "header_findings"
                    )
                    or []
                ),
            )
            or 0
        ),

        "receivedHopCount": len(
            detailed.get(
                "received_chain"
            )
            or []
        ),

        "authenticationFailureCount": sum(
            1
            for name in (
                "spf",
                "dkim",
                "dmarc",
            )
            if parsed.get(name) == "fail"
        ),

        "totalFindingCount": len(
            findings
        ),
    }

    return {
        "risk": {
            "score": risk_score,

            "severity": score.get(
                "severity",
                "green",
            ),

            "distribution": [
                {
                    "name": "Safe",
                    "value": 100 - risk_score,
                },
                {
                    "name": "Risk",
                    "value": risk_score,
                },
            ],
        },

        "authentication": authentication,

        "threatCategories": threat_categories,

        "findingSeverity": finding_severity,

        "contentRisk": content_risk,

        "metrics": dashboard_metrics,

        "findings": findings,
    }


async def run_analysis(
    content: bytes,
    filename: str,
) -> dict:
    """
    Shared analysis pipeline.

    Runs the full parse -> score -> origin -> similarity -> case/hash
    chain -> dashboard pipeline for raw .eml bytes, regardless of
    whether they came from a direct file upload (POST /analyze) or
    from a Gmail message handed over for analysis
    (POST /integrations/gmail/messages/{id}/analyze).

    Raises ValueError (bad upload, e.g. too large) — callers are
    expected to translate that into the appropriate HTTP error for
    their own endpoint.
    """

    validate_upload(
        filename,
        content,
    )

    # ---------------------------------------------------------------
    # Parse with the integrated real analyzer
    # ---------------------------------------------------------------

    parsed = parse_eml(
        content
    )

    # ---------------------------------------------------------------
    # Existing MailGuard scoring
    # ---------------------------------------------------------------

    score = score_email(
        parsed
    )

    # ---------------------------------------------------------------
    # Origin Analysis
    # ---------------------------------------------------------------

    case_id = (
        f"case-{len(store.all_cases()) + 1}"
    )

    origin_analysis = await origin_service.analyze(
        parsed.get(
            "received_chain",
            [],
        ),
        case_id=case_id,
        from_domain=parsed.get(
            "from_domain"
        ),
        base_risk=int(
            score.get(
                "riskScore",
                0,
            )
            or 0
        ),
    )

    raw_origin = origin_analysis.get("origin") or {}

    # Preserve the existing MailingGuard Origin contract.
    origin = {
        "ip": raw_origin.get("ip")
        or parsed.get("origin_ip")
        or "",
        "country": raw_origin.get("country"),
        "city": raw_origin.get("city"),
        "lat": raw_origin.get("lat"),
        "lng": raw_origin.get("lng", raw_origin.get("lon")),
        "isVpnOrHosting": bool(
            raw_origin.get("isVpnOrHosting")
            or raw_origin.get("hosting")
            or raw_origin.get("proxy")
        ),
    }

    # ---------------------------------------------------------------
    # Existing similarity analysis
    # ---------------------------------------------------------------

    related = find_related_cases(
        parsed,
        origin,
        store.all_cases(),
    )

    # ---------------------------------------------------------------
    # Existing case/hash chain
    # ---------------------------------------------------------------

    previous_hash = (
        store.last_case_hash()
    )

    case_hash = compute_case_hash(
        parsed,
        previous_hash,
    )

    analyzed_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    # ---------------------------------------------------------------
    # Detailed analyzer data
    #
    # parsing.py retains the imported analyzer's richer information.
    # ---------------------------------------------------------------

    detailed = {
        "metadata": parsed.get(
            "metadata",
            {},
        ),

        "authentication": parsed.get(
            "authentication",
            {},
        ),

        "body": {
            "text": parsed.get(
                "body_text",
                "",
            ),

            "html": parsed.get(
                "body_html",
            ),
        },

        "received_chain": parsed.get(
            "received_chain",
            [],
        ),

        "urls": parsed.get(
            "urls",
            [],
        ),

        "attachments": parsed.get(
            "attachments",
            [],
        ),

        "header_findings": parsed.get(
            "header_findings",
            [],
        ),
    }

    # ---------------------------------------------------------------
    # Dashboard payload
    # ---------------------------------------------------------------

    dashboard = _build_dashboard(
        parsed,
        score,
        detailed,
    )

    # ---------------------------------------------------------------
    # API response
    # ---------------------------------------------------------------

    response = {
        "caseId": case_id,

        "riskScore": score[
            "riskScore"
        ],

        "severity": score[
            "severity"
        ],

        "headerChecks": {
            "spf": parsed[
                "spf"
            ],

            "dkim": parsed[
                "dkim"
            ],

            "dmarc": parsed[
                "dmarc"
            ],

            "senderDomainMismatch": (
                parsed.get(
                    "from_domain"
                )
                != parsed.get(
                    "reply_to_domain"
                )
            ),
        },

        "aiSignals": {
            "urgencyLanguage": score[
                "urgencyLanguage"
            ],

            "impersonationScore": score[
                "impersonationScore"
            ],

            "summary": score[
                "summary"
            ],
        },

        "origin": origin,

        "origin_trace": origin_analysis.get("origin_trace"),

        "origin_analysis": {
            "risk": origin_analysis.get("risk"),
            "correlation": origin_analysis.get("correlation"),
            "cache_stats": origin_analysis.get("cache_stats"),
        },

        "relatedCases": related,

        "caseHash": case_hash,

        "analysis": detailed,

        "dashboard": dashboard,
    }

    # ---------------------------------------------------------------
    # Persist the complete normalized case
    # ---------------------------------------------------------------

    store.add_case(
        {
            **parsed,

            "caseId": case_id,

            "analyzedAt": analyzed_at,

            "response": response,
        }
    )

    return response


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
)
async def analyze_email(
    file: UploadFile = File(...),
):
    content = await file.read()

    try:
        return await run_analysis(
            content,
            filename=file.filename,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
