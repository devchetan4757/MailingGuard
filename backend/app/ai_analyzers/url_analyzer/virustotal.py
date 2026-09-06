# virustotal.py
#
# VirusTotal v3 -- aggregates verdicts from 70+ AV engines and
# blocklists for a URL. Free API key, rate-limited (4 req/min on the
# free tier). If the URL has never been scanned before, we submit it
# then poll briefly for the analysis to finish.
# Docs: https://docs.virustotal.com/reference/url-info

import base64
import time
import requests

try:
    from . import config
except ImportError:
    import config

BASE_URL = "https://www.virustotal.com/api/v3"
POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 15


def _url_id(url: str) -> str:
    # VirusTotal identifies URLs by the base64 (URL-safe, no padding) of the URL itself
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")


def check_url(url: str) -> dict:
    skip = config.require_key(
        config.VIRUSTOTAL_API_KEY,
        "virustotal",
        "https://www.virustotal.com/gui/my-apikey",
    )
    if skip:
        return skip

    headers = {"x-apikey": config.VIRUSTOTAL_API_KEY}

    try:
        report = requests.get(
            f"{BASE_URL}/urls/{_url_id(url)}",
            headers=headers,
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )

        if report.status_code == 404:
            # Never scanned before -- submit it, then poll briefly
            submit = requests.post(
                f"{BASE_URL}/urls",
                headers=headers,
                data={"url": url},
                timeout=config.HTTP_TIMEOUT_SECONDS,
            )
            submit.raise_for_status()
            analysis_id = submit.json()["data"]["id"]

            deadline = time.time() + MAX_WAIT_SECONDS
            while time.time() < deadline:
                time.sleep(POLL_INTERVAL_SECONDS)
                analysis = requests.get(
                    f"{BASE_URL}/analyses/{analysis_id}",
                    headers=headers,
                    timeout=config.HTTP_TIMEOUT_SECONDS,
                )
                analysis.raise_for_status()
                status = analysis.json()["data"]["attributes"]["status"]
                if status == "completed":
                    stats = analysis.json()["data"]["attributes"]["stats"]
                    return _format_stats(stats, url)

            return {"source": "virustotal", "error": f"Analysis not finished within {MAX_WAIT_SECONDS}s"}

        report.raise_for_status()
        stats = report.json()["data"]["attributes"]["last_analysis_stats"]
        return _format_stats(stats, url)

    except requests.exceptions.RequestException as error:
        return {"source": "virustotal", "error": str(error)}


def _format_stats(stats: dict, url: str) -> dict:
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)

    return {
        "source": "virustotal",
        "malicious_count": malicious,
        "suspicious_count": suspicious,
        "harmless_count": stats.get("harmless", 0),
        "flagged": (malicious + suspicious) > 0,
        "report_url": f"https://www.virustotal.com/gui/url/{_url_id(url)}",
    }
