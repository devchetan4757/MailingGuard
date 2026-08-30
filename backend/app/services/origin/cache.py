"""Small in-process, IP-keyed TTL cache for geolocation, rDNS and DNSBL results.

Used when the host application has no shared cache; the interface mirrors a
minimal get/set API so it can be swapped for Redis/memcached later. Per-IP
entries record the lookup timestamp so the UI can display it and consumers can
see how stale a value is.

Negative results ("not listed", "no rDNS") are cached too, with their own
shorter TTL for lookup errors.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class TtlCache:
    """Thread-safe in-memory cache with per-key TTL and max size."""

    def __init__(self, ttl_seconds: int, max_entries: int = 10000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, now: Optional[float] = None):
        """Return ``(value, fetched_at_epoch)`` or ``(None, None)``."""
        now = time.time() if now is None else now
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None, None
            fetched_at, value = entry
            if now - fetched_at >= self.ttl_seconds:
                self._entries.pop(key, None)
                return None, None
            return value, fetched_at

    def set(self, key: str, value: Any, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            if len(self._entries) >= self.max_entries and key not in self._entries:
                # Evict the oldest entry (simple FIFO by insertion time).
                oldest = min(self._entries, key=lambda k: self._entries[k][0])
                self._entries.pop(oldest, None)
            self._entries[key] = (now, value)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class ResultCache:
    """Cache facade for Origin Analysis lookups.

    Holds three namespaces -- geo, rdns, dnsbl -- each keyed by IP, plus a
    separate small TTL store for lookup *errors* (cached briefly so a flaky
    upstream is not hammered).

    Every stored value is a dict; a ``_cached_at`` epoch timestamp is injected
    and returned to callers via ``CachedResult``.
    """

    def __init__(self, ttl_seconds: int = 86400, error_ttl_seconds: int = 300,
                 max_entries: int = 10000):
        self.ttl_seconds = ttl_seconds
        self._geo = TtlCache(ttl_seconds, max_entries)
        self._rdns = TtlCache(ttl_seconds, max_entries)
        self._dnsbl = TtlCache(ttl_seconds, max_entries)
        self._errors = TtlCache(error_ttl_seconds, max_entries)

    def get_geo(self, ip: str, now: Optional[float] = None):
        return self._geo.get(ip, now)

    def set_geo(self, ip: str, value: dict, now: Optional[float] = None):
        self._geo.set(ip, value, now)

    def get_rdns(self, ip: str, now: Optional[float] = None):
        return self._rdns.get(ip, now)

    def set_rdns(self, ip: str, value: dict, now: Optional[float] = None):
        self._rdns.set(ip, value, now)

    def get_dnsbl(self, ip: str, now: Optional[float] = None):
        return self._dnsbl.get(ip, now)

    def set_dnsbl(self, ip: str, value: dict, now: Optional[float] = None):
        self._dnsbl.set(ip, value, now)

    def get_error(self, ip: str, now: Optional[float] = None):
        return self._errors.get(ip, now)

    def set_error(self, ip: str, value: dict, now: Optional[float] = None):
        self._errors.set(ip, value, now)

    def stats(self) -> dict:
        return {
            "geo": len(self._geo),
            "rdns": len(self._rdns),
            "dnsbl": len(self._dnsbl),
            "errors": len(self._errors),
        }


def iso_timestamp(epoch: Optional[float]) -> Optional[str]:
    """Format a cache timestamp for the JSON contract (ISO 8601 UTC)."""
    if epoch is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))
