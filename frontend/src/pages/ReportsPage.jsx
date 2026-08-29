// src/pages/ReportsPage.jsx
/**
 * Fourth interface. No case list here — that's what this used to be
 * (see the old HistoryPage). This is just the report for whatever email
 * is currently loaded: what's in it, and a button to download it.
 */

import { useNavigate } from "react-router-dom";
import {
  FileText,
  ArrowRight,
  Download,
  CheckCircle2,
} from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel } from "../components/dashboard/DashboardWidgets";
import { getCaseReportUrl } from "../api/casesApi";

const SEVERITY_LABEL = {
  red: "High risk",
  yellow: "Medium risk",
  green: "Low risk",
};

const INCLUDES = [
  "Fraud risk score",
  "SPF / DKIM / DMARC authentication checks",
  "Sending origin & server location",
  "AI-detected signals",
];

export default function ReportsPage() {
  const navigate = useNavigate();
  const { currentCase } = useCaseContext();

  if (!currentCase) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <header className="reference-page-head">
            <h1>
              Report <span>Download</span>
            </h1>
          </header>

          <section className="ref-panel ref-analysis-empty">
            <FileText size={30} strokeWidth={1.6} />
            <h3>No report available yet</h3>
            <p>Upload an email from the dashboard to generate a downloadable report.</p>
            <button type="button" className="ref-empty-cta" onClick={() => navigate("/")}>
              Go to Dashboard
              <ArrowRight size={16} />
            </button>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head">
          <h1>
            Report <span>Download</span>
          </h1>

          <div className="reference-head-actions">
            <span className="ref-origin-eyebrow-tag">CASE #{currentCase.caseId}</span>
          </div>
        </header>

        <DashboardPanel title="Case report">
          <div className="ref-report-card">
            <div className="ref-report-icon">
              <FileText size={22} />
            </div>

            <div className="ref-report-copy">
              <strong>Case #{currentCase.caseId} — PDF report</strong>
              <span>{SEVERITY_LABEL[currentCase.severity] || "Risk assessment"} · Risk score {currentCase.riskScore ?? "—"}</span>
            </div>

            <a href={getCaseReportUrl(currentCase.caseId)} download className="ref-download-btn">
              <Download size={16} />
              Download PDF
            </a>
          </div>
        </DashboardPanel>

        <DashboardPanel title="What's included">
          <ul className="ref-signal-list">
            {INCLUDES.map((item) => (
              <li key={item} className="ref-signal-item level-low">
                <CheckCircle2 size={15} />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </DashboardPanel>
      </div>
    </main>
  );
}
