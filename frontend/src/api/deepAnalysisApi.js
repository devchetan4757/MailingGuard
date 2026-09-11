/**
 * Client for the /deep-analysis/* endpoints.
 *
 * Deep analysis is performed by the backend. The frontend only sends the
 * already-known URL, domain, or case attachment reference and renders the
 * returned analysis result.
 */

import { apiFetch, BASE_URL } from "./client";

/**
 * Analyze a URL.
 *
 * Backend:
 * POST /deep-analysis/link
 *
 * Returns:
 * {
 *   option: string,
 *   result: object,
 *   explanation: string | null
 * }
 */
export function analyzeLink(url) {
  return apiFetch("/deep-analysis/link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

/**
 * Analyze a domain.
 *
 * Backend:
 * POST /deep-analysis/domain
 */
export function analyzeDomain(domain) {
  return apiFetch("/deep-analysis/domain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain }),
  });
}

/**
 * Fetch page source through the backend.
 *
 * The browser does not directly request the potentially unsafe URL.
 *
 * Backend:
 * GET /deep-analysis/page-source?url=<url>
 */
export function fetchPageSource(url) {
  return apiFetch(
    `/deep-analysis/page-source?${new URLSearchParams({ url }).toString()}`
  );
}

/**
 * Analyze an attachment belonging to an already analyzed email case.
 *
 * The backend extracts the attachment directly from the stored .eml file.
 *
 * Backend:
 * POST /deep-analysis/case/{caseId}/attachment/{index}
 *
 * The backend determines the attachment type and currently supports:
 * - PDF
 * - Image attachments
 *
 * For PDFs, the backend runs the complete PDF analyzer and returns the
 * complete PDF analysis result, including the generated URL analysis.
 */
export function analyzeCaseAttachment(caseId, index) {
  if (!caseId) {
    return Promise.reject(new Error("Missing case ID."));
  }

  if (index === undefined || index === null) {
    return Promise.reject(new Error("Missing attachment index."));
  }

  return apiFetch(
    `/deep-analysis/case/${encodeURIComponent(caseId)}/attachment/${index}`,
    {
      method: "POST",
    }
  );
}

/**
 * Internal helper for Server-Sent Event based deep analysis.
 *
 * The stream emits:
 *
 * source:
 *   { key, ...sourceResult }
 *
 * done:
 *   { verdict, sources, explanation, url, domain }
 *
 * This is used for URL/domain analysis so individual checks can appear
 * progressively in the UI.
 */
function _streamViaEventSource(
  path,
  params,
  { onSource, onDone, onError }
) {
  const query = new URLSearchParams(params).toString();
  const source = new EventSource(`${BASE_URL}${path}?${query}`);

  source.addEventListener("source", (event) => {
    try {
      onSource?.(JSON.parse(event.data));
    } catch {
      // Ignore malformed individual events and keep the stream alive.
    }
  });

  source.addEventListener("done", (event) => {
    try {
      onDone?.(JSON.parse(event.data));
    } catch {
      onError?.("Could not parse the final analysis result.");
    } finally {
      source.close();
    }
  });

  source.onerror = () => {
    onError?.("Connection to the analyzer stream was lost.");
    source.close();
  };

  return () => {
    source.close();
  };
}

/**
 * Stream URL analysis.
 */
export function streamAnalyzeLink(url, callbacks) {
  return _streamViaEventSource(
    "/deep-analysis/link/stream",
    { url },
    callbacks
  );
}

/**
 * Stream domain analysis.
 */
export function streamAnalyzeDomain(domain, callbacks) {
  return _streamViaEventSource(
    "/deep-analysis/domain/stream",
    { domain },
    callbacks
  );
}
