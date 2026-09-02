// src/components/dashboard/DeepAnalysisPanel.jsx
/**
 * The "AI Deep Analysis" interface: user picks one item (a link, the
 * sender domain, a PDF attachment, or an image attachment), we send it
 * to /api/deep-analysis/*, and show the raw result + Groq's plain-
 * language explanation. Purely an input -> result view; all the actual
 * analysis logic lives in the backend (dispatcher.py + ai_analyzers/).
 *
 * Drop into AnalysisPage.jsx: <DeepAnalysisPanel currentCase={currentCase} />
 */

import { useState } from "react";
import {
  Link2,
  Globe2,
  FileText,
  Image as ImageIcon,
  Loader2,
  ChevronDown,
  Sparkles,
} from "lucide-react";

import { DashboardPanel } from "./DashboardWidgets";
import AiBadge from "./AiBadge";
import { useDeepAnalysis } from "../../hooks/useDeepAnalysis";

function ResultBlock({ state }) {
  const [showRaw, setShowRaw] = useState(false);
  const { isLoading, error, data } = state;

  if (isLoading) {
    return (
      <div className="deep-result deep-result--loading">
        <Loader2 size={14} className="deep-spin" />
        Running analysis…
      </div>
    );
  }

  if (error) {
    return <div className="deep-result deep-result--error">{error}</div>;
  }

  if (!data) return null;

  return (
    <div className="deep-result">
      {data.explanation ? (
        <p className="deep-explanation">
          <Sparkles size={13} />
          <span>{data.explanation}</span>
        </p>
      ) : (
        <p className="deep-explanation deep-explanation--muted">
          No AI explanation available for this result — showing raw
          analyzer output below.
        </p>
      )}

      <button
        type="button"
        className="deep-raw-toggle"
        onClick={() => setShowRaw((v) => !v)}
      >
        <ChevronDown
          size={13}
          style={{ transform: showRaw ? "rotate(180deg)" : "none" }}
        />
        {showRaw ? "Hide raw result" : "View raw result"}
      </button>

      {showRaw && (
        <pre className="deep-raw-json">
          {JSON.stringify(data.result, null, 2)}
        </pre>
      )}
    </div>
  );
}

function AnalyzerCard({
  icon: Icon,
  title,
  description,
  children,
  state,
}) {
  return (
    <div className="deep-card">
      <div className="deep-card-head">
        <Icon size={16} />
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>

      <div className="deep-card-body">{children}</div>

      <ResultBlock state={state} />
    </div>
  );
}

export default function DeepAnalysisPanel({ currentCase }) {
  const { run, getState } = useDeepAnalysis();

  const [linkInput, setLinkInput] = useState("");
  const [domainInput, setDomainInput] = useState(
    currentCase?.senderDomain || ""
  );
  const [pdfFile, setPdfFile] = useState(null);
  const [imageFile, setImageFile] = useState(null);

  const linkState = getState("link");
  const domainState = getState("domain");
  const pdfState = getState("pdf-attachment");
  const imageState = getState("image-attachment");

  return (
    <DashboardPanel
      title="Run a deep analysis"
      right={<AiBadge label="Groq-powered" />}
    >
      <div className="deep-grid">
        <AnalyzerCard
          icon={Link2}
          title="Analyze a link"
          description="Crawl a link from this email and check where it actually leads."
          state={linkState}
        >
          <form
            className="deep-inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (linkInput.trim()) run("link", linkInput.trim());
            }}
          >
            <input
              type="text"
              placeholder="https://example.com/reset-password"
              value={linkInput}
              onChange={(e) => setLinkInput(e.target.value)}
              disabled={linkState.isLoading}
            />
            <button type="submit" disabled={linkState.isLoading || !linkInput.trim()}>
              Scan link
            </button>
          </form>
        </AnalyzerCard>

        <AnalyzerCard
          icon={Globe2}
          title="Check sender domain"
          description="Look up WHOIS/DNS info for the domain this email claims to be from."
          state={domainState}
        >
          <form
            className="deep-inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (domainInput.trim()) run("domain", domainInput.trim());
            }}
          >
            <input
              type="text"
              placeholder="example.com"
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              disabled={domainState.isLoading}
            />
            <button type="submit" disabled={domainState.isLoading || !domainInput.trim()}>
              Check domain
            </button>
          </form>
        </AnalyzerCard>

        <AnalyzerCard
          icon={FileText}
          title="Scan PDF attachment"
          description="Re-upload a PDF from this email to check for risky content or scripts."
          state={pdfState}
        >
          <form
            className="deep-inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (pdfFile) run("pdf-attachment", pdfFile);
            }}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
              disabled={pdfState.isLoading}
            />
            <button type="submit" disabled={pdfState.isLoading || !pdfFile}>
              Scan PDF
            </button>
          </form>
        </AnalyzerCard>

        <AnalyzerCard
          icon={ImageIcon}
          title="Scan image attachment"
          description="Re-upload an image from this email to check its metadata for privacy risks."
          state={imageState}
        >
          <form
            className="deep-inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (imageFile) run("image-attachment", imageFile);
            }}
          >
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.gif,.tif,.tiff,.bmp,.webp,.heic"
              onChange={(e) => setImageFile(e.target.files?.[0] || null)}
              disabled={imageState.isLoading}
            />
            <button type="submit" disabled={imageState.isLoading || !imageFile}>
              Scan image
            </button>
          </form>
        </AnalyzerCard>
      </div>
    </DashboardPanel>
  );
}
