/**
 * Shared fetch wrapper — integrator owned.
 * Everyone else: import `apiFetch`, don't call fetch() directly in your
 * own api file, so the base URL and error handling stay in one place.
 */

export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    cache: "no-store",
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }

  return res.json();
}
