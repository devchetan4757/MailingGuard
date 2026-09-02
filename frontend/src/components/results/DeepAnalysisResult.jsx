// src/components/results/DeepAnalysisResult.jsx
/**
 * Inline "Deep analyze" trigger + result panel, meant to sit directly on
 * an existing data card (a URL row, an attachment row, ...) rather than
 * sending the user to a separate manual-entry panel -- the thing being
 * analyzed is already known from the card it's attached to.
 *
 * Two pieces, used together by the parent card:
 *   <DeepAnalyzeTrigger .../>  -- small button/status, sits in the row
 *   <DeepAnalyzePanel .../>    -- full result, rendered below the row
 */

import { useState } from "react";
import { BrainCircuit, ChevronDown, LoaderCircle, ShieldAlert, XCircle } from "lucide-react";

export function DeepAnalyzeTrigger({ label, entry, onRun, onClear }) {
  const status = entry?.status;

  if (!status) {
    return (
      <button type="button" className="ref-deep-btn" onClick={onRun} title={`Deep analyze ${label}`}>
        <BrainCircuit size={13} />
        Deep analyze
      </button>
    );
  }

  if (status === "loading") {
    return (
      <span className="ref-deep-btn is-loading" aria-live="polite">
        <LoaderCircle size={13} className="ref-deep-spin" />
        Analyzing…
      </span>
    );
  }

  if (status === "error") {
    return (
      <button type="button" className="ref-deep-btn is-error" onClick={onRun} title={entry.error}>
        <XCircle size={13} />
        Retry
      </button>
    );
  }

  // done — collapse back to a small "re-run" affordance; the full result
  // is shown by DeepAnalyzePanel below the row.
  return (
    <button type="button" className="ref-deep-btn is-done" onClick={onClear} title="Close result">
      <BrainCircuit size={13} />
      Analyzed
    </button>
  );
}

// Only show a handful of primitive fields when there's no Groq explanation
// to fall back on (raw analyzer shapes differ per analyzer type).
function RawFallback({ result }) {
  const [open, setOpen] = useState(false);

  const entries = Object.entries(result || {}).filter(
    ([, value]) => value === null || ["string", "number", "boolean"].includes(typeof value)
  );

  return (
    <div className="ref-deep-raw">
      {entries.slice(0, 6).map(([key, value]) => (
        <div className="ref-deep-raw-row" key={key}>
          <span>{key.replaceAll("_", " ")}</span>
          <strong>{value === null || value === "" ? "—" : String(value)}</strong>
        </div>
      ))}

      <button type="button" className="ref-deep-raw-toggle" onClick={() => setOpen((o) => !o)}>
        <ChevronDown size={12} style={{ transform: open ? "rotate(180deg)" : "none" }} />
        {open ? "Hide" : "Show"} raw result
      </button>

      {open && <pre className="ref-deep-raw-json">{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export function DeepAnalyzePanel({ entry, onRun, onClear }) {
  if (!entry) return null;

  if (entry.status === "error") {
    return (
      <div className="ref-deep-panel is-error">
        <div className="ref-deep-panel-head">
          <XCircle size={14} />
          <span>{entry.error}</span>
          <button type="button" onClick={onRun}>Retry</button>
          <button type="button" onClick={onClear}>Dismiss</button>
        </div>
      </div>
    );
  }

  if (entry.status !== "done") return null;

  const { explanation, result } = entry.data || {};

  return (
    <div className="ref-deep-panel">
      <div className="ref-deep-panel-head">
        <BrainCircuit size={14} />
        <span>AI deep analysis</span>
        <button type="button" onClick={onClear}>Close</button>
      </div>

      {explanation ? (
        <p className="ref-deep-explanation">{explanation}</p>
      ) : (
        <p className="ref-deep-explanation ref-deep-explanation-muted">
          <ShieldAlert size={12} /> No AI summary available — showing raw findings.
        </p>
      )}

      <RawFallback result={result} />
    </div>
  );
}
