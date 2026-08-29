"""
Shared app configuration.

Owner: integrator / backend lead.
Everyone else: import from here (e.g. `from app.core.config import settings`),
don't hardcode values like the CORS origin in your own file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load .env from the backend project root.
# config.py is:
# backend/app/core/config.py
#
# parents[2] = backend/
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_NAME: str = "MailingGuard API"
    VERSION: str = "0.1.0"

    FRONTEND_ORIGIN: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173",
    )

    MAX_UPLOAD_BYTES: int = 2 * 1024 * 1024

    GMAIL_CACHE_TTL_SECONDS: int = int(
        os.getenv(
            "GMAIL_CACHE_TTL_SECONDS",
            "600",
        )
    )

    GOOGLE_CLIENT_ID: str = os.getenv(
        "GOOGLE_CLIENT_ID",
        "",
    )

    GOOGLE_CLIENT_SECRET: str = os.getenv(
        "GOOGLE_CLIENT_SECRET",
        "",
    )

    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/integrations/gmail/callback",
    )

    @property
    def cors_origins(self) -> list[str]:
        extra = os.getenv(
            "EXTRA_CORS_ORIGINS",
            "",
        )

        origins = [
            self.FRONTEND_ORIGIN
        ]

        if extra:
            origins += [
                o.strip()
                for o in extra.split(",")
                if o.strip()
            ]

        return origins

settings = Settings()
