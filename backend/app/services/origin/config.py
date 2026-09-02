"""Single module-level configuration for Origin Analysis.

Every knob of the Origin Analysis feature lives in this file. Values are
overridable through environment variables with the ``ORIGIN_`` prefix, so the
module can be tuned without touching code (or a larger project's config
system).

Environment variables
---------------------
ORIGIN_GEO_BASE_URL          ip-api.com endpoint (free tier is HTTP-only)
ORIGIN_GEO_MOCK              "1"/"true" -> offline canned responses (demos/tests)
ORIGIN_GEO_TIMEOUT_SECONDS   per-lookup timeout
ORIGIN_GEO_RATE_PER_MINUTE   token-bucket budget (ip-api free tier: 45/min)
ORIGIN_CACHE_TTL_SECONDS     cache TTL for geo/rDNS/DNSBL results (default 24h)
ORIGIN_DNSBL_ENABLED         "0"/"false" disables Spamhaus ZEN checks
ORIGIN_ABUSEIPDB_API_KEY     optional key enabling AbuseIPDB abuse scores
ORIGIN_ASN_REPUTATION_ENABLED  "0"/"false" disables ASN reputation flags
ORIGIN_SUSPICIOUS_ASNS       comma-separated list, e.g. "AS9009,AS62240"
ORIGIN_CONFIDENCE_CITY_RADIUS_KM   conservative radius for city-level results
ORIGIN_CONFIDENCE_COUNTRY_RADIUS_KM  conservative radius for country-level results
ORIGIN_CORRELATION_PERSIST_PATH     optional JSON file for the case index
ORIGIN_LOG_REDACT_IPS        "0"/"false" disables IP masking in logs
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class GeoConfig:
    """ip-api.com lookups (geolocation + ISP/ASN + optional reverse)."""

    base_url: str = "http://ip-api.com/json/"
    # Free tier is HTTP-only and ignores `key`; switch to https://pro.ip-api.com
    # and set api_key when a paid key is configured.
    api_key: str = ""
    fields: str = (
        "status,message,country,countryCode,region,regionName,city,zip,lat,lon,"
        "timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query"
    )
    timeout_seconds: float = 5.0
    # ip-api free tier allows 45 HTTP requests/minute per source IP.
    # We keep a small safety margin so bursts never get blocked.
    max_requests_per_minute: int = 40
    ptr_timeout_seconds: float = 3.0
    mock: bool = False  # offline canned responses (demo mode / tests)


@dataclass(frozen=True)
class ConfidenceConfig:
    """Conservative accuracy radii, used because the free ip-api API does not
    return an accuracy field. City-level -> 50 km, country-only -> 500 km."""

    city_radius_km: float = 50.0
    country_radius_km: float = 500.0


@dataclass(frozen=True)
class CacheConfig:
    """IP-keyed cache for geolocation, reverse DNS and DNSBL results."""

    ttl_seconds: int = 86400          # default 24 hours
    error_ttl_seconds: int = 300      # failed lookups cached briefly
    max_entries: int = 10000


@dataclass(frozen=True)
class DnsblConfig:
    """DNSBL / abuse checks. Both optional and off by default where a key is
    required (AbuseIPDB); Spamhaus ZEN is enabled by default."""

    enabled: bool = True
    zen_zone: str = "zen.spamhaus.org"
    timeout_seconds: float = 5.0
    min_interval_seconds: float = 1.0   # politeness throttle between queries
    abuseipdb_api_key: str = ""         # empty = AbuseIPDB disabled


@dataclass(frozen=True)
class AsnReputationConfig:
    """Configurable list of suspicious ASNs. Empty list = no ASN flagged."""

    enabled: bool = True
    suspicious_asns: tuple = field(default_factory=tuple)
    # Examples of common bulletproof/hosting ASNs operators may want to list:
    # ("AS9009", "AS62240", "AS60068", "AS202425")


@dataclass(frozen=True)
class RiskConfig:
    """Exact origin-risk weightings fed into the existing case risk score.

    These are the ONLY signals this module contributes. The base score is
    computed by the existing risk engine and passed in untouched; this module
    only adds origin-derived points (see risk.apply_origin_risk).
    """

    weight_blacklist: int = 25          # DNSBL/abuse hit on any public hop
    weight_hosting_vpn: int = 15        # hosting/VPN flag on any public hop
    weight_asn_reputation: int = 10     # hop ASN in suspicious-ASN list
    weight_rdns_mismatch: int = 5       # header hostname != PTR record
    weight_geo_from_mismatch: int = 5   # hop country != From-domain MX country
    weight_geo_failure: int = 5         # geolocation unavailable (uncertainty)
    weight_delivery_delay: int = 5      # unusually long Received-hop delay
    max_contribution: int = 40          # cap so origin never dominates the score


@dataclass(frozen=True)
class CorrelationConfig:
    """Cross-case correlation index (same IP/ASN seen in other cases)."""

    persist_path: str = ""              # optional JSON file to persist the index
    max_recent_case_ids: int = 10


@dataclass(frozen=True)
class LoggingConfig:
    """Privacy: IPs in log records are masked (e.g. 203.0.113.x)."""

    redact_ips: bool = True


@dataclass(frozen=True)
class Config:
    geo: GeoConfig = field(default_factory=GeoConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    dnsbl: DnsblConfig = field(default_factory=DnsblConfig)
    asn_reputation: AsnReputationConfig = field(default_factory=AsnReputationConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    correlation: CorrelationConfig = field(default_factory=CorrelationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(env=None) -> Config:
    """Build a Config from environment variables (``ORIGIN_*``).

    ``env`` is injectable for tests; defaults to os.environ.
    """
    env = os.environ if env is None else env

    def get(name: str, default: str = "") -> str:
        return env.get(name, default)

    geo = GeoConfig(
        base_url=get("ORIGIN_GEO_BASE_URL", "http://ip-api.com/json/"),
        api_key=get("ORIGIN_GEO_API_KEY", ""),
        timeout_seconds=_env_float(get("ORIGIN_GEO_TIMEOUT_SECONDS"), 5.0),
        max_requests_per_minute=_env_int(get("ORIGIN_GEO_RATE_PER_MINUTE"), 40),
        ptr_timeout_seconds=_env_float(get("ORIGIN_GEO_PTR_TIMEOUT_SECONDS"), 3.0),
        mock=_env_bool(get("ORIGIN_GEO_MOCK"), False),
    )
    confidence = ConfidenceConfig(
        city_radius_km=_env_float(get("ORIGIN_CONFIDENCE_CITY_RADIUS_KM"), 50.0),
        country_radius_km=_env_float(get("ORIGIN_CONFIDENCE_COUNTRY_RADIUS_KM"), 500.0),
    )
    cache = CacheConfig(
        ttl_seconds=_env_int(get("ORIGIN_CACHE_TTL_SECONDS"), 86400),
        error_ttl_seconds=_env_int(get("ORIGIN_CACHE_ERROR_TTL_SECONDS"), 300),
        max_entries=_env_int(get("ORIGIN_CACHE_MAX_ENTRIES"), 10000),
    )
    dnsbl = DnsblConfig(
        enabled=_env_bool(get("ORIGIN_DNSBL_ENABLED"), True),
        zen_zone=get("ORIGIN_DNSBL_ZEN_ZONE", "zen.spamhaus.org"),
        timeout_seconds=_env_float(get("ORIGIN_DNSBL_TIMEOUT_SECONDS"), 5.0),
        min_interval_seconds=_env_float(get("ORIGIN_DNSBL_MIN_INTERVAL_SECONDS"), 1.0),
        abuseipdb_api_key=get("ORIGIN_ABUSEIPDB_API_KEY", ""),
    )
    asn_reputation = AsnReputationConfig(
        enabled=_env_bool(get("ORIGIN_ASN_REPUTATION_ENABLED"), True),
        suspicious_asns=tuple(
            a.strip()
            for a in get("ORIGIN_SUSPICIOUS_ASNS", "").split(",")
            if a.strip()
        ),
    )
    risk = RiskConfig(
        weight_blacklist=_env_int(get("ORIGIN_RISK_WEIGHT_BLACKLIST"), 25),
        weight_hosting_vpn=_env_int(get("ORIGIN_RISK_WEIGHT_HOSTING_VPN"), 15),
        weight_asn_reputation=_env_int(get("ORIGIN_RISK_WEIGHT_ASN_REPUTATION"), 10),
        weight_rdns_mismatch=_env_int(get("ORIGIN_RISK_WEIGHT_RDNS_MISMATCH"), 5),
        weight_geo_from_mismatch=_env_int(get("ORIGIN_RISK_WEIGHT_GEO_FROM_MISMATCH"), 5),
        weight_geo_failure=_env_int(get("ORIGIN_RISK_WEIGHT_GEO_FAILURE"), 5),
        weight_delivery_delay=_env_int(get("ORIGIN_RISK_WEIGHT_DELIVERY_DELAY"), 5),
        max_contribution=_env_int(get("ORIGIN_RISK_MAX_CONTRIBUTION"), 40),
    )
    correlation = CorrelationConfig(
        persist_path=get("ORIGIN_CORRELATION_PERSIST_PATH", ""),
        max_recent_case_ids=_env_int(get("ORIGIN_CORRELATION_MAX_RECENT"), 10),
    )
    logging_cfg = LoggingConfig(
        redact_ips=_env_bool(get("ORIGIN_LOG_REDACT_IPS"), True),
    )
    return Config(
        geo=geo,
        confidence=confidence,
        cache=cache,
        dnsbl=dnsbl,
        asn_reputation=asn_reputation,
        risk=risk,
        correlation=correlation,
        logging=logging_cfg,
    )


CONFIG = load_config()
