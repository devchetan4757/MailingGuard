# safe_browsing.py
#
# Google Safe Browsing v4 -- checks a URL against Google's live
# malware/phishing/unwanted-software blocklists. Free API key required.
# Docs: https://developers.google.com/safe-browsing/v4/lookup-api

import requests

try:
    from . import config
except ImportError:
    import config

API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


def check_url(url: str) -> dict:
    skip = config.require_key(
        config.GOOGLE_SAFE_BROWSING_API_KEY,
        "google_safe_browsing",
        "https://console.cloud.google.com/apis/library/safebrowsing.googleapis.com",
    )
    if skip:
        return skip

    body = {
        "client": {"clientId": "mailguard-url-analyzer", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }

    try:
        response = requests.post(
            API_URL,
            params={"key": config.GOOGLE_SAFE_BROWSING_API_KEY},
            json=body,
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        matches = data.get("matches", [])

        return {
            "source": "google_safe_browsing",
            "malicious": len(matches) > 0,
            "threat_types": [m.get("threatType") for m in matches],
            "raw_matches": matches,
        }

    except requests.exceptions.RequestException as error:
        return {"source": "google_safe_browsing", "error": str(error)}
