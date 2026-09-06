// src/pages/DeepAnalysisReportPage.jsx
/**
 * Full-page "Deep analysis report" for a single URL — reached from the
 * "Full report" button on an Extracted links card (EmailParsingPanel).
 *
 * Replaces the old small Modal popup: this is a real routed page, styled
 * like every other page in the app (reference-dashboard shell + ref-panel
 * cards), that lays out every field the analyzers returned alongside
 * charts summarizing what was found. It owns its own live SSE run so it
 * keeps updating even if the row it was opened from goes away, and can
 * be re-run/refreshed on its own.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  BrainCircuit,
  ChevronDown,
  Eye,
  Link2,
  LoaderCircle,
  RefreshCcw,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";

import { DashboardPanel, DashboardStat, RiskGauge } from "../components/dashboard/DashboardWidgets";
import {
  SOURCE_LABELS,
  SOURCE_ORDER,
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  SOURCE_CATEGORY,
  isFlagged,
  riskMeta,
  friendlyErrorReason,
  SourceIcon,
} from "../components/results/DeepAnalysisResult";
import { streamAnalyzeLink } from "../api/deepAnalysisApi";

// Pulls a single representative number out of a source's raw result so it
// can sit on the "signal strength" bar chart — different analyzers name
// their score/count field differently, so this checks the common shapes
// in order of how meaningful they are, and falls back to a flat 0/1.
// The shared .ref-verdict-banner styling keys its color off the site-wide
// red/yellow/green severity scale, while a deep-analysis verdict uses a
// finer critical/high/medium/low scale — map the latter onto the former
// so this banner picks up the same theming as every other verdict banner.
function severityFromRiskLevel(level) {
  if (level === "critical" || level === "high") return "red";
  if (level === "medium") return "yellow";
  if (level === "low") return "green";
  return undefined;
}

function signalStrength(result) {
  if (!result || result.error) return 0;
  if (typeof result.abuse_confidence_score === "number") return result.abuse_confidence_score;
  if (typeof result.risk_score === "number") return result.risk_score;
  if (Array.isArray(result.vulnerabilities)) return result.vulnerabilities.length * 10;
  if (Array.isArray(result.detections)) return result.detections.length * 10;
  if (typeof result.malicious === "number") return result.malicious * 10;
  // dnstwist has no score/count field the checks above recognize --
  // without this it always plots at 0 regardless of lookalikes found.
  if (typeof result.registered_lookalike_count === "number") return result.registered_lookalike_count * 10;
  return isFlagged(result) ? 100 : 0;
}

// ---------------------------------------------------------------------
// Turning a raw check result into something worth reading.
//
// Every analyzer returns a different shape, some of them huge (full
// certificate chains, redirect trails, vulnerability lists...). Rather
// than dump every key the backend happens to send, each card surfaces a
// handful of the most informative facts up front, tucks everything else
// behind a "more details" toggle in a still-compact form, and only falls
// back to a full JSON dump as a last resort for anyone who wants it.
// ---------------------------------------------------------------------

const HIGHLIGHT_HINTS = [
  "verdict", "malicious", "flagged", "listed", "in_database", "risk", "score",
  "confidence", "category", "categories", "threat", "tag", "country", "asn",
  "isp", "org", "organization", "registrar", "age", "status", "brand",
  "similarity", "reputation", "positives", "total_votes", "community",
];

function isPrimitive(value) {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function truncateText(text, max = 90) {
  const str = String(text);
  return str.length > max ? `${str.slice(0, max - 1)}…` : str;
}

function formatPrimitive(value) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

// One representative value out of an object, so a list of objects (e.g.
// certificate entries, redirect hops) can render as short preview chips
// instead of stringified JSON blobs.
function chipPreview(item) {
  if (item === null || item === undefined) return "—";
  if (isPrimitive(item)) return truncateText(item, 34);
  const entries = Object.entries(item).filter(([, v]) => isPrimitive(v) && v !== "" && v !== null);
  if (!entries.length) return "…";
  return truncateText(entries[0][1], 34);
}

// Splits a result's fields into short, glanceable "highlights" and
// everything else ("details" — long strings, arrays, nested objects).
function classifyFields(result) {
  const entries = Object.entries(result || {}).filter(
    ([key, value]) => key !== "error" && value !== null && value !== undefined && value !== ""
  );

  const highlights = [];
  const details = [];

  entries.forEach((entry) => {
    const [, value] = entry;
    if (isPrimitive(value) && String(value).length <= 48) highlights.push(entry);
    else details.push(entry);
  });

  highlights.sort((a, b) => {
    const rank = (key) => (HIGHLIGHT_HINTS.some((hint) => key.toLowerCase().includes(hint)) ? 0 : 1);
    return rank(a[0]) - rank(b[0]);
  });

  return { highlights: highlights.slice(0, 6), details };
}

function DetailRow({ fieldKey, value }) {
  const label = fieldKey.replaceAll("_", " ");

  if (Array.isArray(value)) {
    if (!value.length) return null;
    const preview = value.slice(0, 3);
    return (
      <div className="ref-report-detail-row">
        <span>{label}</span>
        <div className="ref-report-chip-row">
          {preview.map((item, i) => (
            <span className="ref-report-chip" key={i}>{chipPreview(item)}</span>
          ))}
          {value.length > preview.length && (
            <span className="ref-report-chip is-more">+{value.length - preview.length} more</span>
          )}
        </div>
      </div>
    );
  }

  if (typeof value === "object") {
    const count = Object.keys(value).length;
    return (
      <div className="ref-report-detail-row">
        <span>{label}</span>
        <span className="ref-report-detail-note">{count} field{count === 1 ? "" : "s"} — see raw JSON</span>
      </div>
    );
  }

  return (
    <div className="ref-report-detail-row">
      <span>{label}</span>
      <span className="ref-report-detail-text" title={String(value)}>{truncateText(value, 130)}</span>
    </div>
  );
}

function SourceReportCard({ sourceKey, result }) {
  const [rawOpen, setRawOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const label = SOURCE_LABELS[sourceKey] || sourceKey.replaceAll("_", " ");
  const pending = !result;
  const flagged = isFlagged(result);
  const hasFields = result && !result.error;
  const { highlights, details } = hasFields ? classifyFields(result) : { highlights: [], details: [] };

  return (
    <div
      className={`ref-report-source-card ${pending ? "is-pending" : ""} ${flagged ? "is-flagged" : ""} ${
        flagged === false ? "is-clean" : ""
      }`}
    >
      <div className="ref-report-source-head">
        <SourceIcon result={result} />
        <div className="ref-report-source-title">
          <strong>{label}</strong>
          <span>{sourceKey.replaceAll("_", " ")}</span>
        </div>
        {result?.error && flagged === null && (
          <em className="ref-report-source-reason">{friendlyErrorReason(result.error)}</em>
        )}
        {!pending && !result?.error && (
          <span className={`ref-report-source-tag ${flagged ? "is-flagged" : "is-clean"}`}>
            {flagged ? "Flagged" : "Clean"}
          </span>
        )}
      </div>

      {pending && (
        <p className="ref-report-pending-note">
          <LoaderCircle size={12} className="ref-deep-spin" />
          Waiting on this check…
        </p>
      )}

      {result?.error && (
        <p className="ref-report-error-detail">{String(result.error)}</p>
      )}

      {hasFields && (highlights.length > 0 || details.length > 0) && (
        <>
          {highlights.length > 0 ? (
            <div className="ref-report-field-grid">
              {highlights.map(([key, value]) => (
                <div className="ref-report-field" key={key}>
                  <span>{key.replaceAll("_", " ")}</span>
                  <strong>{formatPrimitive(value)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="ref-report-empty-note">No standout fields — see details below.</p>
          )}

          {details.length > 0 && (
            <>
              <button type="button" className="ref-deep-raw-toggle" onClick={() => setDetailsOpen((o) => !o)}>
                <ChevronDown size={12} style={{ transform: detailsOpen ? "rotate(180deg)" : "none" }} />
                {detailsOpen ? "Hide" : "Show"} {details.length} more detail{details.length === 1 ? "" : "s"}
              </button>

              {detailsOpen && (
                <div className="ref-report-detail-list">
                  {details.map(([key, value]) => (
                    <DetailRow key={key} fieldKey={key} value={value} />
                  ))}
                </div>
              )}
            </>
          )}

          <button type="button" className="ref-deep-raw-toggle ref-deep-raw-toggle-muted" onClick={() => setRawOpen((o) => !o)}>
            <ChevronDown size={12} style={{ transform: rawOpen ? "rotate(180deg)" : "none" }} />
            {rawOpen ? "Hide" : "Show"} raw JSON
          </button>

          {rawOpen && <pre className="ref-deep-raw-json">{JSON.stringify(result, null, 2)}</pre>}
        </>
      )}
    </div>
  );
}

function SourceVerdictDonut({ sources, orderedKeys }) {
  let clean = 0;
  let flagged = 0;
  let skipped = 0;
  let pending = 0;

  orderedKeys.forEach((key) => {
    const result = sources[key];
    if (!result) {
      pending += 1;
      return;
    }
    const flag = isFlagged(result);
    if (flag === null) skipped += 1;
    else if (flag) flagged += 1;
    else clean += 1;
  });

  const data = [
    { name: "Clean", value: clean, color: "#56a98a" },
    { name: "Flagged", value: flagged, color: "#c0574c" },
    { name: "Unavailable", value: skipped, color: "#cbd5d8" },
    { name: "Pending", value: pending, color: "#e4e9ea" },
  ].filter((d) => d.value > 0);

  const total = orderedKeys.length;

  return (
    <div className="ref-report-donut">
      <div className="ref-report-donut-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="68%" outerRadius="94%" paddingAngle={3} stroke="none">
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="ref-report-donut-center">
          <strong>{clean + flagged + skipped}</strong>
          <span>of {total} checks</span>
        </div>
      </div>

      <div className="ref-report-donut-legend">
        {data.map((d) => (
          <div className="ref-report-donut-legend-row" key={d.name}>
            <i style={{ background: d.color }} />
            <span>{d.name}</span>
            <b>{d.value}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

// Renamed from "signal strength" (0 = clean, 100 = risky) to a legitimacy
// score (100 = clean, 0 = risky) so a fully clean link shows full, green,
// lively bars/shapes instead of an empty-looking chart, and reads as "how
// legit is this" rather than "how much risk did we find".
function legitimacyScore(result) {
  if (!result || result.error) return null;
  return 100 - Math.min(100, signalStrength(result));
}

function legitColor(value) {
  if (value >= 70) return "#56a98a";
  if (value >= 40) return "#e8b45c";
  return "#df7469";
}

function LegitimacyChart({ sources, orderedKeys }) {
  const data = orderedKeys
    .filter((key) => sources[key] && !sources[key].error)
    .map((key) => ({
      name: SOURCE_LABELS[key] || key.replaceAll("_", " "),
      value: legitimacyScore(sources[key]),
    }));

  if (!data.length) {
    return <p className="ref-empty-inline">No completed checks yet — legitimacy will appear as results come in.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="rgba(38,58,67,.08)" strokeDasharray="4 5" />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "#8b969b" }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: "#3b4b51" }} axisLine={false} tickLine={false} />
        <Tooltip
          cursor={{ fill: "rgba(85,174,181,.06)" }}
          contentStyle={{ borderRadius: 10, border: "1px solid #d9e3e5", boxShadow: "0 8px 24px rgba(35,55,61,.10)" }}
          formatter={(value) => [`${value}/100`, "Legitimacy"]}
        />
        <Bar dataKey="value" radius={[0, 6, 6, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={legitColor(entry.value)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Rolls the per-source legitimacy scores + flags up into one row per
// category (reputation / infrastructure / content), so the shape of the
// result -- not just its total -- is visible at a glance.
function buildCategoryData(sources, orderedKeys) {
  const buckets = {};
  CATEGORY_ORDER.forEach((cat) => {
    buckets[cat] = { total: 0, done: 0, flagged: 0, legitSum: 0 };
  });

  orderedKeys.forEach((key) => {
    const cat = SOURCE_CATEGORY[key];
    if (!cat || !buckets[cat]) return;
    const bucket = buckets[cat];
    bucket.total += 1;

    const result = sources[key];
    if (!result) return;
    bucket.done += 1;
    if (isFlagged(result)) bucket.flagged += 1;
    const legit = legitimacyScore(result);
    if (legit !== null) bucket.legitSum += legit;
  });

  return CATEGORY_ORDER.map((cat) => {
    const bucket = buckets[cat];
    const avg = bucket.done > 0 ? Math.round(bucket.legitSum / bucket.done) : 0;
    return {
      key: cat,
      name: CATEGORY_LABELS[cat],
      value: avg,
      flagged: bucket.flagged,
      total: bucket.total,
      done: bucket.done,
    };
  });
}

function CategoryLegitimacyChart({ sources, orderedKeys }) {
  const data = buildCategoryData(sources, orderedKeys);
  const anyDone = data.some((d) => d.done > 0);

  return (
    <div className="ref-category-panel">
      <div className="ref-category-chart-wrap">
        {anyDone ? (
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={data} outerRadius="72%">
              <PolarGrid stroke="rgba(38,58,67,.14)" />
              <PolarAngleAxis dataKey="name" tick={{ fontSize: 10.5, fill: "#3b4b51" }} />
              <PolarRadiusAxis
                domain={[0, 100]}
                tick={{ fontSize: 9, fill: "#8b969b" }}
                axisLine={false}
                tickCount={3}
              />
              <Radar
                dataKey="value"
                stroke="#3f8267"
                fill="#56a98a"
                fillOpacity={0.4}
                isAnimationActive={false}
              />
            </RadarChart>
          </ResponsiveContainer>
        ) : (
          <p className="ref-empty-inline">Legitimacy by category will fill in as checks complete.</p>
        )}
      </div>

      <div className="ref-category-list">
        {data.map((cat) => (
          <div className="ref-category-card" key={cat.key}>
            <div className="ref-category-card-head">
              <span>{cat.name}</span>
              <b>{cat.done}/{cat.total} checked</b>
            </div>
            <div className="ref-category-bar">
              <div
                className="ref-category-bar-fill"
                style={{ width: `${cat.value}%`, background: legitColor(cat.value) }}
              />
            </div>
            <div className="ref-category-card-foot">
              <span>{cat.value}/100 legitimacy</span>
              {cat.flagged > 0 ? (
                <span className="ref-category-flag-note">{cat.flagged} flagged</span>
              ) : (
                <span className="ref-category-clean-note">All clear</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DeepAnalysisReportPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const initial = location.state || null;

  const [url] = useState(initial?.url || "");
  const [entry, setEntry] = useState(initial?.entry || null);
  const closeStream = useRef(null);

  const runFull = useCallback(() => {
    if (!url) return;
    closeStream.current?.();
    setEntry({ status: "loading", sources: {} });

    closeStream.current = streamAnalyzeLink(url, {
      onSource: (payload) => {
        const { key: sourceKey, ...result } = payload;
        setEntry((prev) =>
          prev && prev.status === "loading"
            ? { ...prev, sources: { ...prev.sources, [sourceKey]: result } }
            : prev
        );
      },
      onDone: (payload) => {
        setEntry({
          status: "done",
          data: { explanation: payload.explanation, result: payload },
          sources: payload.sources,
        });
      },
      onError: (message) => {
        setEntry({ status: "error", error: message });
      },
    });
  }, [url]);

  // If we arrived with a snapshot still mid-stream (the card it was opened
  // from is gone now), or with no snapshot at all, start/continue a fresh
  // run of our own so this page keeps updating independently.
  useEffect(() => {
    if (url && (!initial?.entry || initial.entry.status === "loading")) {
      runFull();
    }
    return () => closeStream.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  if (!url) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <header className="reference-page-head">
            <h1>
              Deep <span>Analysis Report</span>
            </h1>
          </header>

          <section className="ref-panel ref-analysis-empty">
            <BrainCircuit size={30} strokeWidth={1.6} />
            <h3>No report open</h3>
            <p>Open this page from a link's "Full report" button on the AI Deep Analysis page.</p>
            <button type="button" className="ref-empty-cta" onClick={() => navigate("/analyze")}>
              Go to AI Deep Analysis
            </button>
          </section>
        </div>
      </main>
    );
  }

  const sources = entry?.sources || {};
  const extraKeys = Object.keys(sources).filter((k) => !SOURCE_ORDER.includes(k));
  const orderedKeys = [...SOURCE_ORDER, ...extraKeys];
  const totalDone = Object.keys(sources).length;

  const verdict = entry?.status === "done" ? entry.data?.result?.verdict : null;
  const explanation = entry?.status === "done" ? entry.data?.explanation : null;
  const flaggedCount = orderedKeys.filter((k) => isFlagged(sources[k]) === true).length;
  const cleanCount = orderedKeys.filter((k) => isFlagged(sources[k]) === false).length;
  const unavailableCount = orderedKeys.filter((k) => isFlagged(sources[k]) === null).length;

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head ref-report-head">
          <div className="ref-report-head-left">
            <button type="button" className="ref-report-back" onClick={() => navigate(-1)} title="Back">
              <ArrowLeft size={18} />
            </button>
            <div>
              <h1 className="ref-report-title">
                Deep <span>Analysis Report</span>
              </h1>
              <div className="ref-report-target">
                <Link2 size={13} />
                <span title={url}>{url}</span>
              </div>
            </div>
          </div>

          <div className="reference-head-actions">
            <button
              type="button"
              className="ref-report-preview-btn"
              onClick={() => navigate("/deep-analysis/source", { state: { url } })}
              title="Fetch this page's HTML and preview how it looks"
            >
              <Eye size={14} />
              Preview page
            </button>

            <button
              type="button"
              className="ref-report-refresh"
              onClick={runFull}
              disabled={entry?.status === "loading"}
            >
              {entry?.status === "loading" ? (
                <LoaderCircle size={14} className="ref-deep-spin" />
              ) : (
                <RefreshCcw size={14} />
              )}
              {entry?.status === "loading" ? "Analyzing…" : "Re-run analysis"}
            </button>
          </div>
        </header>

        {entry?.status === "error" ? (
          <section className="ref-panel ref-deep-panel is-error" style={{ margin: "0 0 18px" }}>
            <XCircle size={16} />
            <span>{entry.error}</span>
            <button type="button" onClick={runFull}>Retry</button>
          </section>
        ) : (
          <>
            <section className="ref-verdict-banner ref-report-verdict" data-severity={verdict ? severityFromRiskLevel(verdict.risk_level) : undefined}>
              <div className="ref-verdict-gauge">
                <RiskGauge value={verdict ? verdict.risk_score : 0} caption="Risk score" />
              </div>

              <div className="ref-verdict-copy">
                <div className="ref-verdict-eyebrow">
                  <BrainCircuit size={13} />
                  {totalDone} of {SOURCE_ORDER.length} checks complete
                </div>

                <h2>
                  {verdict
                    ? riskMeta(verdict.risk_level).label
                    : entry?.status === "loading"
                    ? "Analyzing this link…"
                    : "Awaiting results"}
                </h2>

                {verdict && verdict.flags?.length > 0 && (
                  <div className="ref-report-flag-row">
                    {verdict.flags.map((flag, i) => (
                      <span className="ref-report-flag-chip" key={i}>{flag}</span>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className={`ref-ai-summary ${verdict ? severityFromRiskLevel(verdict.risk_level) ? `is-${severityFromRiskLevel(verdict.risk_level)}` : "" : ""}`}>
              <div className="ref-ai-summary-icon">
                <BrainCircuit size={17} />
              </div>
              <div className="ref-ai-summary-body">
                <div className="ref-ai-summary-eyebrow">
                  <span>AI summary</span>
                  {verdict && <span className="ref-ai-summary-score">{verdict.risk_score}/100 risk</span>}
                </div>

                {explanation ? (
                  <p className="ref-ai-summary-text">{explanation}</p>
                ) : (
                  <p className="ref-ai-summary-text ref-ai-summary-text-muted">
                    <LoaderCircle size={12} className={entry?.status === "loading" ? "ref-deep-spin" : ""} />
                    {entry?.status === "loading"
                      ? "The model will summarize what these checks found as soon as every check is in."
                      : "Every authentication, reputation, and infrastructure check we run against this link will appear below as it finishes."}
                  </p>
                )}
              </div>
            </section>

            <div className="ref-parse-stats" style={{ margin: "0 0 18px" }}>
              <DashboardStat icon={ShieldAlert} label="Flagged sources" value={flaggedCount} />
              <DashboardStat icon={ShieldCheck} label="Clean sources" value={cleanCount} />
              <DashboardStat icon={XCircle} label="Unavailable" value={unavailableCount} />
              <DashboardStat icon={Link2} label="Total checks" value={SOURCE_ORDER.length} />
            </div>

            <div className="ref-grid-two">
              <DashboardPanel title="Source verdicts">
                <SourceVerdictDonut sources={sources} orderedKeys={orderedKeys} />
              </DashboardPanel>

              <DashboardPanel title="Legitimacy score by source">
                <LegitimacyChart sources={sources} orderedKeys={orderedKeys} />
              </DashboardPanel>
            </div>

            <DashboardPanel
              title="Legitimacy by category"
              right={<span className="ref-panel-number">{CATEGORY_ORDER.length}</span>}
              className="ref-category-full-panel"
            >
              <CategoryLegitimacyChart sources={sources} orderedKeys={orderedKeys} />
            </DashboardPanel>

            <DashboardPanel title="Every check, in full" right={<span className="ref-panel-number">{orderedKeys.length}</span>}>
              <div className="ref-report-source-grid">
                {orderedKeys.map((key) => (
                  <SourceReportCard key={key} sourceKey={key} result={sources[key]} />
                ))}
              </div>
            </DashboardPanel>
          </>
        )}
      </div>
    </main>
  );
}
