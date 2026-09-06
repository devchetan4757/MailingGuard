# urlhaus.py
#
# URLhaus (abuse.ch) -- tracks URLs actively distributing malware
# payloads. abuse.ch now requires a free Auth-Key for all API requests
# (see https://auth.abuse.ch/). Docs: https://urlhaus-api.abuse.ch/

import requests

try:
    from . import config
except ImportError:
    import config

API_URL = "https://urlhaus-api.abuse.ch/v1/url/"


def check_url(url: str) -> dict:
    skip = config.require_key(
        config.URLHAUS_API_KEY,
        "urlhaus",
        "https://auth.abuse.ch/",
    )
    if skip:
        return skip

    try:
        response = requests.post(
            API_URL,
            data={"url": url},
            headers={"Auth-Key": config.URLHAUS_API_KEY, "User-Agent": config.USER_AGENT},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        query_status = data.get("query_status")

        if query_status == "no_results":
            return {"source": "urlhaus", "listed": False}

        if query_status != "ok":
            return {"source": "urlhaus", "listed": False, "note": query_status}

        return {
            "source": "urlhaus",
            "listed": True,
            "threat": data.get("threat"),
            "tags": data.get("tags", []),
            "url_status": data.get("url_status"),
            "date_added": data.get("date_added"),
            "reference": data.get("urlhaus_reference"),
        }

    except requests.exceptions.RequestException as error:
        return {"source": "urlhaus", "error": str(error)}
