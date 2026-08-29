"""
Dashboard response models for MailGuard.

These models define the data shape that the React dashboard can consume
after an email has been analyzed.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal[
    "green",
    "yellow",
    "red",
]


class AuthenticationStatus(BaseModel):
    result: str = "unknown"
    explanation: str = ""


class HeaderChecks(BaseModel):
    spf: str = "unknown"
    dkim: str = "unknown"
    dmarc: str = "unknown"

    senderDomainMismatch: bool = False


class DashboardMetrics(BaseModel):
    urlCount: int = 0
    suspiciousUrlCount: int = 0

    attachmentCount: int = 0
    suspiciousAttachmentCount: int = 0

    headerFindingCount: int = 0
    receivedHopCount: int = 0

    authenticationFailureCount: int = 0
    totalFindingCount: int = 0


class DashboardFinding(BaseModel):
    category: str
    signal: str
    severity: str
    points: int = 0
    message: str


class ParsedEmailSummary(BaseModel):
    filename: str | None = None

    sender: str | None = None
    senderDomain: str | None = None

    replyTo: str | None = None
    replyToDomain: str | None = None

    recipient: str | None = None
    subject: str | None = None
    date: str | None = None
    messageId: str | None = None

    originIp: str | None = None


class OriginInformation(BaseModel):
    ip: str | None = None
    country: str | None = None
    city: str | None = None

    isVpnOrHosting: bool = False


class AISignals(BaseModel):
    urgencyLanguage: str = "low"

    impersonationScore: float = 0.0

    summary: str = ""


class DashboardAnalysisResponse(BaseModel):
    """
    Main response consumed by the MailGuard dashboard.
    """

    caseId: str

    riskScore: int = Field(
        ge=0,
        le=100,
    )

    severity: RiskLevel

    headerChecks: HeaderChecks

    aiSignals: AISignals

    origin: OriginInformation

    parsedEmail: ParsedEmailSummary

    metrics: DashboardMetrics

    highlights: list[
        DashboardFinding
    ] = Field(
        default_factory=list
    )

    # Complete analyzer result is retained so detailed result pages can
    # display information without another analysis request.
    analysis: dict[str, Any] = Field(
        default_factory=dict
    )

    caseHash: str | None = None

    relatedCases: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    analyzedAt: str
