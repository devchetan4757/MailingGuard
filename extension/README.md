# MailingGuard — Phase 2.1

This directory contains the Manifest V3 extension foundation only. It provides a persistent protection toggle, notification preference, alert-threshold setting, a small service-worker lifecycle foundation, and reusable notification plumbing for future phases.

## Load in Chrome or Edge

1. Open `chrome://extensions` in Chrome or `edge://extensions` in Edge.
2. Turn on **Developer mode**.
3. Choose **Load unpacked**.
4. Select this `extension/` directory.
5. Click the MailingGuard toolbar icon to open the popup. Use **Open Settings** in the popup (or the extension's **Details → Extension options**) for the settings page.

To test a changed unpacked extension, use the extension page's reload button, then reopen the popup. Settings are stored in `chrome.storage.local` and are not reset by that reload.

## Current permissions

- `storage` — persists the three foundation settings.
- `notifications` — reserves browser notification infrastructure for future suspicious-email alerts.
- `alarms` — schedules a low-frequency foundation heartbeat; it does not synchronize Gmail.

## Deliberately not implemented

Phase 2.1 does **not** include Gmail authentication, Gmail API or History API access, mailbox monitoring, Gmail synchronization, email bodies or attachments, triage, scoring, parsing, deep analysis, SPF/DKIM/DMARC display, or external AI/LLM services. The backend remains the authoritative scoring system; this extension has no duplicate scoring engine.

The service worker contains an internal `TEST_NOTIFICATION` message path for infrastructure verification only. It is not connected to Gmail and browser notifications intentionally remain concise; authentication details are not shown there. Notification buttons are wired only as future action placeholders.
