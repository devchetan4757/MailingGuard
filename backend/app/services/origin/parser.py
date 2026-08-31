"""Multi-hop Received-header chain parser.

Parses every ``Received:`` header into an ordered list of hops:

    {"ip": "<ip>", "hostname": "<hostname or null>", "timestamp": "<ISO8601 or null>"}

- Order is sender -> relays -> recipient (chronological). Raw mail stores
  Received headers newest-first, so the collected headers are reversed.
- Private/internal hops are KEPT (``internal: true``) but only public IPs are
  geolocated downstream.
- Malformed entries are kept with ``ip: null`` and a ``warnings`` list; they
  never crash the chain.

The hop dict also carries ``order``, ``internal`` and ``warnings`` keys as
documented extensions (see origin_trace.schema.json).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional, Union

from .iputils import is_ip, is_public, normalize_hostname, parse_ip

_IPV4 = r"\d{1,3}(?:\.\d{1,3}){3}"
_IPV6 = r"[0-9a-fA-F:]{2,}(?::\d{1,3}(?:\.\d{1,3}){3})?"
_IP = r"(?:" + _IPV4 + r"|" + _IPV6 + r")"

# A Received header looks like:
#   Received: from <from-part> by <host> (sw) with <proto> id <id> for <rcpt>; <date>
_FROM_PART = re.compile(
    r"\bfrom\b\s+(?P<from>.*?)(?=\s+by\s+|\s+with\s+|\s+via\s+|\s+for\s+|\s+id\s+|;|$)",
    re.IGNORECASE | re.DOTALL,
)
_BRACKETED_IP = re.compile(rf"\[(?P<ip>{_IP})\]", re.IGNORECASE)
_NAKED_IP = re.compile(rf"(?<![.\w:])(?P<ip>{_IP})(?![.\w:])", re.IGNORECASE)
_HOST_TOKEN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", re.IGNORECASE)
_TIMESTAMP = re.compile(r";\s*(?P<ts>.+?)\s*$", re.DOTALL)
_HELO_BLOCK = re.compile(r"\(\s*helo=([^);]*)\)", re.IGNORECASE)

_RECEIVED_START = re.compile(r"^\s*received\s*:", re.IGNORECASE)


class ReceivedHop:
    """One parsed hop of the delivery path."""

    __slots__ = ("ip", "hostname", "timestamp", "order", "header_index",
                 "internal", "warnings", "raw")

    def __init__(self, ip, hostname, timestamp, order, header_index,
                 internal, warnings, raw):
        self.ip = ip
        self.hostname = hostname
        self.timestamp = timestamp
        self.order = order
        self.header_index = header_index
        self.internal = internal
        self.warnings = warnings
        self.raw = raw  # never serialized/logged (privacy)

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "timestamp": self.timestamp,
            "order": self.order,
            "internal": self.internal,
            "warnings": list(self.warnings),
        }

    def __repr__(self) -> str:
        return f"<ReceivedHop order={self.order} ip={self.ip or '-'}>"


def extract_received_headers(raw: Union[str, List[str]]) -> List[str]:
    """Return individual Received header values in top-to-bottom order.

    Accepts either a raw header block (multi-line string, folded headers
    included) or an already-extracted list of Received header values.
    """
    if isinstance(raw, list):
        return [str(v) for v in raw if v and str(v).strip()]
    collected: List[str] = []
    current: Optional[str] = None
    for line in str(raw).splitlines():
        if _RECEIVED_START.match(line):
            if current is not None:
                collected.append(current)
            current = line
        elif current is not None and line[:1] in (" ", "\t"):
            current += " " + line.strip()
        elif current is not None:
            collected.append(current)
            current = None
    if current is not None:
        collected.append(current)
    return collected


def _parse_timestamp(header: str, warnings: List[str]) -> Optional[str]:
    """Extract the trailing ``; <date>`` and return it as ISO 8601 (UTC)."""
    match = _TIMESTAMP.search(header)
    if not match:
        warnings.append("no timestamp found")
        return None
    raw_ts = match.group("ts").strip()
    # Some chains carry two dates ("; Sat, ... ; Sat, ..."). Keep the last one
    # (the actual hand-off time at this hop's receiving host).
    raw_ts = raw_ts.rsplit(";", 1)[-1].strip()
    try:
        parsed = parsedate_to_datetime(raw_ts)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        warnings.append(f"unparseable timestamp: {raw_ts!r}")
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def parse_received_header(value: str) -> dict:
    """Parse a single Received header value into a hop dict.

    Fields: ip, hostname, timestamp (all nullable), plus warnings.
    """
    warnings: List[str] = []
    header = value.strip()
    ip: Optional[str] = None
    hostname: Optional[str] = None

    from_match = _FROM_PART.search(header)
    from_part = from_match.group("from") if from_match else ""

    if not from_part:
        warnings.append("no 'from' clause found")
    else:
        # Preferred: the bracketed IP inside the from clause, e.g.
        #   from mail.example.org ([203.0.113.5])
        #   from [203.0.113.5] (helo=mail.example.org)
        bracketed = _BRACKETED_IP.search(from_part)
        if bracketed:
            raw_ip = bracketed.group("ip")
            if is_ip(raw_ip):
                ip = raw_ip
                prefix = from_part[: bracketed.start("ip")]
                # Hostname is either the token before the brackets
                # ("mail.example.org [...]") or the helo= value ("[ip] (helo=...)").
                hostname = _hostname_before(prefix) or _helo_hostname(from_part)
            else:
                warnings.append(f"unrecognized IP in from clause: {raw_ip!r}")
        else:
            # e.g. "from 203.0.113.5 by mx.example.org ..."
            naked = _NAKED_IP.search(from_part)
            if naked:
                ip = naked.group("ip")
            else:
                warnings.append("no IP address found in from clause")

    timestamp = _parse_timestamp(header, warnings)

    return {
        "ip": ip,
        "hostname": hostname,
        "timestamp": timestamp,
        "warnings": warnings,
    }


def _hostname_before(prefix: str) -> Optional[str]:
    """Hostname token immediately before the bracketed IP, when present."""
    prefix = prefix.rstrip()
    helo = _HELO_BLOCK.search(prefix)
    if helo:
        candidate = helo.group(1).strip().strip("[]")
    else:
        candidate = None
        tokens = [t for t in prefix.replace("(", " ").replace(")", " ").split() if t]
        # Walk backwards past non-hostname artifacts (e.g. the trailing '[').
        for token in reversed(tokens):
            token = token.strip("[]")
            if _HOST_TOKEN.fullmatch(token) and not is_ip(token):
                candidate = token
                break
    if candidate and is_ip(candidate):
        return None
    return normalize_hostname(candidate)


def _helo_hostname(from_part: str) -> Optional[str]:
    """Fall back to the helo= value when nothing else names the sender."""
    helo = _HELO_BLOCK.search(from_part)
    if not helo:
        return None
    candidate = helo.group(1).strip().strip("[]")
    if is_ip(candidate):
        return None
    return normalize_hostname(candidate)


def parse_received_chain(raw: Union[str, List[str]]) -> List[ReceivedHop]:
    """Parse every Received header into an ordered hop list.

    Returns hops in sender -> relays -> recipient (chronological) order.
    Private/internal hops are kept with ``internal=True``; malformed entries
    are kept with ``ip=None`` and a warning.
    """
    headers = extract_received_headers(raw)
    hops: List[ReceivedHop] = []

    # Headers are collected top-to-bottom, i.e. newest first (closest to the
    # recipient). Reverse to get the sender -> recipient order.
    chronological = list(reversed(headers))

    for order, header in enumerate(chronological):
        parsed = parse_received_header(header)
        ip = parsed["ip"]
        if ip is not None:
            parsed["ip"] = str(parse_ip(ip))
        hops.append(
            ReceivedHop(
                ip=parsed["ip"],
                hostname=parsed["hostname"],
                timestamp=parsed["timestamp"],
                order=order,
                header_index=len(headers) - 1 - order,
                internal=ip is not None and not is_public(ip),
                warnings=parsed["warnings"],
                raw=header,
            )
        )

    _flag_out_of_order_timestamps(hops)
    return hops


def _to_datetime(timestamp: str) -> Optional[datetime]:
    """Parse an ISO 8601 or RFC 2822 timestamp into a tz-aware datetime."""
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(timestamp)
        except (TypeError, ValueError):
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _flag_out_of_order_timestamps(hops: List[ReceivedHop]) -> None:
    """Add a warning when timestamps are not monotonically increasing."""
    previous: Optional[datetime] = None
    for hop in hops:
        if hop.timestamp is None:
            continue
        current = _to_datetime(hop.timestamp)
        if current is None:
            continue
        if previous is not None and current < previous:
            hop.warnings.append("timestamp earlier than previous hop")
        previous = current


def public_hops(hops: List[ReceivedHop]) -> List[ReceivedHop]:
    """Only hops with a public, geolocatable IP (internal relays excluded)."""
    return [h for h in hops if h.ip is not None and not h.internal]
