import { apiFetch, BASE_URL } from "./client";

export function getGmailStatus() {
  return apiFetch("/integrations/gmail/status");
}

export function getGmailDashboard() {
  return apiFetch("/integrations/gmail/dashboard");
}

/**
 * Streams the Gmail dashboard via Server-Sent Events instead of
 * waiting for every message (up to 100) to load before showing
 * anything.
 *
 * `onEvent` is called with `{ event, data }` for every message
 * received — `event` is one of "progress", "complete", "error".
 * On "progress"/"complete", `data` is the same shape the plain
 * getGmailDashboard() call returns (plus `loaded`/`total`), so
 * it can be dropped straight into dashboard state.
 *
 * Returns an AbortController — call `.abort()` (e.g. on
 * unmount or before starting a new stream) to stop it early.
 */
export function streamGmailDashboard(
  onEvent,
  { batchSize = 4 } = {}
) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(
        `${BASE_URL}/integrations/gmail/dashboard/stream?batch_size=${batchSize}`,
        { signal: controller.signal }
      );

      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          body.detail || `Request failed (${res.status})`
        );
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE messages are separated by a blank line.
        const messages = buffer.split("\n\n");
        buffer = messages.pop() ?? "";

        for (const raw of messages) {
          if (!raw.trim()) continue;

          const lines = raw.split("\n");

          const eventLine = lines.find((line) =>
            line.startsWith("event: ")
          );
          const dataLine = lines.find((line) =>
            line.startsWith("data: ")
          );

          if (!dataLine) continue;

          const event = eventLine
            ? eventLine.slice("event: ".length).trim()
            : "message";

          let data;
          try {
            data = JSON.parse(dataLine.slice("data: ".length));
          } catch {
            continue;
          }

          onEvent({ event, data });
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        onEvent({
          event: "error",
          data: {
            message:
              err.message || "Gmail dashboard stream failed.",
          },
        });
      }
    }
  })();

  return controller;
}

export function getGmailMessages(maxResults = 20) {
  return apiFetch(
    `/integrations/gmail/messages?max_results=${maxResults}`
  );
}

export function syncGmail() {
  return apiFetch("/integrations/gmail/sync", {
    method: "POST",
  });
}

export function clearGmailCache() {
  return apiFetch("/integrations/gmail/cache", {
    method: "DELETE",
  });
}

export async function connectGmail() {
  const data = await apiFetch(
    "/integrations/gmail/connect"
  );

  if (!data?.authorization_url) {
    throw new Error(
      "Google authorization URL was not returned."
    );
  }

  window.location.href = data.authorization_url;
}
