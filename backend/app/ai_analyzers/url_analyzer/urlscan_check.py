# urlscan_check.py
#
# urlscan.io -- loads the URL in an instrumented sandbox browser and
# reports a verdict plus every domain/IP/file it contacted. This is
# the closest thing here to "what would actually happen if a person
# clicked this link." Submission AND result retrieval both require an
# API key as of urlscan.io's May-2026 auth changes.
# Docs: https://urlscan.io/docs/api/

import time
import requests

try:
    from . import config
except ImportError:
    import config

SUBMIT_URL = "https://urlscan.io/api/v1/scan/"
RESULT_URL = "https://urlscan.io/api/v1/result/{uuid}/"

POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 25  # urlscan scans typically finish in 10-20s


def check_url(url: str) -> dict:
    skip = config.require_key(
        config.URLSCAN_API_KEY,
        "urlscan",
        "https://urlscan.io/user/profile/",
    )
    if skip:
        return skip

    headers = {"API-Key": config.URLSCAN_API_KEY, "Content-Type": "application/json"}

    try:
        submit_response = requests.post(
            SUBMIT_URL,
            headers=headers,
            json={"url": url, "visibility": "unlisted"},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        submit_response.raise_for_status()
        scan_uuid = submit_response.json().get("uuid")

        if not scan_uuid:
            return {"source": "urlscan", "error": "Submission did not return a scan UUID"}

    except requests.exceptions.RequestException as error:
        return {"source": "urlscan", "error": f"Submission failed: {error}"}

    # Poll for the result -- scans run asynchronously
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)

        try:
            result_response = requests.get(
                RESULT_URL.format(uuid=scan_uuid),
                headers=headers,
                timeout=config.HTTP_TIMEOUT_SECONDS,
            )
        except requests.exceptions.RequestException:
            continue

        if result_response.status_code == 404:
            continue  # not ready yet

        if result_response.status_code == 200:
            data = result_response.json()
            verdicts = data.get("verdicts", {}).get("overall", {})
            page = data.get("page", {})

            return {
                "source": "urlscan",
                "malicious": bool(verdicts.get("malicious")),
                "score": verdicts.get("score"),
                "categories": verdicts.get("categories", []),
                "final_url": page.get("url"),
                "ip": page.get("ip"),
                "country": page.get("country"),
                "screenshot": data.get("task", {}).get("screenshotURL"),
                "report_url": f"https://urlscan.io/result/{scan_uuid}/",
            }

    return {
        "source": "urlscan",
        "error": f"Scan did not finish within {MAX_WAIT_SECONDS}s",
        "report_url": f"https://urlscan.io/result/{scan_uuid}/",
    }
