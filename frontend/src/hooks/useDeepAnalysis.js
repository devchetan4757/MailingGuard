/**
 * Tracks deep-analysis state per data card (one entry per URL/attachment
 * key) so multiple "Deep analyze" buttons on the same page can each be
 * loading/showing a result independently.
 *
 * Two run modes:
 *   run(key, requestFn)              -- one-shot (attachments: PDF/image
 *                                        scans aren't streamed, they come
 *                                        back as a single subprocess result)
 *   runStream(key, streamFn)         -- live-updating (links/domains):
 *                                        `sources` fills in one entry at a
 *                                        time as each check finishes
 *
 * state[key] = {
 *   status: "loading" | "done" | "error",
 *   sources?: { [sourceKey]: rawResult }  -- fills in live during streaming
 *   data?, error?
 * }
 */

import { useCallback, useRef, useState } from "react";

export function useDeepAnalysis() {
  const [state, setState] = useState({});
  // Holds each key's `close()` fn so a re-run or unmount can drop the
  // previous EventSource connection instead of leaking it.
  const closers = useRef({});

  const run = useCallback(async (key, requestFn) => {
    setState((prev) => ({ ...prev, [key]: { status: "loading" } }));

    try {
      const data = await requestFn();
      setState((prev) => ({ ...prev, [key]: { status: "done", data } }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        [key]: { status: "error", error: err.message || "Analysis failed." },
      }));
    }
  }, []);

  const runStream = useCallback((key, streamFn) => {
    closers.current[key]?.();

    setState((prev) => ({ ...prev, [key]: { status: "loading", sources: {} } }));

    const close = streamFn({
      onSource: (payload) => {
        const { key: sourceKey, ...result } = payload;
        setState((prev) => {
          const entry = prev[key];
          if (!entry || entry.status !== "loading") return prev; // stale event after clear/retry
          return {
            ...prev,
            [key]: { ...entry, sources: { ...entry.sources, [sourceKey]: result } },
          };
        });
      },
      onDone: (payload) => {
        setState((prev) => ({
          ...prev,
          [key]: {
            status: "done",
            data: { explanation: payload.explanation, result: payload },
            sources: payload.sources,
          },
        }));
      },
      onError: (message) => {
        setState((prev) => ({ ...prev, [key]: { status: "error", error: message } }));
      },
    });

    closers.current[key] = close;
  }, []);

  const clear = useCallback((key) => {
    closers.current[key]?.();
    delete closers.current[key];

    setState((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  return { state, run, runStream, clear };
}
