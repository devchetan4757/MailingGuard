"""
Gmail message cache.

Keeps recently fetched Gmail data locally so the frontend
doesn't need to hit the Gmail API on every request.

Current setup:
- Single testing Gmail account
- Local JSON cache
- 10 minute TTL
"""

import json
import time
from pathlib import Path
from typing import Any


class GmailCache:
    def __init__(
        self,
        cache_file: str | Path,
        ttl_seconds: int = 600,
    ):
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_seconds

        self.cache_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get(self) -> Any | None:
        """
        Return cached data if it exists and hasn't expired.
        """

        if not self.cache_file.exists():
            return None

        try:
            payload = json.loads(
                self.cache_file.read_text(
                    encoding="utf-8"
                )
            )

            cached_at = payload.get("cached_at")
            data = payload.get("data")

            if cached_at is None or data is None:
                return None

            age = time.time() - float(cached_at)

            if age < 0:
                return None

            if age >= self.ttl_seconds:
                return None

            return data

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None

    def set(self, data: Any) -> None:
        """
        Store data in the cache.
        """

        payload = {
            "cached_at": time.time(),
            "data": data,
        }

        self.cache_file.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def clear(self) -> None:
        """
        Delete cached data.
        """

        try:
            self.cache_file.unlink(
                missing_ok=True
            )
        except OSError:
            pass

    def is_valid(self) -> bool:
        """
        Check whether usable cached data exists.
        """

        return self.get() is not None

    def age_seconds(self) -> float | None:
        """
        Return cache age in seconds.
        """

        if not self.cache_file.exists():
            return None

        try:
            payload = json.loads(
                self.cache_file.read_text(
                    encoding="utf-8"
                )
            )

            cached_at = payload.get(
                "cached_at"
            )

            if cached_at is None:
                return None

            age = time.time() - float(
                cached_at
            )

            return max(0.0, age)

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None
