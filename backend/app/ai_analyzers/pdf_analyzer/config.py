# config.py
#
# pdf_analyzer is run in an isolated subprocess (see dispatcher.py:
# _run_isolated -> analyzer_cli.py), so it stays a self-contained
# package rather than importing from url_analyzer/config.py -- same
# reasoning url_analyzer itself uses for having its own config.py
# instead of a shared one.
#
# API keys are read from environment variables only. Nothing is
# hardcoded, so this file is safe to commit. If a key is missing,
# the relevant check returns {"error": "..."} instead of crashing --
# the rest of analyze_pdf() still runs.
#
#   VIRUSTOTAL_API_KEY  -> https://www.virustotal.com/gui/my-apikey
#                          (same key you already use for url_analyzer's
#                          URL lookups -- VT file and URL endpoints
#                          share one API key/quota)

import os

VIRUSTOTAL_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")

HTTP_TIMEOUT_SECONDS = 10


def require_key(key_value, source_name, signup_url):
    """Return a standard 'skipped, no key' dict, or None if the key is present."""
    if not key_value:
        return {
            "source": source_name,
            "error": f"Skipped: no API key set. Get one free at {signup_url}",
        }
    return None
