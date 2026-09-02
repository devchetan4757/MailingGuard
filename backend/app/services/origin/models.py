"""Pydantic models documenting the Origin Analysis JSON contract.

The full contract is also written out as origin_trace.schema.json next to this
code, so consumers/tooling can validate the extended `origin_trace` payload.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SuspiciousFlag(BaseModel):
    reason: str  # hosting_vpn | blacklist | asn_reputation | rdns_mismatch | geo_from_mismatch | delivery_delay
    detail: Optional[str] = None


class Confidence(BaseModel):
    level: str  # city | country | unknown
    radius_m: Optional[float] = None
    label: Optional[str] = None


class BlacklistInfo(BaseModel):
    checked: bool = False
    listed: bool = False
    lists: List[str] = []
    codes: List[str] = []
    meanings: Optional[List[str]] = None
    abuse_score: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    reason: Optional[str] = None  # e.g. "internal hop"
    cached: Optional[bool] = None


class TraceHop(BaseModel):
    ip: Optional[str] = None
    hostname: Optional[str] = None
    timestamp: Optional[str] = None  # ISO 8601 UTC
    order: int
    internal: bool = False
    warnings: List[str] = []
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    asname: Optional[str] = None
    reverse: Optional[str] = None
    hosting: Optional[bool] = None
    proxy: Optional[bool] = None
    mobile: Optional[bool] = None
    geo_error: Optional[str] = None
    geo_message: Optional[str] = None
    partial_failure: Optional[str] = None
    suspicious_flags: List[SuspiciousFlag] = []
    confidence: Optional[Confidence] = None
    blacklist: BlacklistInfo = Field(default_factory=BlacklistInfo)
    flagged: bool = False
    cached_at: Optional[str] = None


class GeoFailure(BaseModel):
    ip: str  # redacted for logging privacy
    message: Optional[str] = None


class TraceSummary(BaseModel):
    public_hops: int = 0
    internal_hops: int = 0
    suspicious_hops: int = 0
    blacklisted_hops: int = 0
    overall_suspicious: bool = False
    sending_ip: Optional[str] = None
    geo_failures: List[GeoFailure] = []


class TraceConfidence(BaseModel):
    method: str
    city_radius_m: Optional[float] = None
    country_radius_m: Optional[float] = None
    note: str


class OriginTrace(BaseModel):
    hops: List[TraceHop]
    summary: TraceSummary
    bounds: Optional[List[List[float]]] = None
    confidence: Optional[TraceConfidence] = None
    from_domain: Optional[str] = None
    from_domain_mx_country: Optional[str] = None


class LegacyOrigin(BaseModel):
    ip: Optional[str] = None
    hostname: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    reverse: Optional[str] = None
    hosting: Optional[bool] = None
    proxy: Optional[bool] = None
    mobile: Optional[bool] = None
    blacklisted: Optional[bool] = None
    abuse_score: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    confidence: Optional[Confidence] = None


class RiskResult(BaseModel):
    base_score: int
    origin_points: int
    origin_breakdown: Dict[str, bool]
    origin_capped: bool = False
    origin_max_contribution: int
    total_score: int


class CorrelationResult(BaseModel):
    ip_count: int
    asn_count: int
    recent_case_ids: List[str]


class AnalyzeResponse(BaseModel):
    origin: Optional[LegacyOrigin] = None
    origin_trace: Optional[OriginTrace] = None
    risk: Optional[RiskResult] = None
    correlation: Optional[CorrelationResult] = None
    cache_stats: Dict[str, int] = {}


class AnalyzeRequest(BaseModel):
    email: Dict[str, Any] = Field(default_factory=dict)
    from_domain: Optional[str] = None
    base_risk: int = 0
    base_risk_max: int = 100
    include_trace: bool = False
    case_id: Optional[str] = None


class CacheStatsResponse(BaseModel):
    stats: Dict[str, int]
    ttl_seconds: int
    config: Dict[str, Any]
