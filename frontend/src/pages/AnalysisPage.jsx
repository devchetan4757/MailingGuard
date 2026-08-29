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
  CheckCircle2,
  XCircle,
  ArrowRight,
  Download,
  Sparkles,
} from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel, RiskGauge } from "../components/dashboard/DashboardWidgets";
import AiBadge from "../components/dashboard/AiBadge";
import EmailParsingPanel from "../components/dashboard/EmailParsingPanel";
import { getCaseReportUrl } from "../api/casesApi";

const CHECK_META = {
  spf: {
    label: "SPF",
    desc: "Confirms the sending server was allowed to send on this domain's behalf.",
  },
  dkim: {
    label: "DKIM",
    desc: "Confirms the message wasn't altered in transit.",
  },
  dmarc: {
    label: "DMARC",
    desc: "Confirms the domain publishes a policy for handling failed checks.",
  },
};

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
              breakdown here — authentication checks, origin trace, and every
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
  const hc = currentCase.headerChecks || {};
  const origin = currentCase.origin || {};
  const checkKeys = ["spf", "dkim", "dmarc"];

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
          <DashboardPanel title="Authentication checks">
            <div className="ref-checklist">
              {checkKeys.map((key) => {
                const rawValue = hc[key];
                const value = rawValue === "pass" || rawValue === "fail" ? rawValue : "unknown";
                const failed = value === "fail";
                const passed = value === "pass";

                return (
                  <div className="ref-check-row" key={key}>
                    <div className={`ref-check-status ${failed ? "is-fail" : passed ? "is-pass" : "is-unknown"}`}>
                      {failed ? <XCircle size={16} /> : passed ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                      {CHECK_META[key].label}
                      <span>{value === "unknown" ? "not checked" : value}</span>
                    </div>
                    <p>{CHECK_META[key].desc}</p>
                  </div>
                );
              })}

              {hc.senderDomainMismatch && (
                <div className="ref-check-flag">
                  <AlertTriangle size={14} />
                  Sender display name doesn't match the reply-to domain.
                </div>
              )}
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

        <EmailParsingPanel currentCase={currentCase} />

        <DashboardPanel title="AI signals" right={<AiBadge label={`${signals.length} found`} />}>
          <ul className="ref-signal-list">
            {signals.map((signal, index) => (
              <li key={index} className={`ref-signal-item level-${signal.level}`}>
                {signal.level === "low" ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}
                <span>{signal.text}</span>
              </li>
            ))}
          </ul>
        </DashboardPanel>

        <div className="ref-analysis-actions">
          <a href={getCaseReportUrl(currentCase.caseId)} download className="ref-download-btn">
            <Download size={16} />
            Download full report (PDF)
          </a>
        </div>
      </div>
    </main>
  );
}
