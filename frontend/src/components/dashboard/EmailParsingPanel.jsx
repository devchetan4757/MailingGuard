// src/components/dashboard/EmailParsingPanel.jsx
/**
 * Shows the parsing output for the most recently analyzed email — header
 * fields, flagged/highlighted sections, and the SPF/DKIM/DMARC result.
 * The parsing itself is a teammate's backend work in progress, so every
 * field below is optional-chained with a "—" fallback. Expected shape,
 * once wired up:
 *
 *   currentCase.parsedEmail: {
 *     subject, from, to, replyTo,
 *     linksCount, attachmentsCount, wordCount,
 *   }
 *   currentCase.highlights: [{ text, reason, level: "high"|"medium"|"low" }]
 *   currentCase.headerChecks: { spf, dkim, dmarc } // already live
 *
 * Nothing here needs to change when those fields start arriving for real —
 * this file just stops rendering "—" and starts rendering data.
 */

import {
  Mail,
  Link2,
  Paperclip,
  Type,
  Highlighter,
  CheckCircle2,
  XCircle,
} from "lucide-react";

import { DashboardPanel, DashboardStat } from "./DashboardWidgets";

const AUTH_KEYS = ["spf", "dkim", "dmarc"];

function AuthChip({ label, value }) {
  const failed = value === "fail";
  return (
    <div className={`ref-auth-chip ${failed ? "is-fail" : "is-pass"}`}>
      {failed ? <XCircle size={14} /> : <CheckCircle2 size={14} />}
      {label}
      <span>{value || "n/a"}</span>
    </div>
  );
}

export default function EmailParsingPanel({ currentCase }) {
  if (!currentCase) {
    return (
      <DashboardPanel title="Email parsing">
        <p className="ref-empty-inline">
          Upload an email above to see its parsed headers, flagged sections, and
          authentication results here.
        </p>
      </DashboardPanel>
    );
  }

  const parsed = currentCase.parsedEmail || {};
  const hc = currentCase.headerChecks || {};
  const highlights = currentCase.highlights || [];

  return (
    <DashboardPanel
      title="Email parsing"
      right={<span className="ref-origin-eyebrow-tag">CASE #{currentCase.caseId}</span>}
    >
      <div className="ref-parse-fields">
        <div className="ref-origin-field">
          <span>Subject</span>
          <strong>{parsed.subject || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>From</span>
          <strong>{parsed.from || currentCase.sender || currentCase.senderDomain || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>To</span>
          <strong>{parsed.to || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>Reply-To</span>
          <strong>{parsed.replyTo || "—"}</strong>
        </div>
      </div>

      <div className="ref-auth-row">
        {AUTH_KEYS.map((key) => (
          <AuthChip key={key} label={key.toUpperCase()} value={hc[key]} />
        ))}
      </div>

      <div className="ref-parse-stats">
        <DashboardStat icon={Link2} label="Links found" value={parsed.linksCount ?? "—"} />
        <DashboardStat icon={Paperclip} label="Attachments" value={parsed.attachmentsCount ?? "—"} />
        <DashboardStat icon={Type} label="Word count" value={parsed.wordCount ?? "—"} />
      </div>

      <div className="ref-highlight-list">
        <div className="ref-highlight-head">
          <Highlighter size={13} />
          Flagged sections
        </div>

        {highlights.length === 0 ? (
          <p className="ref-empty-inline">No flagged sections in this email.</p>
        ) : (
          highlights.map((h, index) => (
            <div key={index} className={`ref-signal-item level-${h.level || "medium"}`}>
              <Mail size={15} />
              <span>
                <strong>“{h.text}”</strong>
                {h.reason ? ` — ${h.reason}` : ""}
              </span>
            </div>
          ))
        )}
      </div>
    </DashboardPanel>
  );
}
