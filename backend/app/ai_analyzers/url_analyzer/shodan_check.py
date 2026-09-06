# shodan_check.py
#
# Shodan -- looks up what services/ports are exposed on the hosting
# IP, and any known vulnerabilities associated with it. Free API key.
# Bulletproof/throwaway phishing hosts often show unusual open-port
# fingerprints compared to legitimate hosting. Docs: https://developer.shodan.io/
#
# NOTE on "Access denied" with a correct key: Shodan's REST Host Lookup
# endpoint (/shodan/host/{ip}, used below) requires query credits on the
# account, which the plain free signup key often does NOT include --
# this is a plan/credits limitation, not a wrong or malformed key. If
# that happens, this falls back to Shodan's InternetDB
# (internetdb.shodan.io), a separate, genuinely free, no-key-required
# endpoint that covers the same open-ports/hostnames/vulns data (just
# without org/tags detail) -- https://internetdb.shodan.io/

import requests

try:
    from . import config
except ImportError:
    import config

API_URL = "https://api.shodan.io/shodan/host/{ip}"
INTERNETDB_URL = "https://internetdb.shodan.io/{ip}"


def _check_internetdb(ip_address: str, note: str) -> dict:
    try:
        response = requests.get(
            INTERNETDB_URL.format(ip=ip_address),
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return {"source": "shodan", "ip_address": ip_address, "no_data": True, "note": note}

        response.raise_for_status()
        data = response.json()

        return {
            "source": "shodan",
            "ip_address": ip_address,
            "open_ports": data.get("ports", []),
            "hostnames": data.get("hostnames", []),
            "vulnerabilities": list(data.get("vulns", [])),
            "tags": data.get("tags", []),
            "note": note,
        }
    except requests.exceptions.RequestException as error:
        return {"source": "shodan", "error": f"{note} InternetDB fallback also failed: {error}"}


def check_ip(ip_address: str) -> dict:
    skip = config.require_key(
        config.SHODAN_API_KEY,
        "shodan",
        "https://account.shodan.io/",
    )
    if skip:
        return skip

    if not ip_address or ip_address == "Could not resolve IP address":
        return {"source": "shodan", "error": "No valid IP address to check"}

    try:
        response = requests.get(
            API_URL.format(ip=ip_address),
            params={"key": config.SHODAN_API_KEY},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {"source": "shodan", "ip_address": ip_address, "no_data": True}

        # A valid key can still get 401/403 here -- Host Lookup needs query
        # credits the free tier often doesn't have. Fall back to the free,
        # unauthenticated InternetDB endpoint instead of just erroring.
        if response.status_code in (401, 403):
            return _check_internetdb(
                ip_address,
                note=(
                    "Full Shodan API returned access denied for this key (likely a free-tier "
                    "credits limit, not an invalid key) -- showing InternetDB data instead, "
                    "which has open ports/hostnames/vulns but not org or paid-tier detail."
                ),
            )

        response.raise_for_status()
        data = response.json()

        return {
            "source": "shodan",
            "ip_address": ip_address,
            "open_ports": data.get("ports", []),
            "organization": data.get("org"),
            "hostnames": data.get("hostnames", []),
            "vulnerabilities": list(data.get("vulns", [])),
            "tags": data.get("tags", []),
        }

    except requests.exceptions.RequestException as error:
        return {"source": "shodan", "error": str(error)}
