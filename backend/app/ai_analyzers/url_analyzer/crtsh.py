# crtsh.py
#
# crt.sh -- searches public Certificate Transparency logs. Every TLS
# cert issued for a domain shows up here, usually within minutes of
# issuance. Useful for spotting freshly-minted lookalike domains
# before they've made it onto any blocklist. No API key needed.

import requests

try:
    from . import config
except ImportError:
    import config

API_URL = "https://crt.sh/"


def check_domain(domain: str) -> dict:
    try:
        response = requests.get(
            API_URL,
            params={"q": domain, "output": "json"},
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        # crt.sh returns an empty body (not valid JSON) when there are no matches
        entries = response.json() if response.text.strip() else []

        issuers = sorted(set(e.get("issuer_name", "") for e in entries))
        earliest = min((e.get("entry_timestamp", "") for e in entries), default=None)

        return {
            "source": "crt_sh",
            "certificate_count": len(entries),
            "issuers": issuers,
            "earliest_entry": earliest,
        }

    except requests.exceptions.RequestException as error:
        return {"source": "crt_sh", "error": str(error)}
    except ValueError:
        return {"source": "crt_sh", "certificate_count": 0, "issuers": [], "earliest_entry": None}
