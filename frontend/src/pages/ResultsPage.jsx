// src/pages/ResultsPage.jsx
/**
 * Full case report: risk score, auth checks, origin, related cases,
 * download. Rebuilt to use the same reference-* design system as
 * AnalysisPage / OriginAnalysisPage / ReportsPage — the old version
 * leaned on Tailwind utility classes (text-flagged, border-graphite/15,
 * etc.) that were never defined anywhere, so it rendered with no
 * styling at all.
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FileSearch,
  ArrowRight,
  ArrowLeft,
  Download,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldAlert,
  X,
} from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel, RiskGauge } from "../components/dashboard/DashboardWidgets";
import { getCaseReportUrl } from "../api/casesApi";
import TraceMap from "../components/results/TraceMap";

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

const SEVERITY_LABEL = {
  red: "High risk",
  yellow: "Medium risk",
  green: "Low risk",
};

export default function ResultsPage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { currentCase } = useCaseContext();
  const [openRelatedCaseId, setOpenRelatedCaseId] = useState(null);

  // TODO (integrator): if currentCase is null (e.g. page was opened via a
  // direct link), fetch it with casesApi.getCase(caseId) instead of bouncing
  // the user back to the dashboard.
  if (!currentCase) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <header className="reference-page-head">
            <h1>
              Case <span>#{caseId}</span>
            </h1>
          </header>

          <section className="ref-panel ref-analysis-empty">
            <FileSearch size={30} strokeWidth={1.6} />
            <h3>Case not loaded</h3>
            <p>Open this case from the dashboard or history list to see its full report.</p>
            <button type="button" className="ref-empty-cta" onClick={() => navigate("/")}>
              Go to Dashboard
              <ArrowRight size={16} />
            </button>
          </section>
        </div>
      </main>
    );
  }

  const hc = currentCase.headerChecks || {};
  const origin = currentCase.origin || {};
  const related = currentCase.relatedCases || [];
  const checkKeys = ["spf", "dkim", "dmarc"];

  const threatIntel = currentCase.threatIntel || null;
  const tiVerdict = threatIntel?.overallVerdict || threatIntel?.verdict || "unknown";
  const tiSignals = threatIntel?.signals || threatIntel || {};

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head">
          <h1>
            Case <span>#{currentCase.caseId}</span>
          </h1>

          <div className="reference-head-actions">
            <button type="button" className="ref-icon-button" aria-label="Back" onClick={() => navigate(-1)}>
              <ArrowLeft size={17} />
            </button>
          </div>
        </header>

        <section className="ref-verdict-banner" data-severity={currentCase.severity}>
          <div className="ref-verdict-gauge">
            <RiskGauge value={currentCase.riskScore} />
          </div>

          <div className="ref-verdict-copy">
            <div className="ref-verdict-eyebrow">
              <FileSearch size={13} />
              CASE REPORT
            </div>

            <h2>{SEVERITY_LABEL[currentCase.severity] || "Risk assessment"}</h2>

            <p>Full breakdown of this case's authentication checks, origin, and related activity.</p>
          </div>
        </section>

        <div className="ref-grid-two">
          <DashboardPanel title="Authentication checks">
            <div className="ref-checklist">
              {checkKeys.map((key) => {
                const value = hc[key];
                const failed = value === "fail";

                return (
                  <div className="ref-check-row" key={key}>
                    <div className={`ref-check-status ${failed ? "is-fail" : "is-pass"}`}>
                      {failed ? <XCircle size={16} /> : <CheckCircle2 size={16} />}
                      {CHECK_META[key].label}
                      <span>{value || "n/a"}</span>
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

          <DashboardPanel title="Origin">
            <TraceMap origin={origin} compact />
          </DashboardPanel>
        </div>

        <DashboardPanel
          title="Related cases"
          right={<span className="ref-panel-number">{related.length}</span>}
        >
          {related.length === 0 ? (
            <p className="ref-empty-inline">
              No related cases yet — this is the first time we've seen anything like this sender or content.
            </p>
          ) : (
            <div className="ref-related-list">
              {related.map((rc) => (
                <div className="ref-related-row" key={rc.caseId}>
                  <div>
                    <strong>#{rc.caseId}</strong>
                    <span>
                      {rc.similarity} similarity · {(rc.matchedOn || []).join(", ")}
                    </span>
                  </div>
                  <button type="button" onClick={() => setOpenRelatedCaseId(rc.caseId)}>
                    View
                    <ArrowRight size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </DashboardPanel>

        <div className="ref-analysis-actions">
          <a href={getCaseReportUrl(currentCase.caseId)} download className="ref-download-btn">
            <Download size={16} />
            Download case file (PDF)
          </a>
        </div>
      </div>

      {openRelatedCaseId && (
        <div className="ref-modal-overlay" onClick={() => setOpenRelatedCaseId(null)}>
          <div className="ref-modal-card" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="ref-modal-close"
              aria-label="Close"
              onClick={() => setOpenRelatedCaseId(null)}
            >
              <X size={16} />
            </button>

            <span className="ref-origin-eyebrow-tag">CASE #{openRelatedCaseId}</span>
            <h3>Related case summary</h3>
            {/* TODO (integrator): fetch this case via casesApi.getCase(caseId)
                and render its real summary here. */}
            <p>Full summary for this case isn't wired up yet.</p>
          </div>
        </div>
      )}
    </main>
  );
}
