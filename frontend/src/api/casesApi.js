/**
 * Epic 4 owner — cases + report endpoint clients.
 */

import { apiFetch } from "./client";

export function listCases() {
  return apiFetch("/cases");
}

export function getCase(caseId) {
  return apiFetch(`/cases/${caseId}`);
}

export function getCaseReportUrl(caseId) {
  const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
  return `${BASE_URL}/cases/${caseId}/report`;
}

// Same PDF as getCaseReportUrl, but served `inline` so it can be dropped
// straight into an <iframe> for a live preview instead of forcing a
// browser download prompt.
export function getCaseReportPreviewUrl(caseId) {
  const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
  return `${BASE_URL}/cases/${caseId}/report/preview`;
}
