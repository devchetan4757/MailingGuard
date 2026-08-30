"""
Gmail integration.

Current scope:
- Single testing Gmail account
- Google OAuth with PKCE
- Persistent OAuth credentials
- Read-only Gmail access
- 10-minute local message cache
- Basic mailbox/dashboard statistics
- Manual sync

Deep email/security analysis is intentionally NOT handled here.
"""

import base64
import json
import logging
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.services.gmail_cache import GmailCache
from app.services.parsing import parse_eml
from app.api.analyze import run_analysis


router = APIRouter(
    prefix="/integrations/gmail"
)

logger = logging.getLogger("mailguard.gmail")


# ============================================================
# Gmail OAuth
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",

    # Read-only access to the account's basic Google profile
    # (name + avatar photo) so the sidebar/profile strip can
    # show the real Gmail profile picture instead of a
    # generic icon. Does not grant access to mail content.
    "https://www.googleapis.com/auth/userinfo.profile",
]


# ============================================================
# Local storage
# ============================================================

# gmail.py:
# app/api/integrations/gmail.py
#
# parents[0] = integrations
# parents[1] = api
# parents[2] = app
# parents[3] = backend

BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"

TOKEN_FILE = DATA_DIR / "gmail_token.json"
CACHE_FILE = DATA_DIR / "gmail_cache.json"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Gmail cache
# ============================================================

gmail_cache = GmailCache(
    cache_file=CACHE_FILE,
    ttl_seconds=settings.GMAIL_CACHE_TTL_SECONDS,
)


# ============================================================
# Temporary OAuth state / PKCE storage
# ============================================================

# state -> code_verifier
#
# This is only needed while an OAuth login is in progress.
#
# For the current single-account testing setup, in-memory
# storage is sufficient.

oauth_sessions: dict[str, str] = {}


# ============================================================
# Google OAuth client configuration
# ============================================================

def get_client_config():
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,

            "client_secret": settings.GOOGLE_CLIENT_SECRET,

            "auth_uri": (
                "https://accounts.google.com/o/oauth2/auth"
            ),

            "token_uri": (
                "https://oauth2.googleapis.com/token"
            ),

            "redirect_uris": [
                settings.GOOGLE_REDIRECT_URI
            ],
        }
    }


# ============================================================
# Credential helpers
# ============================================================

def save_credentials(credentials: Credentials):
    """
    Persist Gmail OAuth credentials locally.

    IMPORTANT:
    gmail_token.json must never be committed to Git.
    """

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )


def load_credentials():
    """
    Load saved Gmail credentials.

    If the access token has expired, automatically refresh it
    using the refresh token.
    """

    if not TOKEN_FILE.exists():
        return None

    try:
        credentials = (
            Credentials.from_authorized_user_file(
                str(TOKEN_FILE),
                SCOPES,
            )
        )

        # ----------------------------------------------------
        # Refresh expired access token
        # ----------------------------------------------------

        if (
            credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(
                Request()
            )

            save_credentials(
                credentials
            )

        return credentials

    except Exception:
        return None


def get_gmail_service():
    """
    Create an authenticated Gmail API service.
    """

    credentials = load_credentials()

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Gmail is not connected",
        )

    try:
        return build(
            "gmail",
            "v1",
            credentials=credentials,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to initialize Gmail API: {exc}"
            ),
        )


# ============================================================
# Gmail message fetching
# ============================================================

def list_gmail_message_refs(
    service,
    max_results: int = 100,
):
    """
    Fetch just the list of message ids (cheap, one API call).
    """

    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            maxResults=max_results,
        )
        .execute()
    )

    return result.get(
        "messages",
        []
    )


def fetch_message_detail(
    service,
    message_id: str,
):
    """
    Fetch and normalize a single Gmail message's metadata.
    """

    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=[
                "Subject",
                "From",
                "To",
                "Date",
            ],
        )
        .execute()
    )

    # ----------------------------------------------------
    # Convert Gmail headers into a simple dictionary
    # ----------------------------------------------------

    headers = {}

    for header in (
        message
        .get("payload", {})
        .get("headers", [])
    ):
        headers[
            header["name"].lower()
        ] = header["value"]

    # ----------------------------------------------------
    # Normalized message object
    # ----------------------------------------------------

    return {
        "id": message["id"],

        "threadId": message.get(
            "threadId"
        ),

        "subject": headers.get(
            "subject",
            "",
        ),

        "from": headers.get(
            "from",
            "",
        ),

        "to": headers.get(
            "to",
            "",
        ),

        "date": headers.get(
            "date",
            "",
        ),

        "snippet": message.get(
            "snippet",
            "",
        ),

        "labelIds": message.get(
            "labelIds",
            [],
        ),
    }


