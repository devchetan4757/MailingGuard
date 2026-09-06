# abuseipdb.py
#
# AbuseIPDB -- checks whether the IP hosting a domain has been
# reported for abuse (spam, brute-force, C2 traffic, etc). Free API
# key. Docs: https://docs.abuseipdb.com/

import requests

try:
    from . import config
except ImportError:
    import config

API_URL = "https://api.abuseipdb.com/api/v2/check"


def check_ip(ip_address: str) -> dict:
    skip = config.require_key(
        config.ABUSEIPDB_API_KEY,
        "abuseipdb",
        "https://www.abuseipdb.com/account/api",
    )
    if skip:
        return skip

    if not ip_address or ip_address == "Could not resolve IP address":
        return {"source": "abuseipdb", "error": "No valid IP address to check"}

    try:
        response = requests.get(
            API_URL,
            params={"ipAddress": ip_address, "maxAgeInDays": 90},
            headers={"Key": config.ABUSEIPDB_API_KEY, "Accept": "application/json"},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json().get("data", {})

        return {
            "source": "abuseipdb",
            "ip_address": ip_address,
            "abuse_confidence_score": data.get("abuseConfidenceScore"),
            "total_reports": data.get("totalReports"),
            "isp": data.get("isp"),
            "country_code": data.get("countryCode"),
            "is_tor": data.get("isTor"),
        }

    except requests.exceptions.RequestException as error:
        return {"source": "abuseipdb", "error": str(error)}
