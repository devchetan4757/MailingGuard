# openphish.py
#
# OpenPhish free "community feed" -- a plain-text list of currently
# active phishing URLs, refreshed by OpenPhish every few hours.
# No API key. We cache the list in-memory for CACHE_TTL_SECONDS so
# repeated lookups don't re-download it every time.
# Docs: https://openphish.com/phish_feed.html

import time
import requests

try:
    from . import config
except ImportError:
    import config

FEED_URL = "https://openphish.com/feed.txt"
CACHE_TTL_SECONDS = 3600  # OpenPhish refreshes this feed every few hours anyway

_cache = {"urls": None, "fetched_at": 0}


def _get_feed():
    now = time.time()

    if _cache["urls"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["urls"]

    response = requests.get(
        FEED_URL,
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    urls = set(line.strip() for line in response.text.splitlines() if line.strip())
    _cache["urls"] = urls
    _cache["fetched_at"] = now

    return urls


def check_url(url: str) -> dict:
    try:
        feed = _get_feed()
        normalized = url.strip().rstrip("/")

        listed = any(
            normalized == entry.rstrip("/") or normalized in entry
            for entry in feed
        )

        return {
            "source": "openphish",
            "listed": listed,
            "feed_size": len(feed),
        }

    except requests.exceptions.RequestException as error:
        return {"source": "openphish", "error": str(error)}
