"""Origin-derived risk integration.

The case risk score is computed elsewhere ("the existing risk engine"); this
module only ADDS origin signals. Base score and existing caps are preserved
untouched -- the contribution below is clamped to ``risk.max_contribution`` so
Origin Analysis can never dominate or distort the other risk sources.

Exact weightings (all configurable via ``ORIGIN_RISK_WEIGHT_*``):

    +25  any public hop is on a DNSBL / has an abuse score >= 50
    +15  any public hop is flagged hosting/proxy/VPN by ip-api
    +10  any hop's ASN is on the configured suspicious-ASN list
     +5  header hostname does not match the PTR record (rDNS mismatch)
     +5  hop country != MX country of the From domain (geo inconsistency)
     +5  geolocation failed for at least one public hop (uncertainty)
    cap  max contribution: 40 points

No other risk source is modified.
"""

from __future__ import annotations

from typing import List, Optional

from .config import Config



def origin_risk_contribution(
    hops: List[dict],
    config: Config,
    from_domain_mx_country: Optional[str] = None,
) -> dict:
    """Compute the origin-derived points added to a case risk score.

    ``hops`` are the enriched hop dicts produced by the service. Returns a
    breakdown for auditing plus the clamped ``points`` value.
    """
    w = config.risk
    asn_flags_enabled = config.asn_reputation.enabled and bool(config.asn_reputation.suspicious_asns)

    points = 0
    breakdown = {
        "blacklist": False,
        "hosting_vpn": False,
        "asn_reputation": False,
        "rdns_mismatch": False,
        "geo_from_mismatch": False,
        "geo_failure": False,
    }

    for hop in hops:
        if hop.get("blacklist", {}).get("listed"):
            breakdown["blacklist"] = True
        if hop.get("hosting") or hop.get("proxy"):
            breakdown["hosting_vpn"] = True
        if asn_flags_enabled and hop.get("asn") in config.asn_reputation.suspicious_asns:
            breakdown["asn_reputation"] = True
        if hop.get("suspicious_flags"):
            for flag in hop["suspicious_flags"]:
                if flag.get("reason") == "rdns_mismatch":
                    breakdown["rdns_mismatch"] = True
                if flag.get("reason") == "geo_from_mismatch":
                    breakdown["geo_from_mismatch"] = True
        if hop.get("geo_error"):
            breakdown["geo_failure"] = True

    if breakdown["blacklist"]:
        points += w.weight_blacklist
    if breakdown["hosting_vpn"]:
        points += w.weight_hosting_vpn
    if breakdown["asn_reputation"]:
        points += w.weight_asn_reputation
    if breakdown["rdns_mismatch"]:
        points += w.weight_rdns_mismatch
    if breakdown["geo_from_mismatch"]:
        points += w.weight_geo_from_mismatch
    if breakdown["geo_failure"]:
        points += w.weight_geo_failure

    capped = min(points, w.max_contribution)
    return {
        "points": capped,
        "uncapped_points": points,
        "capped": capped < points,
        "breakdown": breakdown,
    }
