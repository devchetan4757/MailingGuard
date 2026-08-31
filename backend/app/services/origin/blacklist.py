"""DNSBL / abuse checks per public IP.

- Spamhaus ZEN (aggregates SBL, XBL, PBL, CSS, DBL) via DNS query.
- Optional AbuseIPDB score, enabled only when ORIGIN_ABUSEIPDB_API_KEY is set
  (never hardcoded; the check is skipped without a key).

Results are cached per IP with the configured TTL; "not listed" is also cached
so repeated views cost nothing. ZEN queries are throttled to one per second to
stay within Spamhaus's free usage policy.

ZEN codes:
   2  SBL  (spam sender)
   3  CSS  (snowshoe)
   4  XBL  (exploited host)
   9  PBL  (policy - ISP says no direct email)
  10  PBL  (ISP range)
  11  PBL  (dynamic/consumer range)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from .cache import ResultCache
from .config import Config
from .iputils import redact_ip, reverse_pointer

logger = logging.getLogger(__name__)

ZEN_CODE_MEANING = {
    "2": "SBL - spam source",
    "3": "CSS - snowshoe spam",
    "4": "XBL - exploited host (open proxy/bot)",
    "9": "PBL - policy: no direct email from this range",
    "10": "PBL - ISP policy range",
    "11": "PBL - dynamic/consumer IP range",
}

ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"


class DnsResolver:
    """Minimal async-friendly DNS resolver built on dnspython.

    Runs blocking queries in a worker thread (with timeout) so the event loop
    never stalls; used for both ZEN queries and as a dependency-free PTR
    fallback when dnspython's resolver is not reachable.
    """

    def __init__(self, config: Config):
        self._zen_zone = config.dnsbl.zen_zone
        self._timeout = config.dnsbl.timeout_seconds
        self._min_interval = config.dnsbl.min_interval_seconds
        self._last_query = 0.0
        self._lock = asyncio.Lock()

    async def zen_lookup(self, ip: str) -> List[str]:
        """Return ZEN reply codes for an IP (empty list = not listed)."""
        import dns.resolver

        async with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last_query)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_query = time.monotonic()

        query_name = f"{reverse_pointer(ip)}.{self._zen_zone}"
        loop = asyncio.get_running_loop()

        def _query():
            try:
                answers = dns.resolver.resolve(
                    query_name, "A", lifetime=self._timeout
                )
                return sorted({r.to_text() for r in answers})
            except dns.resolver.NXDOMAIN:
                return []  # not listed
            except Exception:
                raise

        try:
            return await loop.run_in_executor(None, _query)
        except Exception as exc:
            # DNS failure != listing. Distinguish the two for the UI.
            raise LookupError(
                f"DNSBL query failed for {redact_ip(ip)}: {type(exc).__name__}"
            ) from exc


class BlacklistClient:
    """DNSBL (Spamhaus ZEN) + optional AbuseIPDB checks with caching."""

    def __init__(self, config: Config, cache: Optional[ResultCache] = None):
        self.config = config
        self.cache = cache or ResultCache(
            ttl_seconds=config.cache.ttl_seconds,
            error_ttl_seconds=config.cache.error_ttl_seconds,
            max_entries=config.cache.max_entries,
        )
        self._resolver = DnsResolver(config)

    async def check(self, ip: str) -> Dict[str, Any]:
        """Run every enabled abuse check for one public IP.

        Returns ``{listed, lists, codes, abuse_score, error, message, checked_at}``.
        """
        cached, _ = self.cache.get_dnsbl(ip)
        if cached is not None:
            cached = dict(cached)
            cached["cached"] = True
            return cached

        result: Dict[str, Any] = {
            "ip": ip,
            "listed": False,
            "lists": [],
            "codes": [],
            "abuse_score": None,
            "error": None,
            "message": None,
            "checked_at": None,
        }

        if not self.config.dnsbl.enabled:
            result["error"] = "disabled"
            result["message"] = "DNSBL checks are disabled by configuration"
            return result

        try:
            codes = await self._resolver.zen_lookup(ip)
        except LookupError as exc:
            result["error"] = "dns_error"
            result["message"] = str(exc)
            return result

        if codes:
            result["listed"] = True
            result["lists"].append("spamhaus-zen")
            # ZEN answers are 127.0.0.X; keep the human-readable code only.
            result["codes"] = sorted({c.rsplit(".", 1)[-1] for c in codes})
            result["meanings"] = [ZEN_CODE_MEANING.get(c, f"code {c}") for c in result["codes"]]

        if self.config.dnsbl.abuseipdb_api_key:
            score = await self._abuseipdb(ip)
            result["abuse_score"] = score
            if score is not None and score >= 50:
                result["listed"] = True
                result["lists"].append("abuseipdb")

        result["checked_at"] = time.time()
        self.cache.set_dnsbl(ip, result)
        return result

    async def _abuseipdb(self, ip: str) -> Optional[int]:
        """Best-effort AbuseIPDB score; None when the request fails."""
        key = self.config.dnsbl.abuseipdb_api_key
        try:
            async with httpx.AsyncClient(timeout=self.config.dnsbl.timeout_seconds) as client:
                response = await client.get(
                    ABUSEIPDB_URL,
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                    headers={"Key": key, "Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {}).get("abuseConfidenceScore")
        except Exception as exc:
            logger.warning("AbuseIPDB lookup failed for %s: %s", redact_ip(ip), type(exc).__name__)
            return None

