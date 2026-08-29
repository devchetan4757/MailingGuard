"""
Epic 3 — origin tracing (Layer 3, reused free lookup + our flagging logic).

Owner: whoever is assigned Epic 3 in OWNERSHIP.md (same person as similarity.py).

CONTRACT:
    locate_ip(ip: str) -> dict
        Returns a dict shaped like ORIGIN_SHAPE below. Use a free geolocation
        API (see master doc, section 4, Layer 3) - don't build your own
        IP-to-location database.
"""

import ipaddress

import httpx

ORIGIN_SHAPE = {
    "ip": "",
    "country": None,
    "city": None,
    "lat": None,
    "lng": None,
    "isVpnOrHosting": False,
}

IP_API_URL = "http://ip-api.com/json/{ip}"

TIMEOUT = 5


def _is_public_ip(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
        return (
            address.is_global
            and not address.is_private
            and not address.is_loopback
            and not address.is_reserved
        )
    except ValueError:
        return False


def locate_ip(ip: str) -> dict:
    """
    Resolve an IP to an approximate location and flag hosting/VPN
    infrastructure, via a free lookup (ip-api.com). Always returns the
    ORIGIN_SHAPE contract, even on failure, so callers never have to
    special-case a missing/invalid IP.
    """

    ip = (ip or "").strip()

    if not ip:
        return {**ORIGIN_SHAPE, "ip": ""}

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        # Not a parseable IP at all - still return the contract shape.
        return {**ORIGIN_SHAPE, "ip": ip}

    if not _is_public_ip(ip):
        # Private/loopback/reserved addresses aren't worth sending to a
        # public geolocation API - there's nothing to look up.
        return {**ORIGIN_SHAPE, "ip": ip}

    try:
        response = httpx.get(
            IP_API_URL.format(ip=ip),
            params={
                "fields": (
                    "status,message,query,country,countryCode,"
                    "regionName,city,zip,lat,lon,timezone,"
                    "isp,org,as,proxy,hosting"
                )
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            return {**ORIGIN_SHAPE, "ip": ip}

        is_proxy = bool(data.get("proxy"))
        is_hosting = bool(data.get("hosting"))

        # ip-api returns lat/lon as numbers (or omits them on partial
        # matches) - coerce defensively so a bad/missing value degrades to
        # None instead of raising or silently returning a string.
        lat = data.get("lat")
        lng = data.get("lon")

        try:
            lat = float(lat) if lat is not None else None
        except (TypeError, ValueError):
            lat = None

        try:
            lng = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lng = None

        return {
            "ip": data.get("query") or ip,
            "country": data.get("country"),
            "city": data.get("city"),
            "lat": lat,
            "lng": lng,
            "isVpnOrHosting": is_proxy or is_hosting,
        }

    except (httpx.HTTPError, ValueError):
        # Network failure, timeout, or bad JSON - degrade gracefully rather
        # than let a flaky third-party API break the whole /analyze call.
        return {**ORIGIN_SHAPE, "ip": ip}
