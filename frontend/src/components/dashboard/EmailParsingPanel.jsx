// src/components/dashboard/EmailParsingPanel.jsx
/**
 * Shows the parsing output for the most recently analyzed email — header
 * fields, URLs/attachments/header findings, the content-risk chart, and
 * the SPF/DKIM/DMARC result.
 *
 * Wired to the REAL /api/analyze response shape (see
 * backend/app/api/analyze.py + backend/app/services/parsing.py):
 *
 *   currentCase.analysis.metadata: {
 *     from, to, cc, bcc, subject, date, reply_to,
 *     message_id, return_path, received_spf, dkim_signature,
 *     x_mailer, x_originating_ip
 *   }
 *   currentCase.analysis.urls: string[]
 *   currentCase.analysis.attachments: [{ filename, content_type, size,
 *     extension, suspicious, reason }]
 *   currentCase.analysis.header_findings: [{ type, severity, message }]
 *   currentCase.headerChecks: { spf, dkim, dmarc, senderDomainMismatch }
 *   currentCase.dashboard.contentRisk: [{ name, total, suspicious }]
 */

import {
  Link2,
  Paperclip,
  ListChecks,
  Highlighter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

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

function ContentRiskChart({ data }) {
  const hasAny = data.some((d) => d.total > 0);

  if (!hasAny) {
    return (
      <p className="ref-empty-inline" style={{ padding: "0 17px 12px" }}>
        No URLs, attachments, or header findings in this email.
      </p>
    );
  }

  return (
    <div style={{ padding: "4px 12px 14px" }}>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="rgba(0,0,0,.06)" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: "#9aa3a6" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: "#9aa3a6" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip />
          <Bar dataKey="total" name="Total" fill="#9fc3d8" radius={[4, 4, 0, 0]} />
          <Bar dataKey="suspicious" name="Suspicious" fill="#e0685f" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function EmailParsingPanel({ currentCase }) {
  if (!currentCase) {
    return (
      <DashboardPanel title="Email parsing">
        <p className="ref-empty-inline">
          Upload an email above to see its parsed headers, URLs, attachments, and
          authentication results here.
        </p>
      </DashboardPanel>
    );
  }

  const analysis = currentCase.analysis || {};
  const metadata = analysis.metadata || {};
  const hc = currentCase.headerChecks || {};

  const urls = analysis.urls || [];
  const attachments = analysis.attachments || [];
  const headerFindings = analysis.header_findings || [];

  const contentRisk =
    currentCase.dashboard?.contentRisk || [
      { name: "URLs", total: urls.length, suspicious: 0 },
      {
        name: "Attachments",
        total: attachments.length,
        suspicious: attachments.filter((a) => a.suspicious).length,
      },
      { name: "Header Findings", total: headerFindings.length, suspicious: headerFindings.length },
    ];

  // Flagged sections list: real header-relationship findings + any
  // attachment the analyzer flagged as suspicious.
  const flags = [
    ...headerFindings.map((f) => ({
      text: f.type?.replace(/_/g, " ") || "Header anomaly",
      reason: f.message,
      level: f.severity === "high" ? "high" : f.severity === "medium" ? "medium" : "low",
    })),
    ...attachments
      .filter((a) => a.suspicious)
      .map((a) => ({
        text: a.filename || "Attachment",
        reason: a.reason || "Flagged as a suspicious attachment type.",
        level: "high",
      })),
  ];

  return (
    <DashboardPanel
      title="Email parsing"
      right={<span className="ref-origin-eyebrow-tag">CASE #{currentCase.caseId}</span>}
    >
      <div className="ref-parse-fields">
        <div className="ref-origin-field">
          <span>Subject</span>
          <strong>{metadata.subject || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>From</span>
          <strong>{metadata.from || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>To</span>
          <strong>{metadata.to || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>Date</span>
          <strong>{metadata.date || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>Reply-To</span>
          <strong>{metadata.reply_to || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>Return-Path</span>
          <strong>{metadata.return_path || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>Message-ID</span>
          <strong>{metadata.message_id || "—"}</strong>
        </div>
        <div className="ref-origin-field">
          <span>Originating IP</span>
          <strong>{metadata.x_originating_ip || "—"}</strong>
        </div>
      </div>

      <div className="ref-auth-row">
        {AUTH_KEYS.map((key) => (
          <AuthChip key={key} label={key.toUpperCase()} value={hc[key]} />
        ))}
        {hc.senderDomainMismatch && (
          <div className="ref-auth-chip is-fail">
            <AlertTriangle size={14} />
            Domain mismatch
          </div>
        )}
      </div>

      <div className="ref-parse-stats">
        <DashboardStat icon={Link2} label="Links found" value={urls.length} />
        <DashboardStat icon={Paperclip} label="Attachments" value={attachments.length} />
        <DashboardStat icon={ListChecks} label="Header findings" value={headerFindings.length} />
      </div>

      <ContentRiskChart data={contentRisk} />

      <div className="ref-highlight-list">
        <div className="ref-highlight-head">
          <Highlighter size={13} />
          Flagged sections
        </div>

        {flags.length === 0 ? (
          <p className="ref-empty-inline">No flagged sections in this email.</p>
        ) : (
          flags.map((h, index) => (
            <div key={index} className={`ref-signal-item level-${h.level}`}>
              <AlertTriangle size={15} />
              <span>
                <strong>{h.text}</strong>
                {h.reason ? ` — ${h.reason}` : ""}
              </span>
            </div>
          ))
        )}
      </div>
    </DashboardPanel>
  );
}
