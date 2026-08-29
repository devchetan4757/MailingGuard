// src/components/dashboard/EmailParsingPanel.jsx

import {
  Link2,
  Paperclip,
  ListChecks,
  Highlighter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Mail,
  Globe2,
  Clock3,
  UserRound,
} from "lucide-react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";

import { DashboardPanel, DashboardStat } from "./DashboardWidgets";

const AUTH_KEYS = ["spf", "dkim", "dmarc"];

function ContentRiskChart({ data }) {
  const safeData = data.map((item) => ({
    ...item,
    total: Number(item.total || 0),
    suspicious: Number(item.suspicious || 0),
  }));

  const hasAny = safeData.some((d) => d.total > 0);
  if (!hasAny) return <EmptyBlock text="No URLs, attachments, or header findings were detected." />;

  return (
    <div className="ref-analysis-chart-wrap">
      <div className="ref-analysis-chart-title">
        <div>
          <span>CONTENT EXPOSURE</span>
          <strong>What the parser found</strong>
        </div>
        <div className="ref-chart-legend">
          <i className="legend-total" /> Total
          <i className="legend-suspicious" /> Suspicious
        </div>
      </div>

      <ResponsiveContainer width="100%" height={225}>
        <BarChart data={safeData} margin={{ top: 14, right: 8, left: -20, bottom: 4 }} barGap={7}>
          <CartesianGrid vertical={false} stroke="rgba(38,58,67,.08)" strokeDasharray="4 5" />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#718087" }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#8b969b" }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: "rgba(85,174,181,.06)" }}
            contentStyle={{ borderRadius: 10, border: "1px solid #d9e3e5", boxShadow: "0 8px 24px rgba(35,55,61,.10)" }}
          />
          <Bar dataKey="total" name="Total" fill="#9fc3d8" radius={[7, 7, 2, 2]} />
          <Bar dataKey="suspicious" name="Suspicious" fill="#df7469" radius={[7, 7, 2, 2]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function normaliseAuthValue(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "pass") return "pass";
  if (normalized === "fail") return "fail";
  return "unknown";
}

function AuthChart({ checks, analysis }) {
  const authentication = analysis?.authentication || {};

  // Prefer the API's normalized headerChecks, but fall back to the detailed
  // parser authentication object when a field is missing.
  const auth = Object.fromEntries(
    AUTH_KEYS.map((key) => {
      const fallback = authentication?.[key]?.result;
      return [key, normaliseAuthValue(checks?.[key] ?? fallback)];
    })
  );

  const pass = AUTH_KEYS.filter((key) => auth[key] === "pass").length;
  const fail = AUTH_KEYS.filter((key) => auth[key] === "fail").length;
  const unknown = AUTH_KEYS.length - pass - fail;
  const known = pass + fail;

  const data = [
    { name: "Passed", value: pass },
    { name: "Failed", value: fail },
    { name: "Not checked", value: unknown },
  ].filter((x) => x.value > 0);

  // Unknown authentication must NOT make a message look like a 0% result.
  // A percentage is only meaningful when the email actually contains an
  // authentication result.
  const score = known ? Math.round((pass / known) * 100) : null;

  return (
    <div className="ref-auth-visual">
      <div className="ref-auth-donut">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="68%" outerRadius="92%" paddingAngle={3} stroke="none">
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.name === "Passed" ? "#56a98a" : entry.name === "Failed" ? "#df7469" : "#cbd5d8"} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="ref-auth-donut-center">
          <strong>{score === null ? "—" : `${score}%`}</strong>
          <span>{known ? `${known}/3 checked` : "not available"}</span>
        </div>
      </div>

      <div className="ref-auth-breakdown">
        {AUTH_KEYS.map((key) => {
          const value = auth[key];
          const failed = value === "fail";
          const passed = value === "pass";
          return (
            <div className="ref-auth-breakdown-row" key={key}>
              <span className={`ref-auth-dot ${failed ? "fail" : passed ? "pass" : "unknown"}`} />
              <b>{key.toUpperCase()}</b>
              <span>{value === "unknown" ? "not checked" : value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetadataGrid({ metadata }) {
  const fields = [
    ["Subject", metadata.subject, Mail],
    ["From", metadata.from, UserRound],
    ["To", metadata.to, UserRound],
    ["Date", metadata.date, Clock3],
    ["Reply-To", metadata.reply_to, Mail],
    ["Return-Path", metadata.return_path, Mail],
    ["Message-ID", metadata.message_id, ListChecks],
    ["Originating IP", metadata.x_originating_ip, Globe2],
  ];

  return (
    <div className="ref-meta-grid">
      {fields.map(([label, value, Icon]) => (
        <div className="ref-meta-card" key={label}>
          <div className="ref-meta-icon"><Icon size={14} /></div>
          <div>
            <span>{label}</span>
            <strong title={value || "—"}>{value || "—"}</strong>
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyBlock({ text }) {
  return <p className="ref-empty-inline ref-analysis-empty-note">{text}</p>;
}

export default function EmailParsingPanel({ currentCase }) {
  if (!currentCase) {
    return (
      <DashboardPanel title="Email analysis">
        <EmptyBlock text="Upload an email above to see its parsed headers, links, attachments, authentication health, and threat indicators." />
      </DashboardPanel>
    );
  }

  const analysis = currentCase.analysis || {};
  const metadata = analysis.metadata || {};
  const hc = currentCase.headerChecks || {};
  const urls = analysis.urls || [];
  const attachments = analysis.attachments || [];
  const headerFindings = analysis.header_findings || [];

  const contentRisk = currentCase.dashboard?.contentRisk || [
    { name: "URLs", total: urls.length, suspicious: 0 },
    { name: "Attachments", total: attachments.length, suspicious: attachments.filter((a) => a.suspicious).length },
    { name: "Header findings", total: headerFindings.length, suspicious: headerFindings.length },
  ];

  const flags = [
    ...headerFindings.map((f) => ({
      text: f.type?.replace(/_/g, " ") || "Header anomaly",
      reason: f.message,
      level: f.severity === "high" ? "high" : f.severity === "medium" ? "medium" : "low",
    })),
    ...attachments.filter((a) => a.suspicious).map((a) => ({
      text: a.filename || "Attachment",
      reason: a.reason || "Flagged as a suspicious attachment type.",
      level: "high",
    })),
  ];

  const severity = currentCase.severity || "yellow";
  const risk = Number(currentCase.riskScore || 0);

  return (
    <div className="ref-email-analysis-stack">
      <DashboardPanel
        title="Email analysis overview"
        right={<span className={`ref-analysis-severity severity-${severity}`}>{severity} risk · {risk}%</span>}
      >
        <div className="ref-analysis-hero-grid">
          <div className="ref-analysis-risk-card" data-severity={severity}>
            <div className="ref-analysis-risk-ring" style={{ "--risk": `${risk}%` }}>
              <div>
                <strong>{risk}</strong>
                <span>/ 100</span>
              </div>
            </div>
            <div>
              <span className="ref-analysis-overline">THREAT SCORE</span>
              <h3>{severity === "red" ? "High-risk email" : severity === "green" ? "Low-risk email" : "Needs review"}</h3>
              <p>{currentCase.verdict || "The parser combined authentication, content and origin signals into this score."}</p>
            </div>
          </div>

          <div className="ref-analysis-auth-card">
            <div className="ref-analysis-overline">AUTHENTICATION HEALTH</div>
            <AuthChart checks={hc} analysis={analysis} />
          </div>
        </div>

        <div className="ref-parse-stats">
          <DashboardStat icon={Link2} label="Links found" value={urls.length} />
          <DashboardStat icon={Paperclip} label="Attachments" value={attachments.length} />
          <DashboardStat icon={ListChecks} label="Header findings" value={headerFindings.length} />
        </div>
      </DashboardPanel>

      <DashboardPanel title="Parser telemetry">
        <ContentRiskChart data={contentRisk} />
      </DashboardPanel>

      <DashboardPanel title="Email metadata" right={<span className="ref-origin-eyebrow-tag">CASE #{currentCase.caseId}</span>}>
        <MetadataGrid metadata={metadata} />
      </DashboardPanel>

      <div className="ref-grid-two">
        <DashboardPanel title="Threat indicators" right={<span className="ref-panel-number">{flags.length}</span>}>
          <div className="ref-highlight-list ref-analysis-findings">
            {flags.length === 0 ? (
              <div className="ref-safe-state">
                <ShieldCheck size={22} />
                <div><strong>No flagged indicators</strong><span>No major parser findings were raised for this email.</span></div>
              </div>
            ) : (
              flags.map((item, index) => (
                <div key={index} className={`ref-analysis-finding level-${item.level}`}>
                  {item.level === "high" ? <ShieldAlert size={17} /> : <AlertTriangle size={17} />}
                  <div><strong>{item.text}</strong><span>{item.reason}</span></div>
                </div>
              ))
            )}
          </div>
        </DashboardPanel>

        <DashboardPanel title="Detected attachments" right={<span className="ref-panel-number">{attachments.length}</span>}>
          {attachments.length === 0 ? (
            <EmptyBlock text="No attachments were found in this email." />
          ) : (
            <div className="ref-attachment-list">
              {attachments.map((item, index) => (
                <div className={`ref-attachment-row ${item.suspicious ? "is-suspicious" : ""}`} key={`${item.filename}-${index}`}>
                  <div className="ref-attachment-icon"><Paperclip size={16} /></div>
                  <div><strong>{item.filename || "Unnamed attachment"}</strong><span>{item.content_type || item.extension || "Unknown type"}{item.size ? ` · ${item.size}` : ""}</span></div>
                  {item.suspicious && <b>FLAGGED</b>}
                </div>
              ))}
            </div>
          )}
        </DashboardPanel>
      </div>

      <DashboardPanel title="Extracted links" right={<span className="ref-panel-number">{urls.length}</span>}>
        {urls.length === 0 ? (
          <EmptyBlock text="No links were extracted from this email." />
        ) : (
          <div className="ref-url-list">
            {urls.map((url, index) => (
              <div className="ref-url-row" key={`${url}-${index}`}>
                <div className="ref-url-icon"><Link2 size={14} /></div>
                <span title={url}>{url}</span>
              </div>
            ))}
          </div>
        )}
      </DashboardPanel>
    </div>
  );
}
