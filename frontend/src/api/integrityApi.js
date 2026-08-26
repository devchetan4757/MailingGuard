/**
 * integrityApi.js
 * ----------------
 * All network calls for the Security & Integrity module, in one place.
 * Every function returns a plain parsed JSON body (or throws), so
 * components never touch `fetch` or response objects directly.
 *
 * Backend routes: backend/app/api/security_routes.py
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — keep the default statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

/** Upload a .eml file for validation. Seals + ledgers it on success. */
export function validateUpload(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/security/validate", { method: "POST", body: formData });
}

/** Fetch the full sealed-case ledger, oldest first. */
export function fetchLedger() {
  return request("/api/security/ledger");
}

/** Run the tamper-evidence check across the whole ledger. */
export function verifyChain() {
  return request("/api/security/verify-chain");
}

/** Preview raw vs. sanitized text for arbitrary content. */
export function sanitizePreview(text) {
  return request("/api/security/sanitize-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

/** Seed the ledger with sample cases (demo convenience). */
export function seedDemoData() {
  return request("/api/security/demo/seed", { method: "POST" });
}

/** Deliberately corrupt a stored case, to demonstrate detection. */
export function tamperCase(caseId, newRiskScore = 5) {
  return request("/api/security/demo/tamper", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ caseId, newRiskScore }),
  });
}

/** Wipe the ledger back to empty. */
export function resetLedger() {
  return request("/api/security/demo/reset", { method: "POST" });
}