def fetch_message_raw(
    service,
    message_id: str,
) -> bytes:
    """
    Fetch a single Gmail message as raw RFC 822 bytes (the same shape
    as an uploaded .eml file), so it can be handed straight to the
    shared analysis pipeline in app.api.analyze.
    """

    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="raw",
        )
        .execute()
    )

    raw = message.get("raw")

    if not raw:
        raise HTTPException(
            status_code=502,
            detail="Gmail did not return raw message content.",
        )

    # Gmail returns URL-safe base64 without guaranteed padding.
    padding = "=" * (-len(raw) % 4)

    try:
        return base64.urlsafe_b64decode(raw + padding)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decode Gmail message: {exc}",
        ) from exc


def fetch_gmail_messages(
    service,
    max_results: int = 100,
):
    """
    Fetch recent Gmail messages and normalize their metadata.

    This function talks directly to Gmail.

    It does NOT use the cache.

    The cache layer is handled by the API endpoints.
    """

    message_refs = list_gmail_message_refs(
        service,
        max_results,
    )

    return [
        fetch_message_detail(service, ref["id"])
        for ref in message_refs
    ]


def fetch_gmail_messages_in_chunks(
    service,
    max_results: int = 100,
    batch_size: int = 4,
):
    """
    Same as fetch_gmail_messages, but fetches messages in small
    batches (10-20-30 at a time) and yields (messages_so_far,
    total) after every batch.

    This lets callers (e.g. the streaming dashboard endpoint)
    show/report progress instead of blocking on every one of
    the up-to-100 individual Gmail API calls before anything
    is returned.
    """

    message_refs = list_gmail_message_refs(
        service,
        max_results,
    )

    total = len(message_refs)

    if total == 0:
        yield [], 0
        return

    messages = []

    for start in range(0, total, batch_size):

        batch = message_refs[
            start:start + batch_size
        ]

        for ref in batch:
            messages.append(
                fetch_message_detail(
                    service,
                    ref["id"],
                )
            )

        # Yield a fresh copy so callers can safely hold on to
        # a previous batch's list without it mutating under them.
        yield list(messages), total


# ============================================================
# OAuth — Connect
# ============================================================

@router.get("/connect")
def connect_gmail():
    """
    Start Google OAuth.
    """

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID is not configured",
        )

    if not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_SECRET is not configured",
        )

    flow = Flow.from_client_config(
        get_client_config(),
        scopes=SCOPES,
    )

    flow.redirect_uri = (
        settings.GOOGLE_REDIRECT_URI
    )

    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
    )

    # --------------------------------------------------------
    # Save PKCE verifier.
    #
    # This fixes:
    #
    # InvalidGrantError:
    # Missing code verifier.
    # --------------------------------------------------------

    oauth_sessions[state] = (
        flow.code_verifier
    )

    return {
        "authorization_url": authorization_url,
        "state": state,
    }


# ============================================================
# OAuth — Callback
# ============================================================

@router.get("/callback")
def gmail_callback(
    code: str,
    state: str,
):
    """
    Handle Google's OAuth callback.

    The browser lands here directly (this is the redirect_uri
    Google sends it back to), so on both success and failure we
    redirect it on to the frontend Gmail page — rather than
    leaving it stuck showing this API's raw JSON response —
    with a query param the page can use to show a status
    message.
    """

    frontend_gmail_url = (
        f"{settings.FRONTEND_ORIGIN}/gmail"
    )

    code_verifier = oauth_sessions.get(
        state
    )

    if not code_verifier:
        return RedirectResponse(
            url=(
                f"{frontend_gmail_url}"
                "?gmail_error="
                "OAuth+session+expired+or+invalid.+"
                "Please+try+connecting+again."
            )
        )

    flow = Flow.from_client_config(
        get_client_config(),
        scopes=SCOPES,
        state=state,
    )

    flow.redirect_uri = (
        settings.GOOGLE_REDIRECT_URI
    )

    # --------------------------------------------------------
    # Restore PKCE verifier
    # --------------------------------------------------------

    flow.code_verifier = code_verifier

    try:

        flow.fetch_token(
            code=code
        )

    except Exception as exc:

        return RedirectResponse(
            url=(
                f"{frontend_gmail_url}"
                "?gmail_error="
                f"Gmail+OAuth+token+exchange+failed:+{exc}"
            )
        )

    credentials = flow.credentials

    # --------------------------------------------------------
    # Persist credentials
    # --------------------------------------------------------

    save_credentials(
        credentials
    )

    # OAuth state is no longer needed.
    oauth_sessions.pop(
        state,
        None,
    )

    return RedirectResponse(
        url=f"{frontend_gmail_url}?gmail_connected=1"
    )


