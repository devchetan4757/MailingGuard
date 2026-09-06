// src/components/results/DeepAnalysisResult.jsx
/**
 * Inline "Deep analyze" trigger + a small modal window showing results
 * LIVE as each backend check finishes, instead of one big spinner
 * until all ~12 checks are done.
 *
 * Two pieces, used together by the parent card:
 *   <DeepAnalyzeTrigger .../>  -- small button/status, sits in the row
 *   <DeepAnalyzeModal .../>    -- the small result window (Modal-based)
 */

import { useState } from "react";
import {
  AlertTriangle,
  BrainCircuit,
  Check,
  ChevronDown,
  LoaderCircle,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import Modal from "../shared/Modal";

// Friendly labels + order for the streamed sources. Anything that
// arrives with a key not in this list still renders, just at the end,
// under its raw key -- so a newly-added analyzer never gets dropped
// silently, it just looks a little less polished until this list is
// updated to match.
// Exported so other views (e.g. the full-page deep analysis report) can
// render the exact same source list/labels/verdict logic instead of
// duplicating it.
export const SOURCE_LABELS = {
  crawl: "Page crawl",
  whois: "WHOIS / DNS",
  safe_browsing: "Google Safe Browsing",
  openphish: "OpenPhish",
  urlhaus: "URLhaus",
  urlscan: "urlscan.io",
  virustotal: "VirusTotal",
  crt_sh: "Certificate log",
  dnstwist: "Lookalike domains",
  abuseipdb: "AbuseIPDB",
  shodan: "Shodan",
};

export const SOURCE_ORDER = Object.keys(SOURCE_LABELS);

// Groups the 11 raw checks into a handful of categories so the report can
// show "how risky is this link, broken down by kind of check" instead of
// just a flat list. Anything not listed here (a future analyzer) simply
// doesn't show up in the category chart -- it still renders fine
// everywhere else via SOURCE_ORDER/extraKeys.
export const CATEGORY_LABELS = {
  reputation: "Reputation & blocklists",
  infrastructure: "Infrastructure & identity",
  content: "Content & similarity",
};

export const CATEGORY_ORDER = ["reputation", "infrastructure", "content"];

export const SOURCE_CATEGORY = {
  safe_browsing: "reputation",
  openphish: "reputation",
  urlhaus: "reputation",
  virustotal: "reputation",
  abuseipdb: "reputation",
  whois: "infrastructure",
  crt_sh: "infrastructure",
  shodan: "infrastructure",
  urlscan: "infrastructure",
  crawl: "content",
  dnstwist: "content",
};

export function isFlagged(result) {
  if (!result || typeof result !== "object") return false;
  if (result.error) return null; // neutral -- skipped/unavailable, not a verdict either way
  return Boolean(
    result.malicious ||
      result.listed ||
      result.in_database ||
      result.flagged ||
      (typeof result.abuse_confidence_score === "number" && result.abuse_confidence_score > 25) ||
      (Array.isArray(result.vulnerabilities) && result.vulnerabilities.length > 0) ||
      // dnstwist doesn't use any of the fields above -- it reports
      // registered_lookalike_count/lookalikes instead. Without this,
      // dnstwist renders "Clean" no matter how many lookalike domains
      // it actually finds.
      (typeof result.registered_lookalike_count === "number" && result.registered_lookalike_count > 0)
  );
}

export function SourceIcon({ result }) {
  if (!result) return <LoaderCircle size={13} className="ref-deep-spin" />;
  const flagged = isFlagged(result);
  if (flagged === null) return <span className="ref-source-dot is-skipped" title={result.error} />;
  return flagged ? (
    <AlertTriangle size={13} className="ref-source-icon is-flagged" />
  ) : (
    <Check size={13} className="ref-source-icon is-clean" />
  );
}

export function riskMeta(level) {
  switch (level) {
    case "critical":
      return { icon: ShieldAlert, label: "Critical risk", cls: "is-critical" };
    case "high":
      return { icon: ShieldAlert, label: "High risk", cls: "is-high" };
    case "medium":
      return { icon: AlertTriangle, label: "Medium risk", cls: "is-medium" };
    default:
      return { icon: ShieldCheck, label: "Low risk", cls: "is-low" };
  }
}

export function DeepAnalyzeTrigger({ label, entry, onRun, onOpen, onClear }) {
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
    const done = entry.sources ? Object.keys(entry.sources).length : 0;
    return (
      <button type="button" className="ref-deep-btn is-loading" onClick={onOpen} aria-live="polite">
        <LoaderCircle size={13} className="ref-deep-spin" />
        Analyzing… {done > 0 && `(${done})`}
      </button>
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

  const verdict = entry?.data?.result?.verdict;

  return (
    <button
      type="button"
      className={`ref-deep-btn is-done ${verdict ? `is-risk-${verdict.risk_level}` : ""}`}
      onClick={onOpen}
      title="View result"
    >
      <BrainCircuit size={13} />
      {verdict ? riskMeta(verdict.risk_level).label : "View result"}
    </button>
  );
}

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

// Turns a raw error string (an HTTP status, a timeout message, a
// "no API key" note, etc.) into a short, plain-language reason so the
// user sees WHY a check didn't run instead of a bare "unavailable"
// that looks like the app itself is broken.
export function friendlyErrorReason(error) {
  if (!error) return "Unavailable";
  const text = String(error);

  if (/no api key|skipped/i.test(text)) return "No API key configured";
  if (/429|rate limit/i.test(text)) return "Rate limited — try again shortly";
  if (/timed out|timeout/i.test(text)) return "Timed out — service was too slow";
  if (/401|403|unauthorized|forbidden/i.test(text)) return "Access denied — check the API key";
  if (/connection|resolve|refused/i.test(text)) return "Couldn't connect to this service";
  if (/50\d/.test(text)) return "This service is temporarily down";

  return "Temporarily unavailable";
}

function SourceRow({ sourceKey, result }) {
  const [open, setOpen] = useState(false);
  const label = SOURCE_LABELS[sourceKey] || sourceKey.replaceAll("_", " ");
  const pending = !result;
  const flagged = isFlagged(result);

  return (
    <div className={`ref-source-row ${pending ? "is-pending" : ""}`}>
      <button
        type="button"
        className="ref-source-row-head"
        onClick={() => result && setOpen((o) => !o)}
        disabled={pending}
      >
        <SourceIcon result={result} />
        <span>{label}</span>
        {result?.error && flagged === null && (
          <em className="ref-source-note">{friendlyErrorReason(result.error)}</em>
        )}
        {!pending && (
          <ChevronDown size={12} className="ref-source-chevron" style={{ transform: open ? "rotate(180deg)" : "none" }} />
        )}
      </button>

      {open && result && !result.error && (
        <div className="ref-source-detail">
          <RawFallback result={result} />
        </div>
      )}

      {open && result?.error && (
        <div className="ref-source-detail ref-source-detail-error">
          <p className="ref-source-error-detail">{String(result.error)}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Inline version of the result view -- same content as DeepAnalyzeModal,
 * but rendered directly in the card flow instead of inside a Modal.
 * Used by panels that show results inline under the trigger button
 * rather than popping up a dialog.
 */
export function DeepAnalyzePanel({ entry, onRun, onClear }) {
  if (!entry) return null;

  const sources = entry.sources || {};
  const extraKeys = Object.keys(sources).filter((k) => !SOURCE_ORDER.includes(k));
  const orderedKeys = [...SOURCE_ORDER, ...extraKeys];

  const totalExpected = SOURCE_ORDER.length;
  const totalDone = Object.keys(sources).length;

  const verdict = entry.status === "done" ? entry.data?.result?.verdict : null;
  const explanation = entry.status === "done" ? entry.data?.explanation : null;

  return (
    <div className="ref-deep-panel-inline">
      {entry.status === "error" ? (
        <div className="ref-deep-panel is-error">
          <XCircle size={14} />
          <span>{entry.error}</span>
          <button type="button" onClick={onRun}>Retry</button>
          {onClear && (
            <button type="button" onClick={onClear}>Dismiss</button>
          )}
        </div>
      ) : (
        <>
          <div className="ref-deep-modal-head">
            <BrainCircuit size={16} />
            <span>Deep analysis</span>
            {onClear && (
              <button type="button" className="ref-deep-modal-close" onClick={onClear}>
                Close
              </button>
            )}
          </div>

          {entry.status === "loading" && (
            <div className="ref-deep-modal-progress">
              <LoaderCircle size={12} className="ref-deep-spin" />
              {totalDone} of {totalExpected} checks complete…
            </div>
          )}

          {verdict && (() => {
            const { icon: Icon, label, cls } = riskMeta(verdict.risk_level);
            return (
              <div className={`ref-deep-verdict ${cls}`}>
                <Icon size={16} />
                <div>
                  <strong>{label}</strong>
                  <span>Score {verdict.risk_score}/100</span>
                </div>
              </div>
            );
          })()}

          {explanation && <p className="ref-deep-explanation">{explanation}</p>}

          {verdict && verdict.flags.length > 0 && (
            <ul className="ref-deep-flags">
              {verdict.flags.map((flag, i) => (
                <li key={i}>{flag}</li>
              ))}
            </ul>
          )}

          <div className="ref-source-list">
            {orderedKeys.map((key) => (
              <SourceRow key={key} sourceKey={key} result={sources[key]} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/**
 * The "small window" -- a Modal containing the live-updating list of
 * per-source results, filling in one row at a time as the SSE stream
 * delivers them, then the overall verdict once every check is in.
 */
export function DeepAnalyzeModal({ isOpen, entry, onClose, onRun }) {
  if (!entry) return null;

  const sources = entry.sources || {};
  const extraKeys = Object.keys(sources).filter((k) => !SOURCE_ORDER.includes(k));
  const orderedKeys = [...SOURCE_ORDER, ...extraKeys];

  const totalExpected = SOURCE_ORDER.length;
  const totalDone = Object.keys(sources).length;

  const verdict = entry.status === "done" ? entry.data?.result?.verdict : null;
  const explanation = entry.status === "done" ? entry.data?.explanation : null;

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="ref-deep-modal">
        <div className="ref-deep-modal-head">
          <BrainCircuit size={16} />
          <span>Deep analysis</span>
          <button type="button" className="ref-deep-modal-close" onClick={onClose}>
            Close
          </button>
        </div>

        {entry.status === "error" ? (
          <div className="ref-deep-panel is-error">
            <XCircle size={14} />
            <span>{entry.error}</span>
            <button type="button" onClick={onRun}>Retry</button>
          </div>
        ) : (
          <>
            {entry.status === "loading" && (
              <div className="ref-deep-modal-progress">
                <LoaderCircle size={12} className="ref-deep-spin" />
                {totalDone} of {totalExpected} checks complete…
              </div>
            )}

            {verdict && (() => {
              const { icon: Icon, label, cls } = riskMeta(verdict.risk_level);
              return (
                <div className={`ref-deep-verdict ${cls}`}>
                  <Icon size={16} />
                  <div>
                    <strong>{label}</strong>
                    <span>Score {verdict.risk_score}/100</span>
                  </div>
                </div>
              );
            })()}

            {explanation && <p className="ref-deep-explanation">{explanation}</p>}

            {verdict && verdict.flags.length > 0 && (
              <ul className="ref-deep-flags">
                {verdict.flags.map((flag, i) => (
                  <li key={i}>{flag}</li>
                ))}
              </ul>
            )}

            <div className="ref-source-list">
              {orderedKeys.map((key) => (
                <SourceRow key={key} sourceKey={key} result={sources[key]} />
              ))}
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
