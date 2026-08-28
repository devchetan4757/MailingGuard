/**
 * Epic 1/2/3 owner(s) — analyze endpoint client.
 * CONTRACT: analyzeEmail(file) -> Promise<AnalyzeResponse>
 * (see backend/app/models/schemas.py for the exact shape)
 */

import { apiFetch } from "./client";

export function analyzeEmail(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch("/analyze", {
    method: "POST",
    body: formData,
  });
}