# ============================================================
# Connection status
# ============================================================

def get_gmail_profile(service):
    """
    Fetch the connected mailbox's address + basic counts.

    Uses users().getProfile — this is covered by the existing
    gmail.readonly scope, no extra permissions needed.
    """

    profile = (
        service.users()
        .getProfile(userId="me")
        .execute()
    )

    return {
        "email": profile.get("emailAddress"),
        "messagesTotal": profile.get("messagesTotal"),
        "threadsTotal": profile.get("threadsTotal"),
    }


def get_gmail_userinfo(credentials):
    """
    Fetch the connected Google account's display name + avatar
    photo, using the userinfo.profile scope granted alongside
    gmail.readonly.

    Uses the People API (people.googleapis.com) rather than the
    legacy oauth2 v2 userinfo endpoint — the legacy endpoint
    depends on the deprecated Google+ API being enabled on the
    Cloud project, which is often not the case for new projects
    and silently 403s. People API is enabled by default.

    Returns None (rather than raising) if the call fails — e.g.
    an account connected before this scope was added, which
    needs to reconnect once to grant it.
    """

    try:
        people_service = build(
            "people",
            "v1",
            credentials=credentials,
        )

        person = (
            people_service.people()
            .get(
                resourceName="people/me",
                personFields="names,photos",
            )
            .execute()
        )

    except Exception as exc:
        # Most common cause: the People API isn't enabled on the
        # Google Cloud project (separate from granting the OAuth
        # scope — it has its own on/off toggle in Cloud Console
        # under "APIs & Services"). Log it instead of swallowing
        # it so it shows up in the backend console.
        logger.warning(
            "Gmail userinfo/photo lookup failed: %s",
            exc,
        )
        return None

    names = person.get("names") or []
    photos = person.get("photos") or []

    name = names[0].get("displayName") if names else None

    # Prefer a non-default photo (Google marks generic silhouette
    # placeholders with metadata.default = true).
    picture = None

    for photo in photos:
        if not photo.get("metadata", {}).get("primary", True):
            continue
        picture = photo.get("url")
        break

    if not picture and photos:
        picture = photos[0].get("url")

    return {
        "name": name,
        "picture": picture,
    }


@router.get("/status")
def gmail_status():
    """
    Return current Gmail connection status, including the
    connected mailbox address when available.
    """

    credentials = load_credentials()

    if not credentials:
        return {
            "connected": False,
        }

    profile = None

    try:
        service = build(
            "gmail",
            "v1",
            credentials=credentials,
        )

        profile = get_gmail_profile(service)

        userinfo = get_gmail_userinfo(credentials)

        if userinfo:
            profile["name"] = userinfo.get("name")
            profile["picture"] = userinfo.get("picture")

    except Exception:
        # Status should still report "connected" even if the
        # profile lookup itself fails (e.g. transient network
        # issue) — the frontend just won't have an email to show.
        profile = None

    return {
        "connected": True,

        "profile": profile,

        "has_access_token": bool(
            credentials.token
        ),

        "has_refresh_token": bool(
            credentials.refresh_token
        ),

        "scopes": credentials.scopes,

        # True when the connected account was authorized before
        # the userinfo.profile scope existed (or the People API
        # call failed) — the frontend can use this to prompt a
        # one-time reconnect instead of silently showing no photo.
        "needsReconnectForProfile": not bool(
            profile and profile.get("picture")
        ),

        "cache": {
            "available": gmail_cache.is_valid(),

            "ageSeconds": (
                gmail_cache.age_seconds()
            ),
        },
    }


# ============================================================
# Messages
# ============================================================

