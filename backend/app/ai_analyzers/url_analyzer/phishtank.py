# phishtank.py
#
# PhishTank (operated by Cisco Talos) -- community-verified phishing
# URL database. Works without an API key at a lower rate limit; set
# PHISHTANK_API_KEY for a higher one. Docs: https://www.phishtank.com/api_info.php

import requests

try:
    from . import config
except ImportError:
    import config

API_URL = "https://checkurl.phishtank.com/checkurl/"


def check_url(url: str) -> dict:
    payload = {"url": url, "format": "json"}
    if config.PHISHTANK_API_KEY:
        payload["app_key"] = config.PHISHTANK_API_KEY

    try:
        response = requests.post(
            API_URL,
            data=payload,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", {})

        return {
            "source": "phishtank",
            "in_database": bool(results.get("in_database")),
            "verified": bool(results.get("verified")),
            "phish_id": results.get("phish_id"),
            "detail_url": results.get("phish_detail_page"),
        }

    except requests.exceptions.RequestException as error:
        return {"source": "phishtank", "error": str(error)}
    except ValueError:
        # PhishTank returns non-JSON when rate-limited without a key
        return {"source": "phishtank", "error": "Rate limited or invalid response (consider adding PHISHTANK_API_KEY)"}
