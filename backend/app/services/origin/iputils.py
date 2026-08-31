"""IP helpers: public/private detection, PTR (reverse DNS) lookups, masking.

Network-independent pure helpers are unit-testable without sockets; the PTR
lookup runs in a worker thread with a hard timeout so it never blocks the
async event loop longer than configured.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import threading
from typing import Optional

_IP_TOKEN = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

# IANA documentation ranges are not routable in the real Internet but are
# treated as public by the parser so fixtures/tests mirror real chains.
_DOCUMENTATION_NETS = tuple(
    ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)


def is_ip(value: Optional[str]) -> bool:
    """True when ``value`` is a syntactically valid IP address."""
    if not value:
        return False
    return parse_ip(value) is not None


def parse_ip(value: Optional[str]) -> Optional[ipaddress._BaseAddress]:
    """Parse an address, returning None when it is not a valid IP."""
    if not value:
        return None
    value = value.strip().strip("[]")
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def is_public(ip: Optional[str]) -> bool:
    """True when ``ip`` is a globally routable (geolocatable) address.

    Private, loopback, link-local, reserved, multicast and unspecified
    addresses are treated as internal relay hops: they are kept in the trace
    but never geolocated. IANA documentation ranges (TEST-NET-1/2/3) are
    deliberately treated as public so test fixtures behave like real chains
    (live geolocation for them simply fails with an explicit error).
    """
    addr = parse_ip(ip)
    if addr is None:
        return False
    if any(addr in net for net in _DOCUMENTATION_NETS):
        return True
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def normalize_hostname(value: Optional[str]) -> Optional[str]:
    """Lower-case a hostname and strip a trailing dot for comparisons."""
    if not value:
        return None
    value = value.strip().strip("[]").lower().rstrip(".")
    if value in ("", "unknown", "localhost", "[127.0.0.1]"):
        return None
    return value


def normalize_asn(value: Optional[str]) -> Optional[str]:
    """Extract a canonical ASN (``AS15169``) from free-text values such as
    ``"AS15169 Google LLC"`` or ``"15169"``."""
    if not value:
        return None
    match = re.search(r"\bAS?(\d+)\b", value, re.IGNORECASE)
    if not match:
        return None
    return f"AS{match.group(1)}"


def reverse_pointer(ip: str) -> str:
    """in-addr.arpa / ip6.arpa reverse pointer name for an IP."""
    addr = ipaddress.ip_address(ip)
    return addr.reverse_pointer


def redact_ip(value: Optional[str]) -> str:
    """Mask the host part of an IP for logs (203.0.113.x / 2001:db8::x)."""
    if not value:
        return "<no-ip>"
    addr = parse_ip(value)
    if addr is None:
        return value
    if addr.version == 4:
        parts = str(addr).split(".")
        return f"{parts[0]}.{parts[1]}.x.x"
    hextets = str(addr).split(":")
    return ":".join(hextets[:4]) + "::x"


def ptr_lookup(ip: str, timeout: float = 3.0) -> Optional[str]:
    """Best-effort reverse DNS (PTR) lookup with a hard timeout.

    Returns the canonical hostname or None. Never raises: DNS failures and
    timeouts simply mean "no rDNS available".
    """
    result: dict = {}

    def _worker() -> None:
        try:
            name, _, _ = socket.gethostbyaddr(ip)
            result["name"] = name if isinstance(name, str) else name[0]
        except Exception:
            result["name"] = None

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout)
    return normalize_hostname(result.get("name"))