@router.get("/messages")
def get_gmail_messages(
    max_results: int = 20,
):
    """
    Return recent Gmail messages.

    Uses the shared 10-minute cache whenever possible.
    """

    if max_results < 1:
        max_results = 1

    if max_results > 100:
        max_results = 100

    # --------------------------------------------------------
    # Try cache first
    # --------------------------------------------------------

    cached_messages = gmail_cache.get()

    if cached_messages is not None:

        return {
            "count": min(
                len(cached_messages),
                max_results,
            ),

            "messages": cached_messages[
                :max_results
            ],

            "cached": True,

            "cacheAgeSeconds": (
                gmail_cache.age_seconds()
            ),
        }

    # --------------------------------------------------------
    # Cache unavailable / expired
    # --------------------------------------------------------

    service = get_gmail_service()

    try:

        messages = fetch_gmail_messages(
            service,
            max_results=100,
        )

        # Save fresh data.
        gmail_cache.set(
            messages
        )

        return {
            "count": min(
                len(messages),
                max_results,
            ),

            "messages": messages[
                :max_results
            ],

            "cached": False,

            "cacheAgeSeconds": 0,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch Gmail messages: {exc}"
            ),
        )


# ============================================================
# Read a single loaded Gmail message (full content, not analysis)
# ============================================================

