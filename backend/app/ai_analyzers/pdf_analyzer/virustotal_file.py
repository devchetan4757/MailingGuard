# virustotal_file.py
#
# VirusTotal v3 file-hash lookup -- aggregates verdicts from 70+ AV
# engines for a file, keyed by its SHA256. This is a *lookup only*:
# unlike url_analyzer/virustotal.py (which submits unseen URLs for
# scanning), we deliberately do NOT upload the PDF itself if VT has
# never seen it before. Uploading someone's email attachment to a
# third party is a different privacy/consent decision than checking
# a hash against an existing database, so that's left as a possible
# opt-in feature later rather than the default behaviour here.
#
# Docs: https://docs.virustotal.com/reference/file-info

import hashlib

import requests

try:
    from . import config
except ImportError:
    import config

BASE_URL = "https://www.virustotal.com/api/v3"


def sha256_of(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()


def check_file(pdf_bytes: bytes) -> dict:
    """
    Look up a PDF's SHA256 on VirusTotal.

    Returns one of:
      {"source": "virustotal", "error": "..."}                     -- no key / request failed
      {"source": "virustotal", "status": "not_seen_before", ...}   -- 404, hash unknown to VT
      {"source": "virustotal", "status": "seen", "sha256": ...,
       "malicious_count": int, "suspicious_count": int,
       "harmless_count": int, "undetected_count": int,
       "malicious_engines": [str, ...],
       "permalink": "https://www.virustotal.com/gui/file/<hash>"}
    """
    skip = config.require_key(
        config.VIRUSTOTAL_API_KEY,
        "virustotal",
        "https://www.virustotal.com/gui/my-apikey",
    )
    if skip:
        return skip

    file_hash = sha256_of(pdf_bytes)
    headers = {"x-apikey": config.VIRUSTOTAL_API_KEY}

    try:
        response = requests.get(
            f"{BASE_URL}/files/{file_hash}",
            headers=headers,
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "source": "virustotal",
                "sha256": file_hash,
                "status": "not_seen_before",
            }

        response.raise_for_status()

        attributes = response.json().get("data", {}).get("attributes", {})
        stats = attributes.get("last_analysis_stats", {}) or {}
        results = attributes.get("last_analysis_results", {}) or {}

        malicious_engines = [
            engine_name
            for engine_name, verdict in results.items()
            if (verdict or {}).get("category") == "malicious"
        ]

        return {
            "source": "virustotal",
            "sha256": file_hash,
            "status": "seen",
            "malicious_count": stats.get("malicious", 0),
            "suspicious_count": stats.get("suspicious", 0),
            "harmless_count": stats.get("harmless", 0),
            "undetected_count": stats.get("undetected", 0),
            "malicious_engines": malicious_engines,
            "permalink": f"https://www.virustotal.com/gui/file/{file_hash}",
        }

    except requests.RequestException as error:
        return {"source": "virustotal", "error": str(error)}
