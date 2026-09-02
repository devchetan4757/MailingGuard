/**
 * Tracks deep-analysis state per data card (one entry per URL/attachment
 * key) so multiple "Deep analyze" buttons on the same page can each be
 * loading/showing a result independently.
 *
 * state[key] = { status: "loading" | "done" | "error", data?, error? }
 */

import { useCallback, useState } from "react";

export function useDeepAnalysis() {
  const [state, setState] = useState({});

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

  const clear = useCallback((key) => {
    setState((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  return { state, run, clear };
}
