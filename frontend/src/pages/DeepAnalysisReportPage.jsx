// src/pages/DeepAnalysisReportPage.jsx
/**
 * Full-page Deep Analysis report.
 *
 * This page supports both:
 *   1. URL reports opened from an extracted-link result.
 *   2. Attachment reports opened from a PDF/image attachment result.
 *
 * PDF reports use the real /deep-analysis/case/{case_id}/attachment/{index}
 * response and render the PDF analyzer's returned fields directly.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Eye,
  FileText,
  Image as ImageIcon,
  Link2,
  LoaderCircle,
  Paperclip,
  QrCode,
  RefreshCcw,
  Search,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
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
import { analyzeCaseAttachment, streamAnalyzeLink } from "../api/deepAnalysisApi";

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
  if (Array.isArray(result.vulnerabilities)) return Math.min(100, result.vulnerabilities.length * 10);
  if (Array.isArray(result.detections)) return Math.min(100, result.detections.length * 10);
  if (typeof result.malicious === "number") return Math.min(100, result.malicious * 10);
  if (typeof result.registered_lookalike_count === "number") return Math.min(100, result.registered_lookalike_count * 10);
  return isFlagged(result) ? 100 : 0;
}

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

function chipPreview(item) {
  if (item === null || item === undefined) return "—";
  if (isPrimitive(item)) return truncateText(item, 34);
  const entries = Object.entries(item).filter(([, value]) => isPrimitive(value) && value !== "" && value !== null);
  if (!entries.length) return "…";
  return truncateText(entries[0][1], 34);
}

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
          {preview.map((item, index) => (
            <span className="ref-report-chip" key={index}>{chipPreview(item)}</span>
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
    <div className={`ref-report-source-card ${pending ? "is-pending" : ""} ${flagged ? "is-flagged" : ""} ${flagged === false ? "is-clean" : ""}`}>
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

      {result?.error && <p className="ref-report-error-detail">{String(result.error)}</p>}

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
              <button type="button" className="ref-deep-raw-toggle" onClick={() => setDetailsOpen((open) => !open)}>
                <ChevronDown size={12} style={{ transform: detailsOpen ? "rotate(180deg)" : "none" }} />
                {detailsOpen ? "Hide" : "Show"} {details.length} more detail{details.length === 1 ? "" : "s"}
              </button>
              {detailsOpen && (
                <div className="ref-report-detail-list">
                  {details.map(([key, value]) => <DetailRow key={key} fieldKey={key} value={value} />)}
                </div>
              )}
            </>
          )}

          <button type="button" className="ref-deep-raw-toggle ref-deep-raw-toggle-muted" onClick={() => setRawOpen((open) => !open)}>
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
  ].filter((item) => item.value > 0);

  return (
    <div className="ref-report-donut">
      <div className="ref-report-donut-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="68%" outerRadius="94%" paddingAngle={3} stroke="none">
              {data.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="ref-report-donut-center">
          <strong>{clean + flagged + skipped}</strong>
          <span>of {orderedKeys.length} checks</span>
        </div>
      </div>
      <div className="ref-report-donut-legend">
        {data.map((item) => (
          <div className="ref-report-donut-legend-row" key={item.name}>
            <i style={{ background: item.color }} />
            <span>{item.name}</span>
            <b>{item.value}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

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
    .map((key) => ({ name: SOURCE_LABELS[key] || key.replaceAll("_", " "), value: legitimacyScore(sources[key]) }));

  if (!data.length) return <p className="ref-empty-inline">No completed checks yet — legitimacy will appear as results come in.</p>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="rgba(38,58,67,.08)" strokeDasharray="4 5" />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "#8b969b" }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: "#3b4b51" }} axisLine={false} tickLine={false} />
        <Tooltip cursor={{ fill: "rgba(85,174,181,.06)" }} contentStyle={{ borderRadius: 10, border: "1px solid #d9e3e5", boxShadow: "0 8px 24px rgba(35,55,61,.10)" }} formatter={(value) => [`${value}/100`, "Legitimacy"]} />
        <Bar dataKey="value" radius={[0, 6, 6, 0]}>
          {data.map((item, index) => <Cell key={index} fill={legitColor(item.value)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function buildCategoryData(sources, orderedKeys) {
  const buckets = {};
  CATEGORY_ORDER.forEach((category) => {
    buckets[category] = { total: 0, done: 0, flagged: 0, legitSum: 0 };
  });

  orderedKeys.forEach((key) => {
    const category = SOURCE_CATEGORY[key];
    if (!category || !buckets[category]) return;
    const bucket = buckets[category];
    bucket.total += 1;
    const result = sources[key];
    if (!result) return;
    bucket.done += 1;
    if (isFlagged(result)) bucket.flagged += 1;
    const legit = legitimacyScore(result);
    if (legit !== null) bucket.legitSum += legit;
  });

  return CATEGORY_ORDER.map((category) => {
    const bucket = buckets[category];
    const avg = bucket.done > 0 ? Math.round(bucket.legitSum / bucket.done) : 0;
    return { key: category, name: CATEGORY_LABELS[category], value: avg, flagged: bucket.flagged, total: bucket.total, done: bucket.done };
  });
}

function CategoryLegitimacyChart({ sources, orderedKeys }) {
  const data = buildCategoryData(sources, orderedKeys);
  const anyDone = data.some((item) => item.done > 0);

  return (
    <div className="ref-category-panel">
      <div className="ref-category-chart-wrap">
        {anyDone ? (
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={data} outerRadius="72%">
              <PolarGrid stroke="rgba(38,58,67,.14)" />
              <PolarAngleAxis dataKey="name" tick={{ fontSize: 10.5, fill: "#3b4b51" }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#8b969b" }} axisLine={false} tickCount={3} />
              <Radar dataKey="value" stroke="#3f8267" fill="#56a98a" fillOpacity={0.4} isAnimationActive={false} />
            </RadarChart>
          </ResponsiveContainer>
        ) : (
          <p className="ref-empty-inline">Legitimacy by category will fill in as checks complete.</p>
        )}
      </div>
      <div className="ref-category-list">
        {data.map((category) => (
          <div className="ref-category-card" key={category.key}>
            <div className="ref-category-card-head"><span>{category.name}</span><b>{category.done}/{category.total} checked</b></div>
            <div className="ref-category-bar"><div className="ref-category-bar-fill" style={{ width: `${category.value}%`, background: legitColor(category.value) }} /></div>
            <div className="ref-category-card-foot">
              <span>{category.value}/100 legitimacy</span>
              {category.flagged > 0 ? <span className="ref-category-flag-note">{category.flagged} flagged</span> : <span className="ref-category-clean-note">All clear</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function pdfCount(value) {
  return Array.isArray(value) ? value.length : Number(value || 0);
}

function pdfRiskLabel(summary) {
  if (!summary) return null;
  return summary.status || summary.verdict || null;
}

function pdfRiskSeverity(summary) {
  const status = String(pdfRiskLabel(summary) || "").toLowerCase();
  if (status.includes("high") || status.includes("critical") || Number(summary?.indicator_score) >= 8) return "red";
  if (status.includes("medium") || Number(summary?.indicator_score) >= 4) return "yellow";
  if (status.includes("low") || Number(summary?.indicator_score) < 4) return "green";
  return undefined;
}

function PdfMetric({ label, value, danger = false }) {
  return (
    <div className={`ref-pdf-metric ${danger ? "is-danger" : ""}`}>
      <span>{label}</span>
      <strong>{formatPrimitive(value)}</strong>
    </div>
  );
}

function PdfObjectList({ title, icon: Icon = FileText, items, empty = "Nothing detected." }) {
  const [open, setOpen] = useState(false);
  if (!Array.isArray(items) || items.length === 0) {
    return (
      <div className="ref-pdf-section-card">
        <div className="ref-pdf-section-head"><Icon size={15} /><strong>{title}</strong><span>0</span></div>
        <p className="ref-pdf-empty">{empty}</p>
      </div>
    );
  }

  return (
    <div className="ref-pdf-section-card">
      <button type="button" className="ref-pdf-section-head ref-pdf-section-button" onClick={() => setOpen((value) => !value)}>
        <Icon size={15} /><strong>{title}</strong><span>{items.length}</span><ChevronDown size={14} style={{ transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      <div className="ref-pdf-item-preview">
        {items.slice(0, open ? items.length : 4).map((item, index) => (
          <div className="ref-pdf-item" key={index}>
            <div className="ref-pdf-item-index">{index + 1}</div>
            <pre>{typeof item === "string" ? item : JSON.stringify(item, null, 2)}</pre>
          </div>
        ))}
        {!open && items.length > 4 && <button type="button" className="ref-deep-raw-toggle" onClick={() => setOpen(true)}>Show all {items.length}</button>}
      </div>
    </div>
  );
}

function PdfUrlList({ urls }) {
  const [open, setOpen] = useState(false);
  const items = Array.isArray(urls) ? urls : [];

  if (items.length === 0) {
    return (
      <div className="ref-pdf-section-card">
        <div className="ref-pdf-section-head"><Link2 size={15} /><strong>Extracted URLs</strong><span>0</span></div>
        <p className="ref-pdf-empty">No URLs were extracted from this PDF.</p>
      </div>
    );
  }

  return (
    <div className="ref-pdf-section-card">
      <button type="button" className="ref-pdf-section-head ref-pdf-section-button" onClick={() => setOpen((value) => !value)}>
        <Link2 size={15} /><strong>Extracted URLs</strong><span>{items.length}</span><ChevronDown size={14} style={{ transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      <div className="ref-pdf-url-list">
        {items.slice(0, open ? items.length : 8).map((item, index) => {
          // Backend returns rich objects ({ url, domain, page, source }),
          // but tolerate plain strings too so this never breaks either way.
          const href = typeof item === "string" ? item : item?.url || "";
          const domain = typeof item === "object" ? item?.domain : null;
          const source = typeof item === "object" ? item?.source : null;
          const page = typeof item === "object" ? item?.page : null;

          return (
            <div className="ref-pdf-url-row" key={`${href}-${index}`}>
              <span>{index + 1}</span>
              <div className="ref-pdf-url-main">
                <a href={href} target="_blank" rel="noreferrer">{href || "—"}</a>
                {(domain || source || page != null) && (
                  <div className="ref-pdf-url-meta">
                    {domain && <span className="ref-pdf-url-domain">{domain}</span>}
                    {source && <span className="ref-pdf-url-tag">{source}</span>}
                    {page != null && <span className="ref-pdf-url-page">Page {page}</span>}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {!open && items.length > 8 && <button type="button" className="ref-deep-raw-toggle" onClick={() => setOpen(true)}>Show all {items.length} URLs</button>}
    </div>
  );
}

function PdfImages({ images }) {
  const visible = Array.isArray(images) ? images : [];
  return (
    <div className="ref-pdf-section-card">
      <div className="ref-pdf-section-head"><ImageIcon size={15} /><strong>Embedded images</strong><span>{visible.length}</span></div>
      {visible.length === 0 ? (
        <p className="ref-pdf-empty">No embedded images were detected.</p>
      ) : (
        <div className="ref-pdf-image-grid">
          {visible.map((image, index) => {
            const src = typeof image?.data_uri === "string" ? image.data_uri : typeof image?.data === "string" && image.data.startsWith("data:") ? image.data : null;
            return (
              <div className="ref-pdf-image-card" key={index}>
                {src ? <img src={src} alt={`PDF embedded image ${index + 1}`} /> : <div className="ref-pdf-image-placeholder"><ImageIcon size={24} /></div>}
                <div><strong>Image {image?.id ?? index + 1}</strong><span>Page {formatPrimitive(image?.page)} · {formatPrimitive(image?.width)} × {formatPrimitive(image?.height)}</span></div>
                {image?.contains_qr_code && <em><QrCode size={11} /> QR detected</em>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PdfReport({ report, attachment }) {
  const result = report?.result || report || {};
  const summary = result.summary || {};
  const file = result.file || {};
  const severity = pdfRiskSeverity(summary);
  const indicatorScore = Number(summary.indicator_score || 0);
  const riskValue = Math.min(100, indicatorScore * 10);
  const metadata = result.metadata || {};
  const metadataForensics = result.metadata_forensics || {};
  const reputation = result.reputation || {};
  const structure = result.structure || {};
  const urlAnalysis = result.url_analysis || {};
  const javascript = result.javascript || [];
  const pages = result.pages || [];

  const metadataAnomalies = pdfCount(summary.total_metadata_anomalies ?? metadataForensics.anomalies);
  const structuralAnomalies = pdfCount(summary.total_structural_anomalies ?? structure.anomalies);
  const jsCount = pdfCount(summary.total_javascript_objects ?? javascript);
  const maliciousEngines = Number(summary.virustotal_malicious_engines ?? reputation.malicious_engines ?? 0);

  return (
    <>
      <section className="ref-verdict-banner ref-report-verdict" data-severity={severity}>
        <div className="ref-verdict-gauge">
          <RiskGauge value={riskValue} caption="PDF risk score" />
        </div>
        <div className="ref-verdict-copy">
          <div className="ref-verdict-eyebrow"><FileText size={13} /> PDF attachment analysis</div>
          <h2>{pdfRiskLabel(summary) || "PDF analysis complete"}</h2>
          <div className="ref-report-target ref-pdf-target"><FileText size={13} /><span title={file.name || attachment?.name}>{file.name || attachment?.name || "PDF attachment"}</span></div>
          {indicatorScore > 0 && <div className="ref-report-flag-row"><span className="ref-report-flag-chip">Indicator score: {indicatorScore}/10</span></div>}
        </div>
      </section>

      <section className={`ref-ai-summary ${severity ? `is-${severity}` : ""}`}>
        <div className="ref-ai-summary-icon"><BrainCircuit size={17} /></div>
        <div className="ref-ai-summary-body">
          <div className="ref-ai-summary-eyebrow"><span>PDF analysis summary</span><span className="ref-ai-summary-score">{summary.status || "Complete"}</span></div>
          <p className="ref-ai-summary-text">{report?.explanation || "The PDF was inspected for metadata anomalies, structural issues, risky content, URLs, clickable links, embedded images, QR codes, hidden text, attachments, suspicious features and JavaScript."}</p>
        </div>
      </section>

      <div className="ref-parse-stats" style={{ margin: "0 0 18px" }}>
        <DashboardStat icon={TriangleAlert} label="Risky words" value={summary.total_risky_words ?? pdfCount(result.risky_words)} />
        <DashboardStat icon={Link2} label="URLs" value={summary.total_urls ?? pdfCount(result.urls)} />
        <DashboardStat icon={QrCode} label="QR codes" value={summary.total_qr_codes ?? pdfCount(result.qr_codes)} />
        <DashboardStat icon={ShieldAlert} label="JS objects" value={jsCount} />
      </div>

      <div className="ref-pdf-metric-grid">
        <PdfMetric label="File size" value={file.size_bytes != null ? `${Number(file.size_bytes).toLocaleString()} bytes` : "—"} />
        <PdfMetric label="Pages" value={file.pages ?? pages.length} />
        <PdfMetric label="Images" value={summary.total_images ?? pdfCount(result.images)} />
        <PdfMetric label="Clickable links" value={pdfCount(result.clickable_links)} />
        <PdfMetric label="Hidden text spans" value={summary.total_hidden_text_spans ?? pdfCount(result.hidden_text)} danger={Boolean(summary.hidden_text_high_severity_detected)} />
        <PdfMetric label="Attachments" value={summary.total_attachments ?? pdfCount(result.attachments)} danger={pdfCount(result.attachments) > 0} />
        <PdfMetric label="Structural anomalies" value={structuralAnomalies} danger={Boolean(summary.structural_high_severity_detected)} />
        <PdfMetric label="Metadata anomalies" value={metadataAnomalies} danger={Boolean(summary.metadata_high_severity_detected)} />
        <PdfMetric label="VT malicious engines" value={maliciousEngines} danger={maliciousEngines > 0} />
        <PdfMetric label="Suspicious JS calls" value={summary.total_suspicious_js_calls ?? 0} danger={Number(summary.total_suspicious_js_calls || 0) > 0} />
      </div>

      <div className="ref-grid-two">
        <DashboardPanel title="PDF risk indicators">
          <div className="ref-pdf-indicator-list">
            <div><span>JavaScript CVE trigger</span><b>{summary.javascript_cve_trigger_detected ? "Detected" : "Not detected"}</b></div>
            <div><span>High-severity hidden text</span><b>{summary.hidden_text_high_severity_detected ? "Detected" : "Not detected"}</b></div>
            <div><span>High-severity structural anomaly</span><b>{summary.structural_high_severity_detected ? "Detected" : "Not detected"}</b></div>
            <div><span>High-severity metadata anomaly</span><b>{summary.metadata_high_severity_detected ? "Detected" : "Not detected"}</b></div>
            <div><span>VirusTotal malicious engines</span><b>{maliciousEngines}</b></div>
          </div>
        </DashboardPanel>

        <DashboardPanel title="PDF structure">
          <div className="ref-pdf-kv-list">
            {Object.entries(structure).slice(0, 14).map(([key, value]) => (
              <div key={key}><span>{key.replaceAll("_", " ")}</span><b>{isPrimitive(value) ? formatPrimitive(value) : Array.isArray(value) ? value.length : "Available"}</b></div>
            ))}
            {!Object.keys(structure).length && <p className="ref-pdf-empty">No additional structure fields were returned.</p>}
          </div>
        </DashboardPanel>
      </div>

      <DashboardPanel title="PDF metadata" right={<span className="ref-panel-number">{Object.keys(metadata).length}</span>}>
        <div className="ref-pdf-kv-grid">
          {Object.entries(metadata).map(([key, value]) => (
            <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{isPrimitive(value) ? formatPrimitive(value) : JSON.stringify(value)}</strong></div>
          ))}
        </div>
        {Object.keys(metadataForensics).length > 0 && (
          <div className="ref-pdf-subsection">
            <h4>Metadata forensics</h4>
            <div className="ref-pdf-kv-grid">
              {Object.entries(metadataForensics).map(([key, value]) => (
                <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{isPrimitive(value) ? formatPrimitive(value) : JSON.stringify(value)}</strong></div>
              ))}
            </div>
          </div>
        )}
      </DashboardPanel>

      <div className="ref-grid-two">
        <PdfObjectList title="Risky words" icon={TriangleAlert} items={result.risky_words} empty="No risky words were detected." />
        <PdfObjectList title="Suspicious paragraphs" icon={Search} items={result.suspicious_paragraphs} empty="No suspicious paragraphs were detected." />
      </div>

      <PdfUrlList urls={result.urls} />

      <div className="ref-grid-two">
        <PdfObjectList title="Clickable links" icon={Link2} items={result.clickable_links} empty="No clickable PDF links were detected." />
        <PdfObjectList title="QR codes" icon={QrCode} items={result.qr_codes} empty="No QR/barcode objects were detected." />
      </div>

      <PdfImages images={result.images} />

      <div className="ref-grid-two">
        <PdfObjectList title="Hidden text" icon={Eye} items={result.hidden_text} empty="No hidden text spans were detected." />
        <PdfObjectList title="Embedded attachments" icon={Paperclip} items={result.attachments} empty="No embedded attachments were detected." />
      </div>

      <div className="ref-grid-two">
        <PdfObjectList title="Suspicious PDF features" icon={ShieldAlert} items={result.suspicious_features} empty="No suspicious PDF features were detected." />
        <PdfObjectList title="JavaScript findings" icon={TriangleAlert} items={javascript} empty="No JavaScript objects were detected." />
      </div>

      {pages.length > 0 && (
        <DashboardPanel title="Page-level analysis" right={<span className="ref-panel-number">{pages.length}</span>}>
          <div className="ref-pdf-pages-table">
            {pages.map((page, index) => (
              <div className="ref-pdf-page-row" key={index}>
                <b>Page {page?.page ?? index + 1}</b>
                <span>{formatPrimitive(page?.words)} words</span>
                <span>{formatPrimitive(page?.characters)} characters</span>
              </div>
            ))}
          </div>
        </DashboardPanel>
      )}

      {Object.keys(reputation).length > 0 && (
        <DashboardPanel title="Reputation" right={<span className="ref-panel-number">{Object.keys(reputation).length}</span>}>
          <div className="ref-pdf-kv-grid">
            {Object.entries(reputation).map(([key, value]) => (
              <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{isPrimitive(value) ? formatPrimitive(value) : JSON.stringify(value)}</strong></div>
            ))}
          </div>
        </DashboardPanel>
      )}

      {Object.keys(urlAnalysis).length > 0 && (
        <DashboardPanel title="Extracted URL analysis" right={<span className="ref-panel-number">{Object.keys(urlAnalysis).length}</span>}>
          <div className="ref-pdf-kv-grid">
            {Object.entries(urlAnalysis).map(([key, value]) => (
              <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{isPrimitive(value) ? formatPrimitive(value) : JSON.stringify(value)}</strong></div>
            ))}
          </div>
        </DashboardPanel>
      )}

      <DashboardPanel title="Complete PDF analyzer result">
        <details className="ref-pdf-raw-details">
          <summary>Show raw backend response</summary>
          <pre className="ref-deep-raw-json">{JSON.stringify(result, null, 2)}</pre>
        </details>
      </DashboardPanel>
    </>
  );
}

export default function DeepAnalysisReportPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const initial = location.state || null;
  const isPdf = initial?.type === "pdf" || initial?.attachment?.name?.toLowerCase?.().endsWith(".pdf");
  const [url] = useState(initial?.url || "");
  const [entry, setEntry] = useState(initial?.entry || null);
  const closeStream = useRef(null);

  const runUrl = useCallback(() => {
    if (!url) return;
    closeStream.current?.();
    setEntry({ status: "loading", sources: {} });
    closeStream.current = streamAnalyzeLink(url, {
      onSource: (payload) => {
        const { key: sourceKey, ...result } = payload;
        setEntry((previous) => previous && previous.status === "loading"
          ? { ...previous, sources: { ...previous.sources, [sourceKey]: result } }
          : previous);
      },
      onDone: (payload) => setEntry({ status: "done", data: { explanation: payload.explanation, result: payload }, sources: payload.sources }),
      onError: (message) => setEntry({ status: "error", error: message }),
    });
  }, [url]);

  const runPdf = useCallback(async () => {
    if (!initial?.caseId || initial?.index === undefined || initial?.index === null) {
      setEntry({ status: "error", error: "The PDF report is missing its case ID or attachment index." });
      return;
    }

    closeStream.current?.();
    setEntry({ status: "loading", result: null });

    try {
      const response = await analyzeCaseAttachment(initial.caseId, initial.index);
      setEntry({
        status: "done",
        result: response?.result || {},
        explanation: response?.explanation || "",
        option: response?.option,
      });
    } catch (error) {
      setEntry({ status: "error", error: error?.message || "PDF analysis failed." });
    }
  }, [initial?.caseId, initial?.index]);

  useEffect(() => {
    if (isPdf) {
      if (!initial?.entry || initial.entry.status === "loading") runPdf();
    } else if (url && (!initial?.entry || initial.entry.status === "loading")) {
      runUrl();
    }
    return () => closeStream.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPdf, url]);

  const pdfReport = isPdf && entry?.status === "done" ? entry : null;
  const sources = !isPdf ? entry?.sources || {} : {};
  const extraKeys = Object.keys(sources).filter((key) => !SOURCE_ORDER.includes(key));
  const orderedKeys = [...SOURCE_ORDER, ...extraKeys];
  const totalDone = Object.keys(sources).length;
  const verdict = !isPdf && entry?.status === "done" ? entry.data?.result?.verdict : null;
  const explanation = !isPdf && entry?.status === "done" ? entry.data?.explanation : null;
  const flaggedCount = orderedKeys.filter((key) => isFlagged(sources[key]) === true).length;
  const cleanCount = orderedKeys.filter((key) => isFlagged(sources[key]) === false).length;
  const unavailableCount = orderedKeys.filter((key) => isFlagged(sources[key]) === null).length;

  const titleTarget = useMemo(() => {
    if (!isPdf) return url;
    return entry?.result?.file?.name || initial?.attachment?.name || "PDF attachment";
  }, [isPdf, url, entry?.result?.file?.name, initial?.attachment?.name]);

  if (!isPdf && !url) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <header className="reference-page-head"><h1>Deep <span>Analysis Report</span></h1></header>
          <section className="ref-panel ref-analysis-empty">
            <BrainCircuit size={30} strokeWidth={1.6} />
            <h3>No report open</h3>
            <p>Open this page from a link or attachment's "Full report" button on the analysis page.</p>
            <button type="button" className="ref-empty-cta" onClick={() => navigate("/analyze")}>Go to AI Deep Analysis</button>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head ref-report-head">
          <div className="ref-report-head-left">
            <button type="button" className="ref-report-back" onClick={() => navigate(-1)} title="Back"><ArrowLeft size={18} /></button>
            <div>
              <h1 className="ref-report-title">Deep <span>Analysis Report</span></h1>
              <div className="ref-report-target">
                {isPdf ? <FileText size={13} /> : <Link2 size={13} />}
                <span title={titleTarget}>{titleTarget}</span>
              </div>
            </div>
          </div>

          <div className="reference-head-actions">
            {!isPdf && (
              <button type="button" className="ref-report-preview-btn" onClick={() => navigate("/deep-analysis/source", { state: { url } })} title="Fetch this page's HTML and preview how it looks">
                <Eye size={14} /> Preview page
              </button>
            )}
            <button
              type="button"
              className="ref-report-refresh"
              onClick={isPdf ? runPdf : runUrl}
              disabled={entry?.status === "loading"}
            >
              {entry?.status === "loading" ? <LoaderCircle size={14} className="ref-deep-spin" /> : <RefreshCcw size={14} />}
              {entry?.status === "loading" ? "Analyzing…" : "Re-run analysis"}
            </button>
          </div>
        </header>

        {entry?.status === "error" ? (
          <section className="ref-panel ref-deep-panel is-error" style={{ margin: "0 0 18px" }}>
            <XCircle size={16} />
            <span>{entry.error}</span>
            <button type="button" onClick={isPdf ? runPdf : runUrl}>Retry</button>
          </section>
        ) : isPdf ? (
          entry?.status === "loading" ? (
            <section className="ref-panel ref-pdf-loading">
              <LoaderCircle size={24} className="ref-deep-spin" />
              <div><strong>Analyzing PDF attachment…</strong><span>The backend is inspecting the PDF structure, metadata, content, links and embedded objects.</span></div>
            </section>
          ) : (
            <PdfReport report={pdfReport} attachment={initial?.attachment} />
          )
        ) : (
          <>
            <section className="ref-verdict-banner ref-report-verdict" data-severity={verdict ? severityFromRiskLevel(verdict.risk_level) : undefined}>
              <div className="ref-verdict-gauge"><RiskGauge value={verdict ? verdict.risk_score : 0} caption="Risk score" /></div>
              <div className="ref-verdict-copy">
                <div className="ref-verdict-eyebrow"><BrainCircuit size={13} /> {totalDone} of {SOURCE_ORDER.length} checks complete</div>
                <h2>{verdict ? riskMeta(verdict.risk_level).label : entry?.status === "loading" ? "Analyzing this link…" : "Awaiting results"}</h2>
                {verdict && verdict.flags?.length > 0 && <div className="ref-report-flag-row">{verdict.flags.map((flag, index) => <span className="ref-report-flag-chip" key={index}>{flag}</span>)}</div>}
              </div>
            </section>

            <section className={`ref-ai-summary ${verdict ? severityFromRiskLevel(verdict.risk_level) ? `is-${severityFromRiskLevel(verdict.risk_level)}` : "" : ""}`}>
              <div className="ref-ai-summary-icon"><BrainCircuit size={17} /></div>
              <div className="ref-ai-summary-body">
                <div className="ref-ai-summary-eyebrow"><span>AI summary</span>{verdict && <span className="ref-ai-summary-score">{verdict.risk_score}/100 risk</span>}</div>
                {explanation ? <p className="ref-ai-summary-text">{explanation}</p> : <p className="ref-ai-summary-text ref-ai-summary-text-muted"><LoaderCircle size={12} className={entry?.status === "loading" ? "ref-deep-spin" : ""} />{entry?.status === "loading" ? "The model will summarize what these checks found as soon as every check is in." : "Every authentication, reputation, and infrastructure check will appear below as it finishes."}</p>}
              </div>
            </section>

            <div className="ref-parse-stats" style={{ margin: "0 0 18px" }}>
              <DashboardStat icon={ShieldAlert} label="Flagged sources" value={flaggedCount} />
              <DashboardStat icon={ShieldCheck} label="Clean sources" value={cleanCount} />
              <DashboardStat icon={XCircle} label="Unavailable" value={unavailableCount} />
              <DashboardStat icon={Link2} label="Total checks" value={SOURCE_ORDER.length} />
            </div>

            <div className="ref-grid-two">
              <DashboardPanel title="Source verdicts"><SourceVerdictDonut sources={sources} orderedKeys={orderedKeys} /></DashboardPanel>
              <DashboardPanel title="Legitimacy score by source"><LegitimacyChart sources={sources} orderedKeys={orderedKeys} /></DashboardPanel>
            </div>

            <DashboardPanel title="Legitimacy by category" right={<span className="ref-panel-number">{CATEGORY_ORDER.length}</span>} className="ref-category-full-panel">
              <CategoryLegitimacyChart sources={sources} orderedKeys={orderedKeys} />
            </DashboardPanel>

            <DashboardPanel title="Every check, in full" right={<span className="ref-panel-number">{orderedKeys.length}</span>}>
              <div className="ref-report-source-grid">{orderedKeys.map((key) => <SourceReportCard key={key} sourceKey={key} result={sources[key]} />)}</div>
            </DashboardPanel>
          </>
        )}
      </div>
    </main>
  );
}
