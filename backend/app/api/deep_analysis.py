"""
POST /api/deep-analysis/*

Backs the "AI Deep Analysis" page on the frontend.

POST /api/analyze already gives the user an overview of an email (headers,
URLs, attachments, origin, ...). This router lets the user pick one
specific item out of that overview -- a link, the sender domain, a PDF
attachment, or an image attachment -- run it through the matching
analyzer in app/ai_analyzers/ (via app/dispatcher.py), and have Groq
(app/groq_summarizer.py) turn the raw result into a short plain-language
explanation the user can read.

Every endpoint returns the same shape:

    {
        "option": "<dispatcher option id>",
        "result": <raw analyzer output, JSON-safe>,
        "explanation": "<Groq's plain-language summary>" | null
    }

`explanation` is null when GROQ_API_KEY isn't configured, or if the Groq
call itself fails -- the raw analyzer result is always returned either
way, so this page keeps working even without Groq wired up.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai_analyzers.url_analyzer.analyzer import analyze_url_stream
from app.ai_analyzers.url_analyzer.crawler import fetch_page_source
from app.core.config import settings
from app.dispatcher import (
    analyze_image_attachment,
    analyze_link,
    analyze_pdf_attachment,
    analyze_sender_domain,
)
from app.groq_summarizer import summarize_analysis
from app.services import store
from app.services.email_parser import extract_attachment_bytes


router = APIRouter(
    prefix="/deep-analysis",
)


# Deep-analysis attachments are only ever held in a short-lived temp file
# for the isolated subprocess call, so a slightly more generous cap than
# the main 2MB .eml limit is fine here.
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB

# A preview is meant to be read, not mirrored -- cap what we ship back so
# one huge page can't blow up the response or the browser tab rendering it.
MAX_PREVIEW_HTML_BYTES = 3 * 1024 * 1024  # 3 MB

ALLOWED_PDF_EXTENSIONS = {".pdf"}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
    ".heic",
}


class LinkRequest(BaseModel):
    url: str


class DomainRequest(BaseModel):
    domain: str


def _explain(option_id: str, result: dict) -> str | None:
    """
    Best-effort Groq explanation. Never blocks the response -- if Groq
    isn't configured or the call fails, the raw analyzer result is still
    returned to the frontend.
    """

    if not settings.GROQ_API_KEY:
        return None

    try:
        return summarize_analysis(option_id, result)

    except Exception as error:
        return f"Explanation unavailable: {error}"


def _validate_url(raw_url: str) -> str:
    raw_url = (raw_url or "").strip()

    if not raw_url:
        raise HTTPException(status_code=400, detail="No URL provided.")

    normalized = raw_url if "://" in raw_url else f"http://{raw_url}"
    parsed = urlparse(normalized)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Only http/https URLs are supported.",
        )

    return normalized


async def _save_upload(file: UploadFile, allowed_extensions: set[str]) -> str:
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{suffix or '?'}'. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            ),
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File exceeds the 10 MB deep-analysis limit.",
        )

    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix="mailguard_deep_",
        delete=False,
    ) as tmp:
        tmp.write(content)
        return tmp.name


@router.post("/link")
async def deep_analyze_link(payload: LinkRequest):
    """UI option: 'Analyze links found in this email'."""

    url = _validate_url(payload.url)
    result = analyze_link(url)

    # Full page HTML is only useful as context for Groq's summary --
    # stripping it here keeps the response small instead of shipping an
    # entire crawled page back down to the frontend.
    result_for_client = {
        key: value
        for key, value in result.items()
        if key != "html"
    }

    return {
        "option": "analyze_link",
        "result": result_for_client,
        "explanation": _explain("analyze_link", result),
    }


@router.post("/domain")
async def deep_analyze_domain(payload: DomainRequest):
    """UI option: 'Check sender domain'."""

    domain = (payload.domain or "").strip()

    if not domain:
        raise HTTPException(status_code=400, detail="No domain provided.")

    result = analyze_sender_domain(domain)

    return {
        "option": "analyze_sender_domain",
        "result": result,
        "explanation": _explain("analyze_sender_domain", result),
    }


def _format_sse(event_type: str, payload: dict) -> str:
    """
    Standard Server-Sent-Events framing. `event:` lets the frontend's
    EventSource listen with addEventListener("source", ...) /
    addEventListener("done", ...) instead of parsing payload shape.
    """
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


def _stream_url_analysis(url: str, option_id: str):
    """
    Wraps analyze_url_stream() for SSE: forwards each ("source", ...)
    event to the client immediately as it's produced, and attaches the
    Groq explanation to the final ("done", ...) event once every
    source has reported in.
    """
    for event_type, payload in analyze_url_stream(url):
        if event_type == "done":
            payload["explanation"] = _explain(option_id, payload.get("sources", {}))
        yield _format_sse(event_type, payload)


@router.get("/link/stream")
async def deep_analyze_link_stream(url: str = Query(..., description="URL to analyze")):
    """
    Live-updating version of POST /deep-analysis/link. Same analyzers,
    same result shape, but each of the ~12 checks (WHOIS, Safe
    Browsing, urlscan, VirusTotal, ...) streams back to the frontend
    the instant it finishes, instead of the client waiting for the
    slowest one (usually urlscan, ~15-25s) before seeing anything.

    Consume with EventSource on the frontend:
        source.addEventListener("source", (e) => { ...one analyzer's result... })
        source.addEventListener("done", (e) => { ...verdict + explanation... })
    """
    validated_url = _validate_url(url)
    return StreamingResponse(
        _stream_url_analysis(validated_url, "analyze_link"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/domain/stream")
async def deep_analyze_domain_stream(domain: str = Query(..., description="Domain to analyze")):
    """Live-updating version of POST /deep-analysis/domain. See /link/stream above."""
    domain = (domain or "").strip()

    if not domain:
        raise HTTPException(status_code=400, detail="No domain provided.")

    return StreamingResponse(
        _stream_url_analysis(domain, "analyze_sender_domain"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/page-source")
async def deep_analysis_page_source(url: str = Query(..., description="URL to fetch raw HTML for")):
    """
    Backs the "Preview page" button on the Deep Analysis Report page.

    Fetches the URL's HTML *server-side* (same crawler the `crawl` check
    uses) and hands it back as JSON so the frontend can render a
    sandboxed, script-free preview -- the user's own browser never
    connects to the target URL directly. This intentionally doesn't
    re-run the other 10 checks; it's just the raw fetch.
    """
    validated_url = _validate_url(url)

    try:
        source = fetch_page_source(validated_url)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))

    html = source["html"] or ""

    if len(html.encode("utf-8", errors="ignore")) > MAX_PREVIEW_HTML_BYTES:
        html = (
            html.encode("utf-8", errors="ignore")[:MAX_PREVIEW_HTML_BYTES].decode("utf-8", errors="ignore")
            + "\n<!-- truncated: page exceeded the 3 MB preview limit -->"
        )

    return {
        "html": html,
        "final_url": source["final_url"],
        "status_code": source["status_code"],
    }


@router.post("/pdf-attachment")
async def deep_analyze_pdf(file: UploadFile = File(...)):
    """
    UI option: 'Scan PDF attachment'.

    Takes the attachment the user picked on the deep-analysis page
    (re-uploaded from the browser, since the backend doesn't retain raw
    attachment bytes from the original /api/analyze call) and runs it
    through analyzer.py in an isolated subprocess.
    """

    temp_path = await _save_upload(file, ALLOWED_PDF_EXTENSIONS)

    try:
        result = analyze_pdf_attachment(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return {
        "option": "analyze_pdf_attachment",
        "result": result,
        "explanation": _explain("analyze_pdf_attachment", result),
    }


@router.post("/case/{case_id}/attachment/{index}")
async def deep_analyze_case_attachment(case_id: str, index: int):
    """
    "Deep analyze" button on an attachment card already shown on an
    existing case (Extracted links / Detected attachments panels) -- no
    re-upload needed. Re-extracts that attachment's raw bytes from the
    .eml kept in app.services.store for this case_id, picks the PDF or
    image analyzer based on its extension, and runs the same pipeline as
    the /pdf-attachment and /image-attachment routes above.
    """

    raw_eml = store.get_raw_eml(case_id)

    if raw_eml is None:
        raise HTTPException(
            status_code=404,
            detail="No stored email found for this case (it may have expired).",
        )

    found = extract_attachment_bytes(raw_eml, index)

    if found is None:
        raise HTTPException(status_code=404, detail="No attachment at that index.")

    filename, _content_type, payload = found

    if not payload:
        raise HTTPException(status_code=400, detail="Attachment is empty.")

    if len(payload) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File exceeds the 10 MB deep-analysis limit.",
        )

    suffix = Path(filename or "").suffix.lower()

    if suffix in ALLOWED_PDF_EXTENSIONS:
        option_id, analyzer = "analyze_pdf_attachment", analyze_pdf_attachment
    elif suffix in ALLOWED_IMAGE_EXTENSIONS:
        option_id, analyzer = "analyze_image_attachment", analyze_image_attachment
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Deep scan isn't supported for '{suffix or 'this'}' attachments yet. "
                f"Supported: {', '.join(sorted(ALLOWED_PDF_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS))}"
            ),
        )

    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix="mailguard_deep_",
        delete=False,
    ) as tmp:
        tmp.write(payload)
        temp_path = tmp.name

    try:
        result = analyzer(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return {
        "option": option_id,
        "result": result,
        "explanation": _explain(option_id, result),
    }


@router.post("/image-attachment")
async def deep_analyze_image(file: UploadFile = File(...)):
    """
    UI option: 'Scan image attachment'.

    Same idea as the PDF route: takes the re-uploaded image attachment
    and runs it through deep_image_analyzer.py in an isolated subprocess
    (requires the `exiftool` binary on the server, see that file's
    header comment).
    """

    temp_path = await _save_upload(file, ALLOWED_IMAGE_EXTENSIONS)

    try:
        result = analyze_image_attachment(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return {
        "option": "analyze_image_attachment",
        "result": result,
        "explanation": _explain("analyze_image_attachment", result),
    }
