/**
 * Read-only "open the email" modal for a single Gmail message.
 *
 * Plain reading, not analysis — the body is shown as text by
 * default. HTML mail bodies (which is most phishing mail) can be
 * toggled on, but always render inside a fully sandboxed iframe
 * (no scripts, no same-origin, no forms) so nothing in a malicious
 * email can execute or reach the app.
 */

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Code2,
  FileText,
  Loader2,
  Paperclip,
  Radar,
  Sparkles,
  X,
} from "lucide-react";

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(kb < 10 ? 1 : 0)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

export default function MailReaderModal({
  isOpen,
  message,
  isLoading,
  error,
  onClose,
  onHandoff,
}) {
  const [viewMode, setViewMode] = useState("text");

  // Reset to plain text whenever a different (or new) message opens —
  // don't carry an "HTML view" choice over from the last email.
  useEffect(() => {
    setViewMode("text");
  }, [message?.id]);

  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(event) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const hasHtml = Boolean(message?.bodyHtml);

  return (
    <div className="gmail-reader-overlay" onClick={onClose}>
      <div
        className="gmail-reader-panel"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="gmail-reader-close"
          aria-label="Close"
          onClick={onClose}
        >
          <X size={16} />
        </button>

        {isLoading && (
          <div className="gmail-reader-state">
            <Loader2 size={20} className="gmail-spin" />
            Loading message…
          </div>
        )}

        {!isLoading && error && (
          <div className="gmail-reader-state gmail-reader-state-error">
            <AlertTriangle size={20} />
            Couldn't load that email: {error}
          </div>
        )}

        {!isLoading && !error && message && (
          <>
            <header className="gmail-reader-head">
              <span className="gmail-panel-kicker">MESSAGE</span>
              <h2>{message.subject || "(no subject)"}</h2>

              <div className="gmail-reader-fields">
                <div>
                  <span>From</span>
                  <strong>{message.from || "—"}</strong>
                </div>
                <div>
                  <span>To</span>
                  <strong>{message.to || "—"}</strong>
                </div>
                {message.cc && (
                  <div>
                    <span>Cc</span>
                    <strong>{message.cc}</strong>
                  </div>
                )}
                <div>
                  <span>Date</span>
                  <strong>{message.date || "—"}</strong>
                </div>
              </div>
            </header>

            {hasHtml && (
              <div className="gmail-reader-viewtabs">
                <button
                  type="button"
                  className={viewMode === "text" ? "is-active" : ""}
                  onClick={() => setViewMode("text")}
                >
                  <FileText size={13} />
                  Plain text
                </button>
                <button
                  type="button"
                  className={viewMode === "html" ? "is-active" : ""}
                  onClick={() => setViewMode("html")}
                >
                  <Code2 size={13} />
                  HTML view
                </button>
              </div>
            )}

            <div className="gmail-reader-body">
              {viewMode === "html" && hasHtml ? (
                <iframe
                  title="Email HTML body"
                  className="gmail-reader-html-frame"
                  sandbox=""
                  srcDoc={message.bodyHtml}
                />
              ) : (
                <pre className="gmail-reader-text">
                  {message.bodyText || "(no body content)"}
                </pre>
              )}
            </div>

            {message.attachments?.length > 0 && (
              <div className="gmail-reader-attachments">
                <span className="gmail-panel-kicker">
                  ATTACHMENTS · {message.attachments.length}
                </span>
                <ul>
                  {message.attachments.map((attachment, index) => (
                    <li key={`${attachment.filename}-${index}`}>
                      <Paperclip size={13} />
                      <span>{attachment.filename}</span>
                      <em>{formatBytes(attachment.size)}</em>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {onHandoff && (
              <footer className="gmail-reader-footer">
                <span>Looks worth a closer look?</span>
                <div className="gmail-reader-footer-actions">
                  <button
                    type="button"
                    className="gmail-reader-footer-btn gmail-reader-footer-btn--analyze"
                    onClick={() => onHandoff("analyze")}
                  >
                    <Sparkles size={13} />
                    AI Deep Analysis
                  </button>
                  <button
                    type="button"
                    className="gmail-reader-footer-btn"
                    onClick={() => onHandoff("origin")}
                  >
                    <Radar size={13} />
                    Origin Analysis
                  </button>
                </div>
              </footer>
            )}
          </>
        )}
      </div>
    </div>
  );
}