@router.get("/messages/{message_id}")
def get_gmail_message(
    message_id: str,
):
    """
    Fetch a single message's full content for reading — subject,
    sender/recipients, date, body (text/html) and attachment
    metadata. This is a plain "open the email" read, distinct from
    POST /messages/{id}/analyze: nothing is scored, stored as a
    case, or run through the analysis pipeline here.
    """

    service = get_gmail_service()

    try:
        content = fetch_message_raw(
            service,
            message_id,
        )

    except HTTPException:
        raise

    except HttpError as exc:
        status_code = (
            exc.resp.status
            if getattr(exc, "resp", None)
            else 502
        )

        raise HTTPException(
            status_code=404 if status_code == 404 else 502,
            detail=(
                "Gmail message not found."
                if status_code == 404
                else f"Failed to fetch Gmail message: {exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Gmail message: {exc}",
        ) from exc

    parsed = parse_eml(content)

    attachments = [
        {
            "filename": attachment.get("filename") or "attachment",
            "contentType": attachment.get(
                "content_type",
                "application/octet-stream",
            ),
            "size": attachment.get("size", 0),
        }
        for attachment in (parsed.get("attachments") or [])
        if isinstance(attachment, dict)
    ]

    return {
        "id": message_id,
        "subject": parsed.get("subject") or "(no subject)",
        "from": parsed.get("from") or "",
        "to": parsed.get("to") or "",
        "cc": parsed.get("cc") or "",
        "date": parsed.get("date") or "",
        "bodyText": parsed.get("body_text") or "",
        "bodyHtml": parsed.get("body_html") or "",
        "attachments": attachments,
    }


# ============================================================
# Hand a loaded Gmail message over to the analysis pipeline
# ============================================================

@router.post("/messages/{message_id}/analyze")
async def analyze_gmail_message(
    message_id: str,
):
    """
    Fetch a single message's raw content straight from Gmail and run
    it through the exact same pipeline as an uploaded .eml file
    (POST /analyze) — parsing, scoring, origin lookup, similarity and
    case/hash chain — so the result can be opened directly on either
    the AI Deep Analysis page or the Origin Analysis page.
    """

    service = get_gmail_service()

    try:
        content = fetch_message_raw(
            service,
            message_id,
        )

    except HTTPException:
        raise

    except HttpError as exc:
        status_code = (
            exc.resp.status
            if getattr(exc, "resp", None)
            else 502
        )

        raise HTTPException(
            status_code=404 if status_code == 404 else 502,
            detail=(
                "Gmail message not found."
                if status_code == 404
                else f"Failed to fetch Gmail message: {exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Gmail message: {exc}",
        ) from exc

    try:
        return await run_analysis(
            content,
            filename=f"{message_id}.eml",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ============================================================
# Dashboard
# ============================================================

# How many of the loaded messages to hand back for display
# (e.g. a "recent mail" list) alongside the aggregate stats.
RECENT_MESSAGES_LIMIT = 50


def compute_dashboard_stats(messages):
    """
    Turn a list of normalized Gmail messages into the stats/
    activity/topSenders/topDomains/labels payload the dashboard
    widgets consume.

    Pulled out of gmail_dashboard() so it can be reused by the
    streaming endpoint to compute PARTIAL stats after every
    batch of messages, not just once everything has loaded.
    """

    # ========================================================
    # Statistics
    # ========================================================

    now = datetime.now(
        timezone.utc
    )

    today_count = 0

    week_count = 0

    unread_count = 0

    sender_counter = Counter()

    domain_counter = Counter()

    label_counter = Counter()

    activity_counter = Counter()

    # ========================================================
    # Process messages
    # ========================================================

    for message in messages:

        # ----------------------------------------------------
        # Labels
        # ----------------------------------------------------

        for label in message.get(
            "labelIds",
            [],
        ):
            label_counter[label] += 1

        # ----------------------------------------------------
        # Unread
        # ----------------------------------------------------

        if "UNREAD" in message.get(
            "labelIds",
            [],
        ):
            unread_count += 1

        # ----------------------------------------------------
        # Sender
        # ----------------------------------------------------

        sender = message.get(
            "from",
            "",
        )

        if sender:

            sender_counter[
                sender
            ] += 1

            # -----------------------------------------------
            # Extract domain
            # -----------------------------------------------

            if "@" in sender:

                domain = (
                    sender
                    .split("@")[-1]
                    .replace(">", "")
                    .strip()
                )

                domain_counter[
                    domain
                ] += 1

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        message_date = None

        message_date_raw = message.get(
            "date",
            "",
        )

        if message_date_raw:

            try:

                message_date = (
                    parsedate_to_datetime(
                        message_date_raw
                    )
                )

                if (
                    message_date.tzinfo
                    is None
                ):
                    message_date = (
                        message_date.replace(
                            tzinfo=timezone.utc
                        )
                    )

                message_date = (
                    message_date.astimezone(
                        timezone.utc
                    )
                )

            except (
                TypeError,
                ValueError,
                OverflowError,
            ):

                message_date = None

        # ----------------------------------------------------
        # Time-based statistics
        # ----------------------------------------------------

        if message_date:

            # Today
            if (
                message_date.date()
                == now.date()
            ):
                today_count += 1

            # Last 7 days
            age_seconds = (
                now - message_date
            ).total_seconds()

            if (
                0
                <= age_seconds
                <= 7 * 24 * 60 * 60
            ):
                week_count += 1

            # Activity graph
            day_key = (
                message_date.strftime(
                    "%Y-%m-%d"
                )
            )

            activity_counter[
                day_key
            ] += 1

    # ========================================================
    # Format activity
    # ========================================================

    activity = [
        {
            "date": date,
            "count": count,
        }
        for date, count
        in sorted(
            activity_counter.items()
        )
    ]

    # ========================================================
    # Top senders
    # ========================================================

    top_senders = [
        {
            "sender": sender,
            "count": count,
        }
        for sender, count
        in sender_counter.most_common(
            10
        )
    ]

    # ========================================================
    # Top domains
    # ========================================================

    top_domains = [
        {
            "domain": domain,
            "count": count,
        }
        for domain, count
        in domain_counter.most_common(
            10
        )
    ]

    # ========================================================
    # Labels
    # ========================================================

    labels = [
        {
            "label": label,
            "count": count,
        }
        for label, count
        in label_counter.most_common(
            15
        )
    ]

    # ========================================================
    # Final stats payload (no connected/cached/etc — those are
    # request-level fields the endpoints attach themselves)
    # ========================================================

    return {
        "stats": {
            "totalFetched": len(messages),

            "today": today_count,

            "thisWeek": week_count,

            "unread": unread_count,
        },

        "activity": activity,

        "topSenders": top_senders,

        "topDomains": top_domains,

        "labels": labels,
    }


@router.get("/dashboard")
def gmail_dashboard():
    """
    Return overall Gmail statistics in one shot.

    Dashboard data is calculated from the shared cached
    message dataset. If there's no cache yet, this blocks
    until all (up to 100) messages have been fetched — prefer
    GET /dashboard/stream for a first-load / no-cache UI so
    the page isn't stuck waiting.

    No deep security analysis happens here.
    """

    messages = gmail_cache.get()

    cached = messages is not None

    if messages is None:

        service = get_gmail_service()

        try:

            messages = fetch_gmail_messages(
                service,
                max_results=100,
            )

            gmail_cache.set(
                messages
            )

        except HTTPException:
            raise

        except Exception as exc:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to build Gmail dashboard: "
                    f"{exc}"
                ),
            )

    payload = compute_dashboard_stats(messages)

    return {
        "connected": True,
        "cached": cached,
        "cacheAgeSeconds": gmail_cache.age_seconds(),
        "loaded": len(messages),
        "total": len(messages),
        "messages": messages[:RECENT_MESSAGES_LIMIT],
        **payload,
    }


# ============================================================
# Dashboard — streamed / chunked loading
# ============================================================

@router.get("/dashboard/stream")
def gmail_dashboard_stream(
    batch_size: int = 4,
):
    """
    Same data as GET /dashboard, but streamed as Server-Sent
    Events so the frontend can update the overview/graphs live
    as messages come in instead of waiting for the whole first
    load (up to 100 sequential Gmail API calls) to finish.

    If cached data is available, it's sent immediately as a
    single "complete" event, same as before.

    Otherwise messages are fetched in small batches (default
    20 at a time) and a "progress" event — with dashboard stats
    computed from everything fetched SO FAR — is emitted after
    each batch. A final "complete" event is sent once every
    message has loaded and the fresh data has been cached.
    """

    if batch_size < 1:
        batch_size = 1

    if batch_size > 50:
        batch_size = 50

    def sse(event_name, payload):
        return (
            f"event: {event_name}\n"
            f"data: {json.dumps(payload)}\n\n"
        )

    def stream():

        # ----------------------------------------------------
        # Cached data — nothing to stream progressively.
        # ----------------------------------------------------

        cached_messages = gmail_cache.get()

        if cached_messages is not None:

            payload = compute_dashboard_stats(
                cached_messages
            )

            yield sse("complete", {
                "connected": True,
                "cached": True,
                "cacheAgeSeconds": gmail_cache.age_seconds(),
                "loaded": len(cached_messages),
                "total": len(cached_messages),
                "messages": cached_messages[
                    :RECENT_MESSAGES_LIMIT
                ],
                **payload,
            })

            return

        # ----------------------------------------------------
        # No cache — fetch in chunks, reporting progress.
        # ----------------------------------------------------

        try:
            service = get_gmail_service()

        except HTTPException as exc:
            yield sse("error", {"message": exc.detail})
            return

        try:

            final_messages = []

            for messages_so_far, total in (
                fetch_gmail_messages_in_chunks(
                    service,
                    max_results=100,
                    batch_size=batch_size,
                )
            ):
                final_messages = messages_so_far

                payload = compute_dashboard_stats(
                    messages_so_far
                )

                yield sse("progress", {
                    "connected": True,
                    "cached": False,
                    "loaded": len(messages_so_far),
                    "total": total,
                    "messages": messages_so_far[
                        :RECENT_MESSAGES_LIMIT
                    ],
                    **payload,
                })

            # Cache the fully-loaded dataset for next time.
            gmail_cache.set(final_messages)

            payload = compute_dashboard_stats(
                final_messages
            )

            yield sse("complete", {
                "connected": True,
                "cached": False,
                "cacheAgeSeconds": 0,
                "loaded": len(final_messages),
                "total": len(final_messages),
                "messages": final_messages[
                    :RECENT_MESSAGES_LIMIT
                ],
                **payload,
            })

        except Exception as exc:

            yield sse("error", {
                "message": (
                    "Failed to build Gmail dashboard: "
                    f"{exc}"
                ),
            })

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Manual synchronization
# ============================================================

@router.post("/sync")
def sync_gmail():
    """
    Force a fresh Gmail synchronization.

    This bypasses the existing cache and replaces it
    with fresh Gmail data.
    """

    service = get_gmail_service()

    try:

        messages = fetch_gmail_messages(
            service,
            max_results=100,
        )

        # Replace old cache.
        gmail_cache.set(
            messages
        )

        return {
            "status": "synced",

            "count": len(messages),

            "cached": False,

            "cacheAgeSeconds": 0,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Gmail sync failed: {exc}"
            ),
        )


# ============================================================
# Clear cache
# ============================================================

@router.delete("/cache")
def clear_gmail_cache():
    """
    Clear the local Gmail message cache.

    Useful during development/testing.
    """

    gmail_cache.clear()

    return {
        "status": "cleared",
        "message": "Gmail cache cleared",
    }
