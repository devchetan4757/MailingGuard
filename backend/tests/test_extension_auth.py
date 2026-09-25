import json
import time
import calendar
from io import BytesIO

import pytest

from backend.app.services.extension_auth import (
    GMAIL_READONLY_SCOPE,
    ExtensionAuthConfig,
    ExtensionAuthError,
    ExtensionAuthService,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def make_service(responses):
    def opener(request, timeout=8):
        return responses.pop(0)
    return ExtensionAuthService(ExtensionAuthConfig("x" * 48, 900, "extension-client"), opener)


def test_successful_authentication_verifies_scope_and_creates_short_session():
    service = make_service([
        FakeResponse({"audience": "extension-client", "scope": GMAIL_READONLY_SCOPE, "expires_in": "300"}),
        FakeResponse({"emailAddress": "User@example.com"}),
    ])
    result = service.authenticate("google-access-token-fixture")
    assert result["authenticated"] is True
    assert result["email"] == "user@example.com"
    assert result["sessionToken"].startswith("mgext.v1.")
    assert 890 <= (calendar.timegm(time.strptime(result["expiresAt"], "%Y-%m-%dT%H:%M:%SZ")) - time.time()) <= 900
    assert service.verify_session(result["sessionToken"]) == "user@example.com"


def test_invalid_token_and_backend_google_rejection_fail_closed():
    service = make_service([FakeResponse({"error": "invalid_token"}, 400)])
    with pytest.raises(ExtensionAuthError):
        service.authenticate("invalid-token-fixture")


def test_missing_readonly_scope_is_rejected():
    service = make_service([FakeResponse({"audience": "extension-client", "scope": "openid", "expires_in": "300"})])
    with pytest.raises(ExtensionAuthError, match="read-only"):
        service.authenticate("scoped-token-fixture")


def test_expired_google_token_is_rejected():
    service = make_service([FakeResponse({"audience": "extension-client", "scope": GMAIL_READONLY_SCOPE, "expires_in": "0"})])
    with pytest.raises(ExtensionAuthError, match="expired"):
        service.authenticate("expired-token-fixture")


def test_session_expiration_and_tampering_are_rejected():
    service = ExtensionAuthService(ExtensionAuthConfig("y" * 48, 60))
    token, expires = service._issue_session("user@example.com", now=100)
    assert service.verify_session(token, now=159) == "user@example.com"
    with pytest.raises(ExtensionAuthError):
        service.verify_session(token, now=160)
    with pytest.raises(ExtensionAuthError):
        service.verify_session(token[:-1] + ("a" if token[-1] != "a" else "b"), now=100)


def test_client_email_is_not_an_accepted_identity():
    service = make_service([
        FakeResponse({"audience": "extension-client", "scope": GMAIL_READONLY_SCOPE, "expires_in": "300"}),
        FakeResponse({"emailAddress": "verified@example.com"}),
    ])
    result = service.authenticate("token")
    assert result["email"] != "attacker@example.com"
