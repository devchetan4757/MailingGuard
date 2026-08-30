// src/pages/ReportsPage.jsx
/**
 * Fourth interface — the "download interface". Reached from the AI Deep
 * Analysis and Origin Analysis pages (they redirect here instead of
 * downloading straight away), or directly via the sidebar.
 *
 * Lets the analyst:
 *   - preview exactly what the PDF will look like before saving it
 *   - rename the file
 *   - download it (or open the preview in a new tab)
 */

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  ArrowRight,
  Download,
  CheckCircle2,
  ExternalLink,
  Loader2,
  AlertTriangle,
} from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel } from "../components/dashboard/DashboardWidgets";
import { getCaseReportUrl, getCaseReportPreviewUrl } from "../api/casesApi";

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

function sanitizeFilename(name) {
  const trimmed = (name || "").trim();
  const withoutIllegalChars = trimmed.replace(/[\\/:*?"<>|]+/g, "-");
  if (!withoutIllegalChars) return "mailguard-report.pdf";
  return withoutIllegalChars.toLowerCase().endsWith(".pdf")
    ? withoutIllegalChars
    : `${withoutIllegalChars}.pdf`;
}

export default function ReportsPage() {
  const navigate = useNavigate();
  const { currentCase } = useCaseContext();

  const defaultFilename = useMemo(
    () => (currentCase ? `${currentCase.caseId}-mailguard-report.pdf` : "mailguard-report.pdf"),
    [currentCase]
  );

  const [filename, setFilename] = useState(defaultFilename);
  const [downloadState, setDownloadState] = useState("idle"); // idle | loading | error

  useEffect(() => {
    setFilename(defaultFilename);
  }, [defaultFilename]);

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

  const previewUrl = getCaseReportPreviewUrl(currentCase.caseId);

  async function handleDownload() {
    setDownloadState("loading");
    try {
      const res = await fetch(getCaseReportUrl(currentCase.caseId));
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const blob = await res.blob();

      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = sanitizeFilename(filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);

      setDownloadState("idle");
    } catch (err) {
      setDownloadState("error");
    }
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
              <span>
                {SEVERITY_LABEL[currentCase.severity] || "Risk assessment"} · Risk score{" "}
                {currentCase.riskScore ?? "—"}
              </span>
            </div>

            <a
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
              className="ref-download-btn ref-download-btn--secondary"
            >
              <ExternalLink size={16} />
              Open in new tab
            </a>
          </div>
        </DashboardPanel>

        <DashboardPanel title="Preview">
          <div className="ref-report-preview">
            <iframe title={`Preview of case ${currentCase.caseId} report`} src={previewUrl} />
          </div>
        </DashboardPanel>

        <DashboardPanel title="Rename &amp; download">
          <div className="ref-report-filename-row">
            <label htmlFor="report-filename">File name</label>
            <input
              id="report-filename"
              type="text"
              className="ref-report-filename-input"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              onBlur={() => setFilename((current) => sanitizeFilename(current))}
              spellCheck={false}
            />
          </div>

          <div className="ref-report-download-actions">
            <button
              type="button"
              className="ref-download-btn"
              onClick={handleDownload}
              disabled={downloadState === "loading"}
            >
              {downloadState === "loading" ? (
                <Loader2 size={16} className="ref-spin" />
              ) : (
                <Download size={16} />
              )}
              {downloadState === "loading" ? "Preparing…" : "Download as entered above"}
            </button>

            {downloadState === "error" && (
              <span className="ref-report-status is-error">
                <AlertTriangle size={14} />
                Couldn't download the report — try again.
              </span>
            )}
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
