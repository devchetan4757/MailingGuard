"""Geolocation + ISP/ASN/rDNS resolution via ip-api.com.

- One bulk request per public hop (lat, lon, city, region, country, isp, org,
  as, asname, reverse, mobile, proxy, hosting).
- `reverse` (rDNS) is requested from the API when supported; when the API
  response lacks it, a native PTR lookup is the fallback.
- All results are cached per IP with the configured TTL; lookup errors are
  cached briefly and surface as explicit partial-failure messages instead of
  being swallowed.
- Requests run concurrently through a token-bucket rate limiter and are fully
  non-blocking (async httpx), so the case UI never stalls on network I/O.

NOTE: ip-api.com's free tier allows 45 requests/minute from one source IP and
does not support HTTPS or an API key. When a paid key is configured the URL
switches to https://pro.ip-api.com automatically.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any, Dict, Optional

import httpx

from .cache import ResultCache
from .config import Config
from .iputils import normalize_asn, normalize_hostname, ptr_lookup, redact_ip

logger = logging.getLogger(__name__)

MOCK_GEO: Dict[str, Dict[str, Any]] = {
    # Deterministic canned data for offline demos and unit tests. Enabled via
    # ORIGIN_GEO_MOCK=1. The PTR fields here are plausible but not real.
    "8.8.8.8": {
        "status": "success", "country": "United States", "countryCode": "US",
        "region": "California", "regionName": "California", "city": "Mountain View",
        "lat": 37.4056, "lon": -122.0775, "isp": "Google LLC",
        "org": "Google Public DNS", "as": "AS15169 Google LLC", "asname": "GOOGLE",
        "reverse": "dns.google", "mobile": False, "proxy": False, "hosting": False,
    },
    "8.8.4.4": {
        "status": "success", "country": "United States", "countryCode": "US",
        "region": "California", "regionName": "California", "city": "Mountain View",
        "lat": 37.4056, "lon": -122.0775, "isp": "Google LLC",
        "org": "Google Public DNS", "as": "AS15169 Google LLC", "asname": "GOOGLE",
        "reverse": "dns.google", "mobile": False, "proxy": False, "hosting": False,
    },
    "5.188.86.0": {
        "status": "success", "country": "Russia", "countryCode": "RU",
        "region": "St.-Petersburg", "regionName": "Saint Petersburg",
        "city": "Saint Petersburg", "lat": 59.9311, "lon": 30.3609,
        "isp": "Petersburg Internet Network ltd.",
        "org": "Petersburg Internet Network ltd.",
        "as": "AS9009 M247 Europe SRL", "asname": "M247",
        "reverse": None, "mobile": False, "proxy": True, "hosting": True,
    },
    "185.45.12.9": {
        "status": "success", "country": "Czechia", "countryCode": "CZ",
        "region": "Prague", "regionName": "Prague",
        "city": "Prague", "lat": 50.0755, "lon": 14.4378,
        "isp": "HOSTPRO s.r.o.",
        "org": "HostPro",
        "as": "AS197197 HOSTPRO s.r.o.", "asname": "HOSTPRO",
        "reverse": "mx1.hostpro.net", "mobile": False, "proxy": False, "hosting": True,
    },
    "203.0.113.9": {
        "status": "success", "country": "United States", "countryCode": "US",
        "region": "Virginia", "regionName": "Virginia",
        "city": "Ashburn", "lat": 39.0438, "lon": -77.4874,
        "isp": "Example Hosting LLC",
        "org": "Customer VPS",
        "as": "AS64500 EXAMPLE-NET", "asname": "EXAMPLE",
        "reverse": "unrelated.example.net", "mobile": False, "proxy": False, "hosting": True,
    },
}


def _geo_url(config: Config, ip: str) -> str:
    base = config.geo.base_url.rstrip("/")
    if config.geo.api_key:
        base = base.replace("http://ip-api.com", "https://pro.ip-api.com")
    url = f"{base}/{ip}?fields={config.geo.fields}"
    if config.geo.api_key:
        url += f"&key={config.geo.api_key}"
    return url


def _to_thread(fn, *args):
    """Run a blocking call in the default executor, shielding cancellation."""
    return asyncio.get_running_loop().run_in_executor(None, fn, *args)


class TokenBucket:
    """Simple async token-bucket rate limiter."""

    def __init__(self, rate: int, per_seconds: float = 60.0):
        self.capacity = max(1, rate)
        self.tokens = float(self.capacity)
        self.refill_rate = self.capacity / per_seconds
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.refill_rate)
            self.updated = now
            if self.tokens < 1.0:
                wait = (1.0 - self.tokens) / self.refill_rate
                await asyncio.sleep(wait)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


class GeoClient:
    """Async ip-api.com client with caching, rate limiting and rDNS fallback."""

    def __init__(self, config: Config, cache: Optional[ResultCache] = None):
        self.config = config
        self.cache = cache or ResultCache(
            ttl_seconds=config.cache.ttl_seconds,
            error_ttl_seconds=config.cache.error_ttl_seconds,
            max_entries=config.cache.max_entries,
        )
        self._bucket = TokenBucket(config.geo.max_requests_per_minute)
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self.config.geo.timeout_seconds),
                        headers={"User-Agent": "origin-analysis/1.0"},
                    )
        return self._client

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    # -- public API -----------------------------------------------------

    async def lookup(self, ip: str) -> Dict[str, Any]:
        """Geolocate a public IP. Returns the full hop-enrichment dict.

        Never raises for network/API errors: the result carries
        ``error`` and ``message`` fields the UI surfaces verbatim.
        """
        cached, fetched_at = self.cache.get_geo(ip)
        if cached is not None:
            cached = dict(cached)
            cached["cached"] = True
            return cached

        error_cached, _ = self.cache.get_error(ip)
        if error_cached is not None:
            # Retry after the short error TTL; if we cannot, reuse the cached
            # error so callers still get the explicit failure message.
            return dict(error_cached)

        if self.config.geo.mock:
            result = self._mock_lookup(ip)
        else:
            result = await self._live_lookup(ip)

        if result.get("error"):
            self.cache.set_error(ip, result)
        else:
            self.cache.set_geo(ip, result)
        return result

    async def lookup_many(self, ips) -> Dict[str, Dict[str, Any]]:
        """Concurrent lookups for a list of public IPs (rate limited)."""
        return {ip: r for ip, r in zip(ips, await asyncio.gather(*(self.lookup(ip) for ip in ips)))}

    # -- internals ------------------------------------------------------

    def _mock_lookup(self, ip: str) -> Dict[str, Any]:
        data = MOCK_GEO.get(ip)
        if data is None:
            return {
                "ip": ip, "error": "lookup_failed",
                "message": "Geolocation mock has no entry for this IP",
            }
        return self._normalize(ip, data)

    async def _live_lookup(self, ip: str) -> Dict[str, Any]:
        client = await self._ensure_client()
        url = _geo_url(self.config, ip)
        try:
            await self._bucket.acquire()
            response = await client.get(url)
        except asyncio.TimeoutError:
            msg = f"Geolocation timed out for IP {redact_ip(ip)}; other fields may be available"
            logger.warning(msg)
            return {"ip": ip, "error": "timeout", "message": msg}
        except httpx.HTTPError as exc:
            msg = f"Geolocation request failed for IP {redact_ip(ip)}: {type(exc).__name__}"
            logger.warning(msg)
            return {"ip": ip, "error": "request_failed", "message": msg}

        try:
            data = response.json()
        except ValueError:
            return {
                "ip": ip, "error": "bad_response",
                "message": "Geolocation service returned an unparseable response",
            }

        if not isinstance(data, dict) or data.get("status") != "success":
            upstream = (data.get("message") if isinstance(data, dict) else None) or "unknown upstream error"
            return {
                "ip": ip, "error": "upstream_error",
                "message": f"Geolocation service error: {upstream}",
            }
        return self._normalize(ip, data)

    def _normalize(self, ip: str, data: Dict[str, Any]) -> Dict[str, Any]:
        reverse = normalize_hostname(data.get("reverse"))
        # `reverse` is requested from the API; when unsupported/absent, fall
        # back to a native PTR lookup (blocking -> run in a thread).
        asn = normalize_asn(data.get("as"))
        return {
            "ip": ip,
            "lat": data.get("lat"),
            "lon": data.get("lon"),
            "city": data.get("city"),
            "region": data.get("regionName") or data.get("region"),
            "country": data.get("country"),
            "country_code": data.get("countryCode"),
            "isp": data.get("isp"),
            "org": data.get("org"),
            "asn": asn,
            "asname": data.get("asname"),
            "reverse": reverse,
            "reverse_fallback": reverse is None and bool(data.get("reverse")),
            "mobile": bool(data.get("mobile")),
            "proxy": bool(data.get("proxy")),
            "hosting": bool(data.get("hosting")),
            "error": None,
            "message": None,
        }

    async def ensure_reverse(self, ip: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a missing `reverse` via cached / native PTR lookup.

        Called by the service after geolocation when the API did not return an
        rDNS name (ip-api's free tier ignores the `reverse` field on plain
        HTTP, so this path is the common one).
        """
        if result.get("reverse"):
            return result
        cached, _ = self.cache.get_rdns(ip)
        if cached is not None:
            result["reverse"] = cached["reverse"]
            result["reverse_source"] = "cache"
            return result
        name = await _to_thread(ptr_lookup, ip, self.config.geo.ptr_timeout_seconds)
        self.cache.set_rdns(ip, {"reverse": name})
        result["reverse"] = name
        result["reverse_source"] = "ptr"
        return result

    async def lookup_rdns(self, ip: str) -> Dict[str, Any]:
        """Standalone rDNS lookup used by the header-hostname mismatch check."""
        cached, fetched_at = self.cache.get_rdns(ip)
        if cached is not None:
            out = dict(cached)
            out["cached"] = True
            return out
        name = await _to_thread(ptr_lookup, ip, self.config.geo.ptr_timeout_seconds)
        result = {"reverse": name}
        self.cache.set_rdns(ip, result)
        return result
