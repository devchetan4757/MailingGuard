// src/pages/PageSourceViewPage.jsx
/**
 * "See how this page looks" -- reached from the "Preview page" button on
 * the Deep Analysis Report page.
 *
 * The HTML is fetched server-side (fetchPageSource) so the browser never
 * makes a direct connection to the (possibly malicious) target -- it just
 * asks our own backend for the bytes it already fetched. What comes back
 * is rendered three ways:
 *   - "Rendered preview": a sandboxed iframe with scripts/forms/popups
 *     all disabled, so nothing on the page can run or navigate anywhere.
 *   - "View source": the raw HTML as text, for anyone who wants to read
 *     it directly (obfuscated redirects, hidden iframes, etc.).
 *   - "Edit HTML": a scratch buffer, seeded from the fetched source, that
 *     can be pasted into or edited freely and rendered on demand -- for
 *     poking at a suspicious snippet in isolation, or previewing markup
 *     that was never fetched from anywhere at all.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  Code2,
  Copy,
  Download,
  Eye,
  FileCode2,
  Info,
  Link2,
  LoaderCircle,
  PlayCircle,
  RefreshCcw,
  RotateCcw,
  ShieldAlert,
  XCircle,
} from "lucide-react";

import { fetchPageSource } from "../api/deepAnalysisApi";

// srcDoc iframes have no URL of their own, so a fetched page's relative
// "/style.css" or "images/logo.png" links silently 404 -- add a <base>
// pointing back at where the page actually came from so its own CSS
// (and any images/fonts it references) resolve and load normally. Only
// used for the real fetched page, never for pasted/edited HTML, which
// has no real origin to resolve against.
function withBase(html, baseUrl) {
  if (!baseUrl || /<base[\s>]/i.test(html)) return html;
  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/<head([^>]*)>/i, `<head$1><base href="${baseUrl}">`);
  }
  return `<base href="${baseUrl}">${html}`;
}

function SourceLines({ html }) {
  // Cheap line numbering without pulling in a syntax highlighter --
  // good enough for scanning structure/looking for suspicious markup.
  const lines = html.split("\n");
  return (
    <div className="ref-source-code">
      <div className="ref-source-code-gutter">
        {lines.map((_, i) => (
          <span key={i}>{i + 1}</span>
        ))}
      </div>
      <pre className="ref-source-code-body">{html}</pre>
    </div>
  );
}

export default function PageSourceViewPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const url = location.state?.url || "";

  const [state, setState] = useState({ status: url ? "loading" : "empty" });
  const [tab, setTab] = useState(url ? "preview" : "edit");
  const [copied, setCopied] = useState(false);
  const copyTimeout = useRef(null);

  // Scratch buffer for the "Edit HTML" tab -- seeded from whatever was
  // fetched (if anything), but otherwise free-standing so this page also
  // works as a plain "paste HTML, see how it renders" tool.
  const [editorHtml, setEditorHtml] = useState("");
  const [customMode, setCustomMode] = useState(false);

  const load = useCallback(() => {
    if (!url) return;
    setState({ status: "loading" });
    fetchPageSource(url)
      .then((data) => {
        setState({
          status: "done",
          html: data.html || "",
          finalUrl: data.final_url || url,
          statusCode: data.status_code ?? null,
        });
      })
      .catch((err) => {
        setState({ status: "error", error: err.message || "Could not fetch this page." });
      });
  }, [url]);

  useEffect(() => {
    load();
    return () => clearTimeout(copyTimeout.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  // A fresh fetch always wins back the "Rendered preview" tab -- re-fetch
  // shouldn't silently keep showing stale edited HTML.
  useEffect(() => {
    if (state.status === "done") {
      setEditorHtml(state.html || "");
      setCustomMode(false);
    }
  }, [state.status, state.html]);

  const fetchedHtml = state.status === "done" ? state.html || "" : "";
  const fetchedBaseUrl = state.status === "done" ? state.finalUrl || url : "";
  const previewHtml = customMode ? editorHtml : withBase(fetchedHtml, fetchedBaseUrl);
  const hasFetch = Boolean(url);

  const handleCopy = async () => {
    const text = tab === "edit" ? editorHtml : fetchedHtml;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      clearTimeout(copyTimeout.current);
      copyTimeout.current = setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard not available -- silently ignore */
    }
  };

  const handleDownload = () => {
    const text = tab === "edit" ? editorHtml : fetchedHtml;
    if (!text) return;
    const blob = new Blob([text], { type: "text/html" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "page-source.html";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const handleRender = () => {
    setCustomMode(true);
    setTab("preview");
  };

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
                Page <span>Preview</span>
              </h1>
              {hasFetch ? (
                <div className="ref-report-target">
                  <Link2 size={13} />
                  <span title={url}>{url}</span>
                </div>
              ) : (
                <div className="ref-report-target">
                  <Info size={13} />
                  <span>No page fetched -- paste HTML below to preview it</span>
                </div>
              )}
            </div>
          </div>

          {hasFetch && (
            <div className="reference-head-actions">
              <button
                type="button"
                className="ref-report-refresh"
                onClick={load}
                disabled={state.status === "loading"}
              >
                {state.status === "loading" ? (
                  <LoaderCircle size={14} className="ref-deep-spin" />
                ) : (
                  <RefreshCcw size={14} />
                )}
                {state.status === "loading" ? "Fetching…" : "Re-fetch"}
              </button>
            </div>
          )}
        </header>

        <div className="ref-source-safety-note">
          <ShieldAlert size={14} />
          <span>
            {hasFetch
              ? "Fetched server-side, so your browser never connects to this URL directly. CSS and images render normally; scripts, forms, and pop-ups stay disabled for this fetched page."
              : "Anything you paste into \u201cEdit HTML\u201d renders locally in a sandboxed iframe -- CSS and JS both run there, but forms and pop-ups stay disabled."}
          </span>
        </div>

        {hasFetch && state.status === "loading" && (
          <section className="ref-panel ref-deep-panel" style={{ margin: "0 0 18px" }}>
            <LoaderCircle size={16} className="ref-deep-spin" />
            <span>Fetching the page source…</span>
          </section>
        )}

        {hasFetch && state.status === "error" && (
          <section className="ref-panel ref-deep-panel is-error" style={{ margin: "0 0 18px" }}>
            <XCircle size={16} />
            <span>{state.error}</span>
            <button type="button" onClick={load}>Retry</button>
          </section>
        )}

        {(!hasFetch || state.status === "done") && (
          <>
            {hasFetch && state.status === "done" && (
              <div className="ref-source-meta-row">
                {state.statusCode !== null && (
                  <span className={`ref-source-status-chip ${state.statusCode >= 400 ? "is-bad" : "is-ok"}`}>
                    HTTP {state.statusCode}
                  </span>
                )}
                {state.finalUrl !== url && (
                  <span className="ref-source-redirect-note" title={state.finalUrl}>
                    Redirected to {state.finalUrl}
                  </span>
                )}
                <span className="ref-source-size-note">
                  {(new Blob([fetchedHtml]).size / 1024).toFixed(1)} KB
                </span>
              </div>
            )}

            <div className="ref-source-tabs">
              <button
                type="button"
                className={`ref-source-tab ${tab === "preview" ? "is-active" : ""}`}
                onClick={() => setTab("preview")}
              >
                <Eye size={13} />
                Rendered preview
              </button>

              {hasFetch && state.status === "done" && (
                <button
                  type="button"
                  className={`ref-source-tab ${tab === "source" ? "is-active" : ""}`}
                  onClick={() => setTab("source")}
                >
                  <Code2 size={13} />
                  View source
                </button>
              )}

              <button
                type="button"
                className={`ref-source-tab ${tab === "edit" ? "is-active" : ""}`}
                onClick={() => setTab("edit")}
              >
                <FileCode2 size={13} />
                Edit HTML
              </button>

              <div className="ref-source-tab-actions">
                <button type="button" className="ref-source-tab-btn" onClick={handleCopy}>
                  {copied ? <Check size={13} /> : <Copy size={13} />}
                  {copied ? "Copied" : "Copy HTML"}
                </button>
                <button type="button" className="ref-source-tab-btn" onClick={handleDownload}>
                  <Download size={13} />
                  Download
                </button>
              </div>
            </div>

            {tab === "preview" && (
              <section className="ref-panel ref-source-panel">
                {customMode && (
                  <div className="ref-source-preview-flag">
                    <Info size={13} />
                    <span>Showing your edited HTML, not the fetched page. Scripts run here.</span>
                    {hasFetch && state.status === "done" && (
                      <button type="button" onClick={() => setCustomMode(false)}>
                        Show fetched page
                      </button>
                    )}
                  </div>
                )}
                {previewHtml ? (
                  <iframe
                    title="Page preview"
                    className="ref-source-iframe"
                    srcDoc={previewHtml}
                    // The real fetched page may be malicious, so it only ever
                    // gets "allow-same-origin" -- CSS/images render, nothing
                    // executes. Edited HTML is the user's own content, so it
                    // also gets "allow-scripts" so JS runs too -- deliberately
                    // *without* allow-same-origin alongside it, so it still
                    // executes in an isolated, cookie-less, storage-less
                    // origin rather than inheriting this app's own origin.
                    sandbox={customMode ? "allow-scripts" : "allow-same-origin"}
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <p className="ref-empty-inline">
                    {hasFetch ? "This page returned no HTML to preview." : "Paste some HTML into the Edit tab and hit Render preview."}
                  </p>
                )}
              </section>
            )}

            {tab === "source" && hasFetch && state.status === "done" && (
              <section className="ref-panel ref-source-panel">
                <SourceLines html={fetchedHtml || "(empty response)"} />
              </section>
            )}

            {tab === "edit" && (
              <section className="ref-panel ref-source-panel">
                <div className="ref-source-editor">
                  <div className="ref-source-editor-toolbar">
                    <span className="ref-source-editor-hint">
                      Paste or tweak HTML, then render it to see it visually -- nothing here is sent anywhere.
                    </span>
                    <div className="ref-source-editor-actions">
                      {hasFetch && state.status === "done" && (
                        <button type="button" className="ref-source-tab-btn" onClick={() => setEditorHtml(fetchedHtml)}>
                          <RotateCcw size={13} />
                          Reset to fetched
                        </button>
                      )}
                      <button type="button" className="ref-source-render-btn" onClick={handleRender}>
                        <PlayCircle size={13} />
                        Render preview
                      </button>
                    </div>
                  </div>
                  <textarea
                    className="ref-source-editor-textarea"
                    value={editorHtml}
                    onChange={(e) => setEditorHtml(e.target.value)}
                    placeholder="<html>&#10;  <body>Paste or write HTML here…</body>&#10;</html>"
                    spellCheck={false}
                  />
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
