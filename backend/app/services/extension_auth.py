"""Authentication service for the MV3 extension.

This module deliberately does not read the web app's gmail_token.json and never
persists a Google access or refresh token. Google verification is performed on
each extension sign-in; the returned MailingGuard credential is a short-lived,
signed application session.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"


class ExtensionAuthError(Exception):
    """An expected authentication failure suitable for a 401/502 response."""


@dataclass(frozen=True)
class ExtensionAuthConfig:
    session_secret: str
    session_ttl_seconds: int = 900
    google_client_id: str | None = None

    @classmethod
    def from_environment(cls) -> "ExtensionAuthConfig":
        secret = os.environ.get("MAILINGGUARD_EXTENSION_SESSION_SECRET", "")
        if len(secret) < 32:
            raise RuntimeError("MAILINGGUARD_EXTENSION_SESSION_SECRET must be at least 32 characters")
        ttl = int(os.environ.get("MAILINGGUARD_EXTENSION_SESSION_TTL_SECONDS", "900"))
        if not 60 <= ttl <= 3600:
            raise RuntimeError("MAILINGGUARD_EXTENSION_SESSION_TTL_SECONDS must be between 60 and 3600")
        google_client_id = os.environ.get("MAILINGGUARD_GOOGLE_EXTENSION_CLIENT_ID", "").strip()
        if not google_client_id:
            raise RuntimeError("MAILINGGUARD_GOOGLE_EXTENSION_CLIENT_ID is required")
        return cls(secret, ttl, google_client_id)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class ExtensionAuthService:
    def __init__(self, config: ExtensionAuthConfig, opener: Callable[..., Any] | None = None):
        self.config = config
        self._open = opener or urllib.request.urlopen

    def _google_json(self, url: str, *, token: str | None = None, query: dict[str, str] | None = None) -> dict[str, Any]:
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
        try:
            with self._open(request, timeout=8) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ExtensionAuthError("Google verification is unavailable") from exc
        if status < 200 or status >= 300:
            raise ExtensionAuthError("Google rejected the access token")
        if not isinstance(body, dict):
            raise ExtensionAuthError("Google returned an invalid verification response")
        return body

    def verify_google_access_token(self, access_token: str) -> str:
        if not isinstance(access_token, str) or not access_token.strip() or len(access_token) > 4096:
            raise ExtensionAuthError("A Google access token is required")
        info = self._google_json(TOKENINFO_URL, query={"access_token": access_token})
        if not self.config.google_client_id or info.get("audience") != self.config.google_client_id:
            raise ExtensionAuthError("Google token audience is not this extension")
        scopes = set(str(info.get("scope", "")).split())
        if GMAIL_READONLY_SCOPE not in scopes:
            raise ExtensionAuthError("The token does not grant Gmail read-only access")
        try:
            if int(info.get("expires_in", 0)) <= 0:
                raise ExtensionAuthError("Google access token is expired")
        except (TypeError, ValueError) as exc:
            raise ExtensionAuthError("Google returned an invalid token expiry") from exc
        profile = self._google_json(PROFILE_URL, token=access_token)
        email = profile.get("emailAddress")
        if not isinstance(email, str) or "@" not in email or len(email) > 320:
            raise ExtensionAuthError("Google did not return a valid Gmail identity")
        return email.lower()

    def _issue_session(self, email: str, now: int | None = None) -> tuple[str, int]:
        issued = int(time.time() if now is None else now)
        expires = issued + self.config.session_ttl_seconds
        payload = {"sub": email, "iat": issued, "exp": expires, "purpose": "mailingguard-extension"}
        encoded = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = _b64(hmac.new(self.config.session_secret.encode(), encoded.encode(), hashlib.sha256).digest())
        return f"mgext.v1.{encoded}.{signature}", expires

    def authenticate(self, access_token: str) -> dict[str, Any]:
        email = self.verify_google_access_token(access_token)
        token, expires = self._issue_session(email)
        return {"authenticated": True, "email": email, "sessionToken": token, "expiresAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires))}

    def verify_session(self, token: str, now: int | None = None) -> str:
        try:
            prefix, version, encoded, supplied = token.split(".")
            if prefix != "mgext" or version != "v1" or not encoded or not supplied:
                raise ValueError
            expected = _b64(hmac.new(self.config.session_secret.encode(), encoded.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(expected, supplied):
                raise ValueError
            payload = json.loads(_unb64(encoded))
            current = int(time.time() if now is None else now)
            if payload.get("purpose") != "mailingguard-extension" or current >= int(payload["exp"]):
                raise ValueError
            return str(payload["sub"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ExtensionAuthError("MailingGuard session is invalid or expired") from exc

