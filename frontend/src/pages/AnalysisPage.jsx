// src/pages/AnalysisPage.jsx
/**
 * Second interface. Upload/parsing lives on its own "Upload & Parse" page,
 * so this page has no upload box and no case list — it's a single-email AI
 * deep-dive for whatever case is currently loaded in CaseContext.
 */

import { useNavigate } from "react-router-dom";
import {
  BrainCircuit,
  ShieldCheck,
  ShieldAlert,
  MapPin,
  Globe2,
  AlertTriangle,
  ArrowRight,
  FileDown,
  Sparkles,
  Link2,
  Paperclip,
  Search,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel, DashboardStat, RiskGauge } from "../components/dashboard/DashboardWidgets";
import AiBadge from "../components/dashboard/AiBadge";
import EmailParsingPanel from "../components/dashboard/EmailParsingPanel";

// Extensions the backend can actually run a deep scan against (mirrors
// backend/app/api/deep_analysis.py's ALLOWED_PDF_EXTENSIONS /
// ALLOWED_IMAGE_EXTENSIONS) — used here purely to show how much of what
// came in on this email is eligible for a deep scan.
const SCANNABLE_EXTENSIONS = new Set([
  ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp", ".webp", ".heic",
]);

function attachmentExtension(item) {
  if (item.extension) return item.extension.toLowerCase();
  const name = item.filename || "";
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot).toLowerCase();
}

const VERDICT_COPY = {
  red: "High-confidence phishing indicators were found. Treat this email as malicious — don't click links, open attachments, or reply.",
  yellow: "Some indicators are inconclusive. We recommend a manual review before taking any action on this email.",
  green: "No strong indicators of phishing or fraud were found. This email looks safe, but stay alert for anything unusual.",
};

const SEVERITY_LABEL = {
  red: "High risk",
  yellow: "Medium risk",
  green: "Low risk",
};

function buildSignals(currentCase) {
  const hc = currentCase.headerChecks || {};
  const origin = currentCase.origin || {};
  const signals = [];

  if (hc.spf === "fail") {
    signals.push({ level: "high", text: "SPF check failed — the sending server wasn't authorized for this domain." });
  }
  if (hc.dkim === "fail") {
    signals.push({ level: "high", text: "DKIM check failed — message content may have been altered in transit." });
  }
  if (hc.dmarc === "fail") {
    signals.push({ level: "medium", text: "DMARC check failed — the domain doesn't enforce a policy for failed auth." });
  }
  if (hc.senderDomainMismatch) {
    signals.push({ level: "high", text: "Sender display name doesn't match the reply-to domain." });
  }
  if (origin.isVpnOrHosting) {
    signals.push({ level: "medium", text: "Origin IP resolves to a hosting/VPN provider, not a normal residential or corporate network." });
  }

  if (!signals.length) {
    signals.push({ level: "low", text: "No major authentication or origin anomalies were detected." });
  }

  return signals;
}

// Everything this email surfaced that a deep scan can actually be run
// against — links, and attachments whose type the PDF/image analyzers
// support — shown as one small "what can we dig into" visual instead of
// a bare list, so the AI Deep Analysis page opens with something worth
// looking at even before any individual scan has been run.
function buildScanCoverage(currentCase) {
  const analysis = currentCase.analysis || {};
  const urls = analysis.urls || [];
  const attachments = analysis.attachments || [];

  const scannableAttachments = attachments.filter((a) => SCANNABLE_EXTENSIONS.has(attachmentExtension(a)));
  const otherAttachments = attachments.length - scannableAttachments.length;
  const suspiciousAttachments = attachments.filter((a) => a.suspicious).length;
  const headerFindings = (analysis.header_findings || []).length;

  const data = [
    { name: "Links", value: urls.length, color: "#5b8dee" },
    { name: "Scannable attachments", value: scannableAttachments.length, color: "#56a98a" },
    { name: "Other attachments", value: otherAttachments, color: "#cbd5d8" },
  ].filter((item) => item.value > 0);

  const total = urls.length + attachments.length;

  return { data, total, urlCount: urls.length, attachmentCount: attachments.length, scannableCount: scannableAttachments.length, suspiciousAttachments, headerFindings };
}

