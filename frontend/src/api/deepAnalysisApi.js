/**
 * Client for the /deep-analysis/* endpoints (backend/app/api/deep_analysis.py).
 *
 * These back the "Deep analyze" buttons that live directly on the existing
 * data cards (Extracted links, Detected attachments) instead of a separate
 * manual-entry panel -- the link/attachment is already known from the case,
 * so the user shouldn't have to paste or re-pick anything.
 */

import { apiFetch } from "./client";

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

// Re-extracts the attachment straight from the case's stored .eml on the
// backend -- no re-upload from the browser needed.
export function analyzeCaseAttachment(caseId, index) {
  return apiFetch(`/deep-analysis/case/${caseId}/attachment/${index}`, {
    method: "POST",
  });
}
