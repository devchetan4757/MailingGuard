"""
API contract (frozen) — see master doc, section 7.

Owner: integrator / backend lead.
Everyone else: don't edit this file. If your feature needs a new field,
propose it to the integrator so both frontend and backend stay in sync -
a silent change here breaks whoever built against the old shape.
"""

from typing import Literal, Optional
from pydantic import BaseModel

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


class AnalyzeResponse(BaseModel):
    caseId: str
    riskScore: int  # 0-100
    severity: Severity
    headerChecks: HeaderChecks
    aiSignals: AiSignals
    origin: Origin
    relatedCases: list[RelatedCase]
    caseHash: str


class CaseSummary(BaseModel):
    caseId: str
    riskScore: int
    severity: Severity
    analyzedAt: str