function ScanCoverageDonut({ data, total }) {
  if (!total) {
    return <p className="ref-empty-inline">No links or attachments were extracted from this email.</p>;
  }

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
          <strong>{total}</strong>
          <span>deep-scannable</span>
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

export default function AnalysisPage() {
  const navigate = useNavigate();
  const { currentCase } = useCaseContext();

  if (!currentCase) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <header className="reference-page-head">
            <h1>
              AI <span>Deep Analysis</span>
            </h1>
          </header>

          <section className="ref-panel ref-analysis-empty">
            <BrainCircuit size={30} strokeWidth={1.6} />
            <h3>No email analyzed yet</h3>
            <p>
              Upload an email on the Upload &amp; Parse page to get a full AI
              breakdown here — origin trace, deep-scannable content, and every
              signal we found.
            </p>
            <button type="button" className="ref-empty-cta" onClick={() => navigate("/upload")}>
              Go to Upload &amp; Parse
              <ArrowRight size={16} />
            </button>
          </section>
        </div>
      </main>
    );
  }

  const signals = buildSignals(currentCase);
  const origin = currentCase.origin || {};
  const coverage = buildScanCoverage(currentCase);

  const highCount = signals.filter((s) => s.level === "high").length;
  const mediumCount = signals.filter((s) => s.level === "medium").length;
  const lowCount = signals.filter((s) => s.level === "low").length;

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head">
          <h1>
            AI <span>Deep Analysis</span>
          </h1>

          <div className="reference-head-actions">
            <AiBadge label="AI analyzed" />
          </div>
        </header>

        <section className="ref-verdict-banner" data-severity={currentCase.severity}>
          <div className="ref-verdict-gauge">
            <RiskGauge value={currentCase.riskScore} />
          </div>

          <div className="ref-verdict-copy">
            <div className="ref-verdict-eyebrow">
              <Sparkles size={13} />
              CASE #{currentCase.caseId}
            </div>

            <h2>{SEVERITY_LABEL[currentCase.severity] || "Risk assessment"}</h2>

            <p>{VERDICT_COPY[currentCase.severity] || VERDICT_COPY.yellow}</p>
          </div>
        </section>

        <div className="ref-grid-two">
          <DashboardPanel
            title="Deep-scannable content"
            right={<span className="ref-panel-number">{coverage.total}</span>}
          >
            <ScanCoverageDonut data={coverage.data} total={coverage.total} />
            <div className="ref-parse-stats ref-scan-coverage-stats">
              <DashboardStat icon={Link2} label="Links found" value={coverage.urlCount} />
              <DashboardStat icon={Paperclip} label="Attachments" value={coverage.attachmentCount} />
              <DashboardStat icon={Search} label="Scannable" value={coverage.scannableCount} />
              <DashboardStat icon={AlertTriangle} label="Flagged" value={coverage.suspiciousAttachments} />
            </div>
          </DashboardPanel>

          <DashboardPanel title="Origin trace">
            <div className="ref-origin-card">
              <div className="ref-origin-pin">
                <MapPin size={18} />
              </div>

              <div className="ref-origin-copy">
                <strong>{origin.ip || "Unknown IP"}</strong>
                <p>{origin.city ? `${origin.city}, ${origin.country}` : "Location unavailable"}</p>
              </div>

              {origin.isVpnOrHosting && (
                <span className="ref-origin-flag">
                  <Globe2 size={13} />
                  Hosting / VPN
                </span>
              )}
            </div>
          </DashboardPanel>
        </div>

        <EmailParsingPanel currentCase={currentCase} variant="minimal" />

        <DashboardPanel
          title="AI signals"
          right={<AiBadge label={`${signals.length} found`} />}
        >
          <div className="ref-signal-summary">
            <span className="ref-signal-count is-high"><b>{highCount}</b> high</span>
            <span className="ref-signal-count is-medium"><b>{mediumCount}</b> medium</span>
            <span className="ref-signal-count is-low"><b>{lowCount}</b> low</span>
          </div>

          <ul className="ref-signal-list">
            {signals.map((signal, index) => (
              <li key={index} className={`ref-signal-item level-${signal.level}`}>
                <span className="ref-signal-icon">
                  {signal.level === "low" ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}
                </span>
                <span className="ref-signal-text">{signal.text}</span>
                <span className={`ref-signal-badge level-${signal.level}`}>{signal.level}</span>
              </li>
            ))}
          </ul>
        </DashboardPanel>

        <div className="ref-analysis-actions">
          <button type="button" className="ref-download-btn" onClick={() => navigate("/reports")}>
            <FileDown size={16} />
            Preview &amp; download full report
          </button>
        </div>
      </div>
    </main>
  );
}
