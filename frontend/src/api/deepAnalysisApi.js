/**
 * Client for the /deep-analysis/* endpoints (backend/app/api/deep_analysis.py).
 *
 * These back the "Deep analyze" buttons that live directly on the existing
 * data cards (Extracted links, Detected attachments) instead of a separate
 * manual-entry panel -- the link/attachment is already known from the case,
 * so the user shouldn't have to paste or re-pick anything.
 */

import { apiFetch, BASE_URL } from "./client";

// One AI-analyzed link/attachment/domain result.
// { option: string, result: object, explanation: string | null }

export function analyzeLink(url) {
  return apiFetch("/deep-analysis/link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export function analyzeDomain(domain) {
  return apiFetch("/deep-analysis/domain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain }),
  });
}

// Fetches the page's raw HTML *server-side* and hands it back as text --
// the browser never connects to the (possibly malicious) URL directly.
// Expected shape: { html: string, final_url: string, status_code: number }.
// Backend contract (not yet implemented as of this frontend change):
//   GET /deep-analysis/page-source?url=<url>
// This is deliberately a separate call from analyzeLink/streamAnalyzeLink
// -- fetching the full HTML body is comparatively heavy, so it only
// happens when someone actually asks to preview the page, not on every
// deep analysis run.
export function fetchPageSource(url) {
  return apiFetch(`/deep-analysis/page-source?${new URLSearchParams({ url }).toString()}`);
}

// Re-extracts the attachment straight from the case's stored .eml on the
// backend -- no re-upload from the browser needed.
export function analyzeCaseAttachment(caseId, index) {
  return apiFetch(`/deep-analysis/case/${caseId}/attachment/${index}`, {
    method: "POST",
  });
}

/**
 * Live-updating versions of analyzeLink/analyzeDomain, backed by the
 * /deep-analysis/{link,domain}/stream SSE endpoints. Each of the ~12
 * checks (WHOIS, Safe Browsing, urlscan, VirusTotal, ...) calls
 * onSource() the instant that ONE check finishes, well before the
 * slowest one is done -- this is what lets the modal fill in live
 * instead of showing a single spinner for 15-25s.
 *
 * callbacks:
 *   onSource(payload)  -- payload = { key, ...that source's raw result }
 *   onDone(payload)    -- payload = { verdict, sources, explanation, url, domain }
 *   onError(message)
 *
 * Returns a close() function -- call it if the modal is dismissed
 * mid-stream, so the browser drops the open connection.
 */
function _streamViaEventSource(path, params, { onSource, onDone, onError }) {
  const query = new URLSearchParams(params).toString();
  const source = new EventSource(`${BASE_URL}${path}?${query}`);

  source.addEventListener("source", (event) => {
    try {
      onSource(JSON.parse(event.data));
    } catch {
      /* ignore a malformed single event -- stream continues */
    }
  });

  source.addEventListener("done", (event) => {
    try {
      onDone(JSON.parse(event.data));
    } catch {
      onError("Could not parse the final analysis result.");
    } finally {
      source.close();
    }
  });

  source.onerror = () => {
    onError("Connection to the analyzer stream was lost.");
    source.close();
  };

  return () => source.close();
}

export function streamAnalyzeLink(url, callbacks) {
  return _streamViaEventSource("/deep-analysis/link/stream", { url }, callbacks);
}

export function streamAnalyzeDomain(domain, callbacks) {
  return _streamViaEventSource("/deep-analysis/domain/stream", { domain }, callbacks);
}
