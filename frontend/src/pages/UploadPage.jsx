// src/pages/UploadPage.jsx
/**
 * Standalone "Upload & Parse" interface.
 *
 * Previously the upload box and the per-email parsing panel lived inside
 * the Dashboard. They now have their own page so uploading/parsing an
 * email and looking at its charts doesn't get mixed in with the
 * aggregate dashboard view.
 */

import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight, LoaderCircle, ShieldCheck, FileSearch } from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { useCases } from "../hooks/useCases";
import { useAnalyzeEmail } from "../hooks/useAnalyzeEmail";

import { DashboardPanel, UploadEmailCard, RiskGauge } from "../components/dashboard/DashboardWidgets";
import EmailParsingPanel from "../components/dashboard/EmailParsingPanel";
import AiBadge from "../components/dashboard/AiBadge";

export default function UploadPage() {
  const navigate = useNavigate();
  const { currentCase, setCurrentCase } = useCaseContext();
  const { refetch } = useCases();

  const {
    analyze,
    isLoading: isAnalyzing,
    error: analyzeError,
  } = useAnalyzeEmail();

  async function handleFileSelected(file) {
    const result = await analyze(file).catch(() => null);

    if (result) {
      setCurrentCase(result);
      refetch();
    }
  }

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head">
          <h1>
            Upload <span>&amp; Parse</span>
          </h1>

          {currentCase && (
            <div className="reference-head-actions">
              <AiBadge label={`CASE #${currentCase.caseId}`} />
            </div>
          )}
        </header>

        {/* =================================================
            EMAIL UPLOAD
            ================================================= */}

        <UploadEmailCard
          onFileSelected={handleFileSelected}
          isLoading={isAnalyzing}
        />

        {isAnalyzing && (
          <section className="ref-analysis-loading" aria-live="polite">
            <div className="ref-analysis-loader-icon"><LoaderCircle size={28} /></div>
            <div className="ref-analysis-loader-copy">
              <span className="ref-analysis-loading-label">AI ANALYSIS IN PROGRESS</span>
              <strong>Inspecting your email</strong>
              <p>Parsing headers, checking authentication, extracting links and evaluating suspicious indicators.</p>
              <div className="ref-analysis-loading-steps">
                <span><FileSearch size={13} /> Parsing</span>
                <span><ShieldCheck size={13} /> Authentication</span>
                <span><Sparkles size={13} /> Threat scoring</span>
              </div>
            </div>
            <div className="ref-analysis-loading-pulse"><i /><i /><i /></div>
          </section>
        )}

        {analyzeError && (
          <p className="ref-history-note">
            Couldn't analyze that email: {analyzeError}
          </p>
        )}

        {/* =================================================
            PER-EMAIL RISK SUMMARY
            ================================================= */}

        {currentCase && (
          <div className="ref-grid-two ref-upload-summary-grid">
            <DashboardPanel title="Risk score" className="ref-upload-risk-panel">
              <div className="ref-upload-risk-inner">
                <RiskGauge
                  value={currentCase.riskScore}
                  caption={`Case #${currentCase.caseId}`}
                />
              </div>
            </DashboardPanel>

            <DashboardPanel title="What's next" className="ref-upload-next-panel">
              <div className="ref-next-content">
                <div>
                  <strong>Want the full signal breakdown?</strong>
                  <p>Open Deep Analysis for authentication, origin and AI findings.</p>
                </div>
                <button
                  type="button"
                  className="ref-next-cta"
                  onClick={() => navigate("/analyze")}
                >
                  Deep Analysis
                  <ArrowRight size={15} />
                </button>
              </div>
            </DashboardPanel>
          </div>
        )}

        {/* =================================================
            PARSING OUTPUT + CHARTS FOR THIS EMAIL
            ================================================= */}

        <EmailParsingPanel currentCase={currentCase} />

        {!currentCase && (
          <p className="ref-history-note">
            <Sparkles size={13} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Upload an .eml file above to see its headers, links, attachments,
            and authentication results here.
          </p>
        )}
      </div>
    </main>
  );
}
