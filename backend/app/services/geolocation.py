"""
Epic 3 — origin tracing (Layer 3, reused free lookup + our flagging logic).

Owner: whoever is assigned Epic 3 in OWNERSHIP.md (same person as similarity.py).

CONTRACT:
    locate_ip(ip: str) -> dict
        Returns a dict shaped like ORIGIN_SHAPE below. Use a free geolocation
        API (see master doc, section 4, Layer 3) - don't build your own
        IP-to-location database.
"""

ORIGIN_SHAPE = {
    "ip": "",
    "country": None,
    "city": None,
    "isVpnOrHosting": False,
}


def locate_ip(ip: str) -> dict:
    # TODO (Epic 3): call a free geolocation API (e.g. ip-api.com, ipinfo.io).
    # Flag known VPN/hosting-provider ASNs as isVpnOrHosting = True - that's
    # an added suspicion signal per the master doc, not just decoration.
    return {
        "ip": ip,
        "country": None,
        "city": None,
        "isVpnOrHosting": False,
    }
