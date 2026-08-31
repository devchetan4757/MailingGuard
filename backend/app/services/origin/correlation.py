"""Cross-case correlation index for Origin Analysis.

Counts other cases that reference the same IP or ASN and keeps the most recent
case IDs, so investigators can pivot between related reports.

Contract returned by :meth:`CaseCorrelation.query`:

    {"ip_count": N, "asn_count": M, "recent_case_ids": [...]}

This is an internal module-level index. If the host application already has a
case database, adapters can feed it by calling :meth:`record` per case; the
index persists to a JSON file when ORIGIN_CORRELATION_PERSIST_PATH is set
(e.g. for the demo the app stores it in /tmp). The adapter does NOT touch the
host data model -- documented limitation for the PR.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .config import Config


class CaseCorrelation:
    def __init__(self, config: Config, seed: Optional[dict] = None):
        self._ip_index: Dict[str, Dict[str, int]] = defaultdict(dict)
        self._asn_index: Dict[str, Dict[str, int]] = defaultdict(dict)
        self._lock = threading.Lock()
        self._persist_path = config.correlation.persist_path
        if seed:
            for case_id, ip in seed.get("ip", {}).items():
                self._ip_index[ip][str(case_id)] = int(seed["ip"][case_id])
            for case_id, asn in seed.get("asn", {}).items():
                self._asn_index[asn][str(case_id)] = int(seed["asn"][case_id])
        elif self._persist_path and os.path.exists(self._persist_path):
            self._load()

    # -- recording -----------------------------------------------------

    def record(self, case_id: str, ips: List[str], asns: List[str]) -> None:
        """Record a case's origin IPs/ASNs into the index."""
        with self._lock:
            for ip in ips:
                self._ip_index[ip][str(case_id)] = int(time.time())
            for asn in asns:
                if asn:
                    self._asn_index[asn][str(case_id)] = int(time.time())
        if self._persist_path:
            self._save()

    def _save(self) -> None:
        try:
            with self._lock:
                payload = {
                    "ip": {ip: dict(cases) for ip, cases in self._ip_index.items()},
                    "asn": {a: dict(cases) for a, cases in self._asn_index.items()},
                }
            with open(self._persist_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except OSError:
            pass  # persistence is best-effort

    def _load(self) -> None:
        try:
            with open(self._persist_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            with self._lock:
                for ip, cases in payload.get("ip", {}).items():
                    self._ip_index[ip].update({k: int(v) for k, v in cases.items()})
                for asn, cases in payload.get("asn", {}).items():
                    self._asn_index[asn].update({k: int(v) for k, v in cases.items()})
        except (OSError, ValueError):
            pass

    # -- querying ------------------------------------------------------

    def _cases_for(self, index: Dict[str, Dict[str, int]], keys: List[str],
                   exclude_case: Optional[str]) -> List[Tuple[str, int]]:
        found: Dict[str, int] = {}
        for key in keys:
            for case_id, ts in index.get(key, {}).items():
                if case_id == exclude_case:
                    continue
                found[case_id] = max(found.get(case_id, 0), ts)
        return sorted(found.items(), key=lambda kv: kv[1], reverse=True)

    def query(self, ips: List[str], asns: List[str], exclude_case: Optional[str] = None,
              max_recent: int = 10) -> Dict[str, object]:
        """Count other cases referencing the same IPs or ASNs.

        ``recent_case_ids`` are sorted newest-first and capped at max_recent.
        """
        ip_matches = self._cases_for(self._ip_index, ips, exclude_case)
        asn_matches = self._cases_for(self._asn_index, [a for a in asns if a], exclude_case)
        recent = sorted(set([c for c, _ in ip_matches] + [c for c, _ in asn_matches]))[:0]
        merged = {c: t for c, t in ip_matches}
        for c, t in asn_matches:
            merged[c] = max(merged.get(c, 0), t)
        recent = [c for c, _ in sorted(merged.items(), key=lambda kv: kv[1], reverse=True)[:max_recent]]
        return {
            "ip_count": len(ip_matches),
            "asn_count": len(asn_matches),
            "recent_case_ids": recent,
        }
