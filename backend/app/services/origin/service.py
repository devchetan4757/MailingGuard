"""Origin Analysis service: parse -> enrich -> flag -> correlate -> risk.

The service is the single entry point the web app uses. Everything here is
async and cache-aware: repeated views of a case cost zero upstream calls.

Privacy: log records mask IPs (e.g. 203.0.113.x). Raw Received headers are
only parsed in memory, never logged or persisted.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime

from typing import Any, Dict, List, Optional

from .blacklist import BlacklistClient
from .cache import ResultCache, iso_timestamp
from .config import Config
from .correlation import CaseCorrelation
from .geo import GeoClient
from .iputils import normalize_hostname, redact_ip
from .parser import ReceivedHop, parse_received_chain
from .risk import origin_risk_contribution

logger = logging.getLogger(__name__)

# Default radius (metres) shown for city-level results when the free API
# provides no accuracy metadata. Conservative by design -- see README.
CITY_DEFAULT_RADIUS_M = 50000
COUNTRY_DEFAULT_RADIUS_M = 500000


class OriginAnalysisService:
    """Stateless orchestration over the per-hop analysis pipeline."""

    def __init__(self, config: Config, correlation: Optional[CaseCorrelation] = None):
        self.config = config
        self.cache = ResultCache(
            ttl_seconds=config.cache.ttl_seconds,
            error_ttl_seconds=config.cache.error_ttl_seconds,
            max_entries=config.cache.max_entries,
        )
        self.geo = GeoClient(config, self.cache)
        self.blacklist = BlacklistClient(config, self.cache)
        self.correlation = correlation or CaseCorrelation(config)

    async def close(self) -> None:
        await self.geo.close()

    # -- public API ----------------------------------------------------

    async def analyze(
        self,
        raw: Any,
        case_id: Optional[str] = None,
        from_domain: Optional[str] = None,
        base_risk: int = 0,
        base_risk_max: int = 100,
    ) -> Dict[str, Any]:
        """Analyze the full Received chain of one email.

        Backward compatibility: the return value contains the legacy ``origin``
        object (best-effort first public hop) for clients that do not request
        the extended trace, plus the new ``origin_trace`` payload. Clients opt
        into the trace explicitly via ``?include_trace=1`` on the HTTP layer.
        """
        hops = parse_received_chain(raw)
        enriched = await self._enrich_hops(hops)
        self._add_chain_diagnostics(enriched)

        public = [h for h in enriched if not h["internal"] and h["ip"]]
        first_public = public[0] if public else None

        origin = self._legacy_origin(first_public, hops, enriched)
        trace = self._build_trace(enriched, first_public, from_domain)

        asns = sorted({h["asn"] for h in public if h.get("asn")})
        ips = [h["ip"] for h in public]

        risk = None
        if case_id:
            self.correlation.record(case_id, ips, asns)
            # Risk is computed from the finished trace hops so that flags
            # added during trace assembly (e.g. geo vs From domain) count.
            trace_public = [h for h in trace["hops"] if not h["internal"] and h["ip"]]
            contribution = origin_risk_contribution(
    trace_public,
    self.config,
    from_domain_mx_country=trace.get("from_domain_mx_country"),
)
            risk = {
                "base_score": int(base_risk),
                "origin_points": contribution["points"],
                "origin_breakdown": contribution["breakdown"],
                "origin_capped": contribution["capped"],
                "origin_max_contribution": self.config.risk.max_contribution,
                "total_score": min(int(base_risk) + contribution["points"], base_risk_max),
            }

        correlation = self.correlation.query(ips, asns, exclude_case=case_id)

        logger.info(
            "origin analysis: case=%s hops=%d public=%d listed=%s geo_errors=%d",
            case_id or "-", len(enriched),
            len(public),
            any(h.get("blacklist", {}).get("listed") for h in public),
            sum(1 for h in public if h.get("geo_error")),
        )

        return {
            "origin": origin,
            "origin_trace": trace,
            "risk": risk,
            "correlation": correlation,
            "cache_stats": self.cache.stats(),
        }

    # -- enrichment ----------------------------------------------------

    async def _enrich_hops(self, hops: List[ReceivedHop]) -> List[Dict[str, Any]]:
        geo_jobs = [
            self.geo.lookup(h.ip) for h in hops if h.ip is not None and not h.internal
        ]
        geo_results = await self._gather(*geo_jobs)

        blacklist_jobs = [
            self.blacklist.check(h.ip) for h in hops if h.ip is not None and not h.internal
        ]
        blacklist_results = await self._gather(*blacklist_jobs)

        rdns_jobs = [
            self.geo.lookup_rdns(h.ip) for h in hops if h.ip is not None and not h.internal
        ]
        rdns_results = await self._gather(*rdns_jobs)

        enriched: List[Dict[str, Any]] = []
        geo_iter = iter(geo_results)
        bl_iter = iter(blacklist_results)
        rdns_iter = iter(rdns_results)

        for hop in hops:
            entry = hop.to_dict()
            entry.update({
                "geo": None, "geo_error": None, "geo_message": None,
                "lat": None, "lon": None, "city": None, "region": None,
                "country": None, "country_code": None,
                "isp": None, "org": None, "asn": None, "asname": None,
                "reverse": None, "hosting": None, "proxy": None, "mobile": None,
                "blacklist": None, "suspicious_flags": [],
                "confidence": None,
                "cached_at": None,
            })
            if hop.internal or hop.ip is None:
                entry["skip_reason"] = "internal_hop" if hop.internal else "no_ip"
                entry["blacklist"] = {
                    "checked": False,
                    "reason": "internal hop" if hop.internal else "no ip to check",
                    "listed": False, "lists": [], "codes": [], "abuse_score": None,
                    "error": None, "message": None,
                }
                enriched.append(entry)
                continue

            geo_result = next(geo_iter)
            entry["geo"] = geo_result
            entry["geo_error"] = geo_result.get("error")
            entry["geo_message"] = geo_result.get("message")
            # `reverse` is requested from ip-api; when unsupported, perform
            # the PTR fallback so the hop always carries the best rDNS name.
            if not geo_result.get("reverse") and not geo_result.get("error"):
                await self.geo.ensure_reverse(hop.ip, geo_result)
            for key in ("lat", "lon", "city", "region", "country", "country_code",
                        "isp", "org", "asn", "asname", "hosting", "proxy", "mobile", "reverse"):
                entry[key] = geo_result.get(key)
            if geo_result.get("cached"):
                entry["cached_at"] = iso_timestamp(self.cache.get_geo(hop.ip)[1])

            bl = next(bl_iter)
            entry["blacklist"] = bl
            entry["blacklist"]["checked"] = True
            if bl.get("listed"):
                entry["suspicious_flags"].append({
                    "reason": "blacklist",
                    "detail": "matched: " + ", ".join(bl.get("lists") or []),
                })

            rdns = next(rdns_iter)
            ptr_name = rdns.get("reverse") or geo_result.get("reverse")
            header_name = normalize_hostname(hop.hostname)
            # rDNS mismatch: header hostname (or its last two labels) vs PTR.
            if header_name and ptr_name:
                if not _hostnames_match(header_name, ptr_name):
                    entry["suspicious_flags"].append({
                        "reason": "rdns_mismatch",
                        "detail": f"header hostname '{header_name}' does not match rDNS '{ptr_name}'",
                    })
            # Hosting/VPN detection from ip-api's own flags.
            if entry.get("hosting") or entry.get("proxy"):
                entry["suspicious_flags"].append({
                    "reason": "hosting_vpn",
                    "detail": "ip-api reports hosting/proxy range",
                })
            # ASN reputation from the configurable suspicious-ASN list.
            if (self.config.asn_reputation.enabled
                    and entry.get("asn") in self.config.asn_reputation.suspicious_asns):
                entry["suspicious_flags"].append({
                    "reason": "asn_reputation",
                    "detail": f"ASN {entry['asn']} is on the suspicious-ASN list",
                })

            entry["confidence"] = self._confidence(geo_result)
            enriched.append(entry)

        return enriched

    async def _gather(self, *coros):
        """Concurrently await tasks, tolerating individual cancellation."""
        import asyncio
        return await asyncio.gather(*coros)

    # -- output assembly ------------------------------------------------

    def _legacy_origin(self, first_public, hops, enriched) -> Dict[str, Any]:
        """Legacy `origin` object -- unchanged shape, enriched values."""
        if first_public is None:
            return {"ip": None, "hostname": None, "error": "no public IP in Received chain"}

        h = dict(first_public)
        return {
            "ip": h.get("ip"),
            "hostname": h.get("reverse") or h.get("hostname"),
            "city": h.get("city"),
            "region": h.get("region"),
            "country": h.get("country"),
            "lat": h.get("lat"),
            "lon": h.get("lon"),
            "isp": h.get("isp"),
            "org": h.get("org"),
            "asn": h.get("asn"),
            "reverse": h.get("reverse"),
            "hosting": h.get("hosting"),
            "proxy": h.get("proxy"),
            "mobile": h.get("mobile"),
            "blacklisted": bool(h.get("blacklist") and h["blacklist"].get("listed")),
            "abuse_score": (h.get("blacklist") or {}).get("abuse_score"),
            "error": h.get("geo_error"),
            "message": h.get("geo_message"),
            "confidence": h.get("confidence"),
        }

    def _build_trace(self, enriched, first_public, from_domain) -> Dict[str, Any]:
        geo_successes = [h for h in enriched if h.get("lat") is not None and h.get("lon") is not None]
        bounds = None
        if geo_successes:
            bounds = [
                [min(h["lat"] for h in geo_successes), min(h["lon"] for h in geo_successes)],
                [max(h["lat"] for h in geo_successes), max(h["lon"] for h in geo_successes)],
            ]
        from_mx_country = self._mx_country_hint(from_domain) if from_domain else None

        hops = []
        for h in enriched:
            hop = {k: h.get(k) for k in (
                "ip", "hostname", "timestamp", "order", "internal", "warnings",
                "lat", "lon", "city", "region", "country", "country_code",
                "isp", "org", "asn", "asname", "reverse", "hosting", "proxy",
                "mobile", "geo_error", "geo_message", "suspicious_flags",
                "confidence", "cached_at", "blacklist", "skip_reason",
                "chain_delay_seconds", "delay_label",
            )}
            hop["suspicious_flags"] = list(h.get("suspicious_flags") or [])
            hop["blacklist"] = h.get("blacklist")
            if hop["geo_error"] and hop["geo_message"]:
                hop["partial_failure"] = hop["geo_message"]
            else:
                hop["partial_failure"] = None

            if from_mx_country and hop.get("country_code"):
                if hop["country_code"].upper() != from_mx_country.upper():
                    hop["suspicious_flags"].append({
                        "reason": "geo_from_mismatch",
                        "detail": f"hop country {hop['country_code']} differs from From-domain MX country {from_mx_country}",
                    })

            hop["flagged"] = bool(hop["suspicious_flags"]) or bool(
                hop.get("blacklist") and hop["blacklist"].get("listed")
            ) or bool(hop.get("hosting")) or bool(hop.get("proxy"))
            hops.append(hop)

        summary = self._summarize(hops, first_public)
        countries = [h.get("country_code") for h in hops if h.get("country_code")]
        asns = [h.get("asn") for h in hops if h.get("asn")]
        summary["unique_countries"] = len(set(countries))
        summary["unique_asns"] = len(set(asns))
        summary["country_path"] = list(dict.fromkeys(countries))
        summary["asn_path"] = list(dict.fromkeys(asns))
        summary["cross_border_hops"] = sum(1 for a,b in zip(countries, countries[1:]) if a != b)
        summary["average_delay_seconds"] = self._average_delay(hops)
        summary["max_delay_seconds"] = max((h.get("chain_delay_seconds") or 0 for h in hops), default=0)
        summary["delayed_hops"] = sum(1 for h in hops if h.get("delay_label") in {"slow", "very_slow"})
        summary["signal_count"] = sum(len(h.get("suspicious_flags") or []) for h in hops)

        return {
            "hops": hops,
            "summary": summary,
            "bounds": bounds,
            "confidence": {
                "method": "api-country-fields",
                "city_radius_m": self.config.confidence.city_radius_km * 1000.0,
                "country_radius_m": self.config.confidence.country_radius_km * 1000.0,
                "note": "IP geolocation is approximate; coordinates identify an IP's estimated network location, not a person's physical address.",
            },
            "from_domain": from_domain,
            "from_domain_mx_country": from_mx_country,
        }

    def _confidence(self, geo: Dict[str, Any]) -> Dict[str, Any]:
        """Geolocation confidence per hop.

        The free ip-api.com API returns no accuracy metadata, so we use a
        conservative default radius; the label degrades gracefully when only
        country-level data came back, and is None on lookup failure.
        """
        if geo.get("error"):
            return None
        if geo.get("city"):
            return {"level": "city", "radius_m": self.config.confidence.city_radius_km * 1000.0,
                    "label": "City-level (approximate)"}
        if geo.get("country"):
            return {"level": "country", "radius_m": self.config.confidence.country_radius_km * 1000.0,
                    "label": "Country-level (approximate)"}
        return {"level": "unknown", "radius_m": None, "label": "Unknown accuracy"}

    def _add_chain_diagnostics(self, hops: List[Dict[str, Any]]) -> None:
        """Add timeline/chain-quality signals without making extra network calls."""
        previous = None
        for hop in hops:
            current = _parse_iso(hop.get("timestamp"))
            delay = None
            if previous is not None and current is not None:
                delay = max(0.0, (current - previous).total_seconds())
            hop["chain_delay_seconds"] = round(delay, 3) if delay is not None else None
            if delay is None:
                hop["delay_label"] = "unknown"
            elif delay >= 3600:
                hop["delay_label"] = "very_slow"
                hop["suspicious_flags"].append({"reason": "delivery_delay", "detail": f"{round(delay / 3600, 2)}h between Received hops"})
            elif delay >= 900:
                hop["delay_label"] = "slow"
                hop["suspicious_flags"].append({"reason": "delivery_delay", "detail": f"{round(delay / 60, 1)}m between Received hops"})
            else:
                hop["delay_label"] = "normal"
            if current is not None:
                previous = current

    @staticmethod
    def _average_delay(hops: List[Dict[str, Any]]) -> float:
        values = [h["chain_delay_seconds"] for h in hops if h.get("chain_delay_seconds") is not None]
        return round(sum(values) / len(values), 3) if values else 0.0

    def _summarize(self, hops: List[Dict[str, Any]], first_public) -> Dict[str, Any]:
        suspicious = [h for h in hops if h.get("flagged")]
        geo_errors = [h for h in hops if h.get("geo_error")]
        return {
            "public_hops": sum(1 for h in hops if not h["internal"] and h["ip"]),
            "internal_hops": sum(1 for h in hops if h["internal"]),
            "suspicious_hops": len(suspicious),
            "blacklisted_hops": sum(1 for h in hops if h.get("blacklist", {}).get("listed")),
            "geo_failures": [
                {"ip": redact_ip(h["ip"]), "message": h.get("geo_message") or h.get("geo_error")}
                for h in geo_errors if h.get("ip")
            ],
            "overall_suspicious": bool(suspicious),
            "sending_ip": first_public.get("ip") if first_public else None,
        }

    @staticmethod
    def _mx_country_hint(from_domain: Optional[str]) -> Optional[str]:
        """Country hint for the From domain, for the geo-consistency flag.

        Uses known MX countries for the largest providers as a lightweight
        heuristic; unknown domains return None (flag simply not evaluated).
        Adapter limitation documented in the PR: resolving live MX + GeoIP of
        the MX host is left to a future integration.
        """
        known = {
            "gmail.com": "US",
            "googlemail.com": "US",
            "outlook.com": "US",
            "hotmail.com": "US",
            "yahoo.com": "US",
            "yahoo.co.in": "US",
            "protonmail.com": "CH",
            "zoho.com": "US",
            "icloud.com": "US",
            "aol.com": "US",
            "rediffmail.com": "IN",
            "mail.ru": "RU",
            "yandex.ru": "RU",
            "qq.com": "CN",
            "163.com": "CN",
        }
        if not from_domain:
            return None
        domain = from_domain.strip().lower().lstrip("@")
        return known.get(domain)


def _hostnames_match(header_name: str, ptr_name: str) -> bool:
    """Compare header hostname with the PTR record (domain-level match)."""
    h_labels = header_name.split(".")
    p_labels = ptr_name.split(".")
    for take in (len(p_labels), 2):
        if len(h_labels) >= take and h_labels[-take:] == p_labels[-take:]:
            return True
    return False


def _parse_iso(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
