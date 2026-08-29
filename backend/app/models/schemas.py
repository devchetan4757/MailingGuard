"""
MailGuard API response models.

The original API fields remain unchanged for compatibility.
The additional analysis/dashboard fields expose the richer analyzer output
to the frontend without requiring the frontend to re-analyze the email.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal["green", "yellow", "red"]


class HeaderChecks(BaseModel):
    spf: Literal["pass", "fail", "none"]
    dkim: Literal["pass", "fail", "none"]
    dmarc: Literal["pass", "fail", "none"]
    senderDomainMismatch: bool


class AiSignals(BaseModel):
    urgencyLanguage: Literal["low", "medium", "high"]
    impersonationScore: float
    summary: str


class Origin(BaseModel):
    ip: str
    country: Optional[str] = None
    city: Optional[str] = None
    isVpnOrHosting: bool = False


class RelatedCase(BaseModel):
    caseId: str
    similarity: float
    matchedOn: list[str]


class DashboardMetrics(BaseModel):
    """
    Metrics directly usable by dashboard cards and charts.
    """

    urlCount: int = 0
    suspiciousUrlCount: int = 0

    attachmentCount: int = 0
    suspiciousAttachmentCount: int = 0

    headerFindingCount: int = 0

    receivedHopCount: int = 0

    authenticationFailureCount: int = 0

    totalFindingCount: int = 0


class DashboardRisk(BaseModel):
    score: int = 0
    severity: Severity = "green"

    distribution: list[dict[str, Any]] = Field(
        default_factory=list
    )


class DashboardAuthentication(BaseModel):
    name: str
    result: str
    status: str
    value: int = 0


class DashboardFindingSeverity(BaseModel):
    name: str
    value: int


class DashboardThreatCategory(BaseModel):
    name: str
    value: int


class DashboardContentRisk(BaseModel):
    name: str
    total: int = 0
    suspicious: int = 0


class DashboardData(BaseModel):
    """
    Complete visualization payload generated from the actual analysis.
    """

    risk: DashboardRisk = Field(
        default_factory=DashboardRisk
    )

    authentication: list[DashboardAuthentication] = Field(
        default_factory=list
    )

    threatCategories: list[DashboardThreatCategory] = Field(
        default_factory=list
    )

    findingSeverity: list[DashboardFindingSeverity] = Field(
        default_factory=list
    )

    contentRisk: list[DashboardContentRisk] = Field(
        default_factory=list
    )

    metrics: DashboardMetrics = Field(
        default_factory=DashboardMetrics
    )

    findings: list[dict[str, Any]] = Field(
        default_factory=list
    )


class AnalyzeResponse(BaseModel):
    """
    Main /api/analyze response.

    Existing fields are preserved. `analysis` contains the detailed analyzer
    result and dashboard-ready visualization data.
    """

    caseId: str
    riskScore: int
    severity: Severity

    headerChecks: HeaderChecks

    aiSignals: AiSignals

    origin: Origin

    relatedCases: list[RelatedCase]

    caseHash: str

    analysis: Optional[dict[str, Any]] = None

    dashboard: Optional[DashboardData] = None


class CaseSummary(BaseModel):
    caseId: str
    riskScore: int
    severity: Severity
    analyzedAt: str
