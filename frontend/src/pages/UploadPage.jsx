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
import { Sparkles, ArrowRight } from "lucide-react";

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

        {analyzeError && (
          <p className="ref-history-note">
            Couldn't analyze that email: {analyzeError}
          </p>
        )}

        {/* =================================================
            PER-EMAIL RISK SUMMARY
            ================================================= */}

        {currentCase && (
          <div className="ref-grid-two">
            <DashboardPanel title="Risk score">
              <RiskGauge
                value={currentCase.riskScore}
                caption={`Case #${currentCase.caseId}`}
              />
            </DashboardPanel>

            <DashboardPanel title="What's next">
              <p className="ref-empty-inline" style={{ padding: "4px 4px 14px" }}>
                This email has been parsed below. For the full AI signal
                breakdown and origin trace, head over to Deep Analysis.
              </p>

              <button
                type="button"
                className="ref-empty-cta"
                onClick={() => navigate("/analyze")}
              >
                Go to Deep Analysis
                <ArrowRight size={16} />
              </button>
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
