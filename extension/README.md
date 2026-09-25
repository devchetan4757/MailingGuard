# MailingGuard â€” Phase 2.2

This directory contains the Manifest V3 extension foundation plus explicit Gmail authentication. A user clicks **Connect Gmail**, Chrome Identity requests only Gmail read-only access, the extension identifies the account through Gmail, and the backend verifies the Google access token before issuing a short-lived MailingGuard session.

## Required deployment setup

1. Create a Google OAuth **Chrome Extension** client for the extension's ID.
2. Replace the placeholder `oauth2.client_id` in `manifest.json` with that client ID. The only declared Google scope is `https://www.googleapis.com/auth/gmail.readonly`.
3. Configure the extension's backend URL in `shared/constants.js` (the checked-in development default is `http://localhost:8000`).
4. Configure the backend with `MAILINGGUARD_EXTENSION_SESSION_SECRET` (at least 32 random characters). Optionally set `MAILINGGUARD_GOOGLE_EXTENSION_CLIENT_ID` to verify the token audience and `MAILINGGUARD_EXTENSION_SESSION_TTL_SECONDS` to a value from 60â€“3600 (default 900).
5. Register `backend/app/api/extension.py`'s `register_extension_routes()` with the existing API router. The host application supplies its normal CORS/auth middleware and error handling.

The OAuth client ID is configuration, not a client secret. No client secret belongs in the extension.

## Load in Chrome, Edge, or Chromium

1. Open `chrome://extensions` (or `edge://extensions` / `brave://extensions`).
2. Turn on **Developer mode**.
3. Choose **Load unpacked** and select this `extension/` directory.
4. Click the MailingGuard toolbar icon, then **Connect Gmail**.
5. After authorization, the verified account is shown in the popup and Settings. Use **Disconnect Gmail** to clear the MailingGuard session and the cached Google access token when available.

## Current permissions

- `storage` â€” persists protection settings and the minimum MailingGuard session state.
- `notifications` â€” reserves browser notification infrastructure.
- `alarms` â€” foundation heartbeat only.
- `identity` â€” obtains a user-authorized Google OAuth access token.

The OAuth declaration requests only `https://www.googleapis.com/auth/gmail.readonly`. No Gmail token is written to extension storage; it is held only in service-worker memory long enough to identify the account and obtain the MailingGuard session. The backend verifies the token with Google's token-info endpoint and Gmail profile endpoint, then returns a signed, short-lived MailingGuard session. It does not store Google access or refresh tokens.

## Deliberately not implemented

Phase 2.2 does **not** include mailbox synchronization, Gmail History API, message bodies, attachments, triage, parsing, scoring, deep analysis, webpage scraping, or external AI/LLM services. Phase 2.3 will use the authenticated session for monitoring. The existing web Gmail integration and its `gmail_token.json` are not used by this extension authentication service.
