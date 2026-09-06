# config.py
#
# All API keys are read from environment variables. Nothing is
# hardcoded so this is safe to commit. If a key is missing, that
# analyzer's module returns {"error": "..."} instead of crashing --
# the rest of the analyzers still run.
#
# Set these before running (e.g. in a .env loaded by your app, or
# `export GOOGLE_SAFE_BROWSING_API_KEY=...` in your shell):
#
#   GOOGLE_SAFE_BROWSING_API_KEY   -> https://console.cloud.google.com/apis/library/safebrowsing.googleapis.com
#   VIRUSTOTAL_API_KEY             -> https://www.virustotal.com/gui/my-apikey
#   URLSCAN_API_KEY                -> https://urlscan.io/user/profile/ (Settings & API)
#   ABUSEIPDB_API_KEY              -> https://www.abuseipdb.com/account/api
#   SHODAN_API_KEY                 -> https://account.shodan.io/
#   PHISHTANK_API_KEY              -> optional, https://www.phishtank.com/api_register.php
#                                      (works without a key on a lower rate limit)
#   URLHAUS_API_KEY                -> https://auth.abuse.ch/ (abuse.ch now requires
#                                      an Auth-Key for all URLhaus API requests)

import os

GOOGLE_SAFE_BROWSING_API_KEY = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY", "")
VIRUSTOTAL_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
URLSCAN_API_KEY = os.environ.get("URLSCAN_API_KEY", "")
ABUSEIPDB_API_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")
SHODAN_API_KEY = os.environ.get("SHODAN_API_KEY", "")
PHISHTANK_API_KEY = os.environ.get("PHISHTANK_API_KEY", "")
URLHAUS_API_KEY = os.environ.get("URLHAUS_API_KEY", "")

HTTP_TIMEOUT_SECONDS = 10
USER_AGENT = "Mozilla/5.0 (compatible; MailGuardURLAnalyzer/1.0)"


def require_key(key_value, source_name, signup_url):
    """Return a standard 'skipped, no key' dict, or None if the key is present."""
    if not key_value:
        return {
            "source": source_name,
            "error": f"Skipped: no API key set. Get one free at {signup_url}",
        }
    return None
