// src/components/dashboard/DashboardWidgets.jsx

import {
  AlertTriangle,
  ArrowUpRight,
  Mail,
  Users,
  ChevronDown,
  Globe,
} from "lucide-react";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

/* =========================================================
   SHARED PANEL
   ========================================================= */

export function DashboardPanel({
  title,
  right,
  children,
  className = "",
}) {
  return (
    <section
      className={`ref-panel ${className}`}
    >
      <div className="ref-panel-head">
        <h2>{title}</h2>
        {right}
      </div>

      {children}
    </section>
  );
}

/* =========================================================
   STAT CARD
   ========================================================= */

export function DashboardStat({
  icon: Icon,
  label,
  value,
  delta,
}) {
  return (
    <section className="ref-stat-card">
      <div className="ref-stat-icon">
        <Icon
          size={17}
          strokeWidth={1.8}
        />
      </div>

      <div className="ref-stat-copy">
        <div className="ref-stat-label">
          {label}
        </div>

        <div className="ref-stat-bottom">
          <strong>{value}</strong>

          {delta && (
            <span className="ref-stat-delta">
              {delta}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   UPLOAD EMAIL
   ========================================================= */

export function UploadEmailCard({
  onFileSelected,
  isLoading,
}) {
  function handleChange(e) {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
    e.target.value = "";
  }

  return (
    <section className="ref-upload-card">
      <div className="ref-upload-content">
        <div className="ref-upload-icon">
          <Mail
            size={25}
            strokeWidth={1.8}
          />
        </div>

        <div className="ref-upload-copy">
          <div className="ref-upload-eyebrow">
            EMAIL THREAT ANALYZER
          </div>

          <h2>
            Analyze a suspicious email
          </h2>

          <p>
            Upload an email and analyze its
            threat risk, sender information,
            suspicious indicators and malicious
            content.
          </p>
        </div>
      </div>

      <label className="ref-upload-button">
        <input
          type="file"
          accept=".eml"
          className="hidden"
          onChange={handleChange}
          disabled={isLoading}
        />

        <Mail
          size={18}
          strokeWidth={2}
        />

        <span>
          {isLoading ? "Analyzing…" : "Upload Email"}
        </span>

        <ArrowUpRight
          size={17}
          strokeWidth={2}
        />
      </label>
    </section>
  );
}

/* =========================================================
   RISK GAUGE
   ========================================================= */

export function RiskGauge({
  value = 86,
  caption = "Risk score",
}) {
  const safe = Math.max(
    0,
    Math.min(
      100,
      Number(value) || 0
    )
  );

  // Track is a clean semicircle: the "0" end sits at -90° from vertical
  // and the "100" end sits at +90°, so the needle must span the same
  // 180° range or it swings past the tick marks at the extremes.
  const angle =
    -90 + safe * 1.8;

  return (
    <div className="ref-gauge-wrap">
      <svg
        viewBox="0 0 360 230"
        className="ref-gauge"
        aria-label={`Risk score ${safe}%`}
      >
        <path
          d="M 52 192 A 128 128 0 0 1 308 192"
          pathLength="100"
          className="ref-gauge-track"
        />

        <path
          d="M 52 192 A 128 128 0 0 1 308 192"
          pathLength="100"
          className="ref-gauge-value"
          style={{
            strokeDasharray: `${safe} 100`,
          }}
        />

        <line
          x1="180"
          y1="192"
          x2="180"
          y2="78"
          className="ref-gauge-needle"
          transform={`rotate(${angle} 180 192)`}
        />

        <circle
          cx="180"
          cy="192"
          r="6"
          className="ref-gauge-dot"
        />

        <text
          x="72"
          y="214"
          className="ref-gauge-label"
        >
          0
        </text>

        <text
          x="288"
          y="214"
          className="ref-gauge-label"
        >
          100
        </text>
      </svg>

      <div className="ref-gauge-value-badge">
        {safe}%
      </div>

      <div className="ref-gauge-caption">
        {caption}
      </div>
    </div>
  );
}

/* =========================================================
   AUTHENTICATION HEALTH CHIPS (aggregate SPF/DKIM/DMARC)
   ========================================================= */

const AUTH_LABELS = [
  { key: "spf", label: "SPF" },
  { key: "dkim", label: "DKIM" },
  { key: "dmarc", label: "DMARC" },
];

export function AuthHealthChips({
  totals = {},
}) {
  return (
    <div className="ref-auth-row">
      {AUTH_LABELS.map(({ key, label }) => {
        const stat = totals[key] || {
          pass: 0,
          fail: 0,
          total: 0,
        };

        const rate = stat.total
          ? Math.round(
              (stat.pass / stat.total) * 100
            )
          : null;

        const failing =
          stat.total > 0 &&
          stat.pass < stat.total;

        return (
          <div
            key={key}
            className={`ref-auth-chip ${
              failing ? "is-fail" : "is-pass"
            }`}
          >
            {label}
            <span>
              {rate === null
                ? "no data"
                : `${rate}% pass`}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* =========================================================
   ALERT VOLUME BAR CHART
   ========================================================= */

export function AlertVolumeChart({
  data = [],
}) {
  // Each entry is expected to carry a real weekday `label`,
  // a case-derived `total`, and (optionally) a `mailboxTotal`
  // — the mailbox count only gets used as a fallback series
  // when there's no case volume yet, so the chart still shows
  // a real number instead of a placeholder.
  const labels = data.map(
    (item, index) =>
      item?.label || `Day ${index + 1}`
  );

  const caseValues = data.map((item) =>
    Number(item?.total || 0)
  );

  const mailboxValues = data.map((item) =>
    Number(item?.mailboxTotal || 0)
  );

  const hasCaseVolume = caseValues.some(
    (value) => value > 0
  );

  const chartValues = hasCaseVolume
    ? caseValues
    : mailboxValues;

  const max = Math.max(
    ...chartValues,
    1
  );

  const showingMailboxFallback =
    !hasCaseVolume &&
    mailboxValues.some((v) => v > 0);

  return (
    <>
      <div className="ref-bar-chart">
        <div className="ref-chart-grid-lines">
          <span />
          <span />
          <span />
        </div>

        <div className="ref-bars">
          {labels.map(
            (label, index) => {
              const value =
                chartValues[index] || 0;

              const height =
                24 +
                (value / max) * 116;

              return (
                <div
                  className="ref-bar-col"
                  key={`${label}-${index}`}
                >
                  <div className="ref-bar-value">
                    {value}
                  </div>

                  <div
                    className="ref-bar"
                    style={{
                      height,
                    }}
                  />

                  <span>
                    {label}
                  </span>
                </div>
              );
            }
          )}
        </div>
      </div>

      {showingMailboxFallback && (
        <p className="ref-chart-note">
          Showing mailbox volume — no
          analyzed alerts yet
        </p>
      )}
    </>
  );
}

/* =========================================================
   RISK SEVERITY AREA CHART
   (the one trend chart kept on the dashboard — High risk vs
   Low risk over the last 7 days)
   ========================================================= */

export function BreakdownChart({
  data = [],
}) {
  const chartData =
    data.length > 0
      ? data
      : [{ label: "", red: 0, green: 0 }];

  return (
    <div className="ref-line-chart">
      <ResponsiveContainer width="100%" height={150}>
        <AreaChart
          data={chartData}
          margin={{ top: 8, right: 6, left: 6, bottom: 0 }}
        >
          <defs>
            <linearGradient
              id="area-risk-a"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor="#e0685f" stopOpacity=".28" />
              <stop offset="100%" stopColor="#e0685f" stopOpacity=".02" />
            </linearGradient>

            <linearGradient
              id="area-risk-b"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor="#e8c56b" stopOpacity=".24" />
              <stop offset="100%" stopColor="#e8c56b" stopOpacity=".02" />
            </linearGradient>
          </defs>

          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#9aa3a6" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />

          <Tooltip
            formatter={(value, name) => [
              value,
              name === "red" ? "High risk" : "Low risk",
            ]}
            labelFormatter={(label) => label}
          />

          <Area
            type="monotone"
            dataKey="red"
            stroke="#e0685f"
            strokeWidth={2}
            fill="url(#area-risk-a)"
          />

          <Area
            type="monotone"
            dataKey="green"
            stroke="#e8c56b"
            strokeWidth={2}
            fill="url(#area-risk-b)"
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="ref-chart-pill">
        RISK
      </div>
    </div>
  );
}

/* =========================================================
   VERDICT DONUT CHART
   (replaces the old stacked-area "Verdict Trend" chart —
   same red/yellow/green totals, shown as a proportion
   instead of a third near-identical area chart)
   ========================================================= */

export function VerdictDonutChart({
  data = [],
}) {
  const totals = data.reduce(
    (acc, day) => {
      acc.threats += Number(day?.red || 0);
      acc.suspicious += Number(day?.yellow || 0);
      acc.safe += Number(day?.green || 0);
      return acc;
    },
    { threats: 0, suspicious: 0, safe: 0 }
  );

  const grandTotal =
    totals.threats + totals.suspicious + totals.safe;

  const slices = [
    { key: "threats", label: "Threats", value: totals.threats, color: "#e0685f" },
    { key: "suspicious", label: "Suspicious", value: totals.suspicious, color: "#e8c56b" },
    { key: "safe", label: "Safe", value: totals.safe, color: "#62b7bc" },
  ];

  if (!grandTotal) {
    return (
      <p className="ref-empty-inline">
        No verdict data yet — analyze an email to see how it's classified.
      </p>
    );
  }

  return (
    <div className="ref-donut-wrap">
      <div className="ref-donut-plot">
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="label"
              innerRadius={52}
              outerRadius={78}
              paddingAngle={slices.filter((s) => s.value > 0).length > 1 ? 3 : 0}
              stroke="none"
            >
              {slices.map((slice) => (
                <Cell key={slice.key} fill={slice.color} />
              ))}
            </Pie>

            <Tooltip
              formatter={(value, name) => [value, name]}
            />
          </PieChart>
        </ResponsiveContainer>

        <div className="ref-donut-center">
          <strong>{grandTotal}</strong>
          <span>emails</span>
        </div>
      </div>

      <div className="ref-legend ref-donut-legend">
        {slices.map((slice) => (
          <span key={slice.key}>
            <i style={{ background: slice.color }} />
            {slice.label}
            <b>{slice.value}</b>
          </span>
        ))}
      </div>
    </div>
  );
}

/* =========================================================
   FLAGGED SECTIONS BREAKDOWN
   (replaces the old stacked-area "Flagged Sections" chart —
   same critical/moderate/minor totals, shown as a single
   segmented bar instead of another near-identical area chart)
   ========================================================= */

export function FlaggedSectionsBreakdown({
  data = [],
}) {
  const totals = data.reduce(
    (acc, day) => {
      acc.high += Number(day?.high || 0);
      acc.medium += Number(day?.medium || 0);
      acc.low += Number(day?.low || 0);
      return acc;
    },
    { high: 0, medium: 0, low: 0 }
  );

  const grandTotal =
    totals.high + totals.medium + totals.low;

  const segments = [
    { key: "high", label: "Critical", value: totals.high, color: "#e0685f" },
    { key: "medium", label: "Moderate", value: totals.medium, color: "#e8c56b" },
    { key: "low", label: "Minor", value: totals.low, color: "#62b7bc" },
  ];

  if (!grandTotal) {
    return (
      <p className="ref-empty-inline">
        No flagged sections yet — analyze an email to see what's being
        highlighted.
      </p>
    );
  }

  return (
    <div className="ref-segment-breakdown">
      <div className="ref-segment-track">
        {segments.map(
          (segment) =>
            segment.value > 0 && (
              <div
                key={segment.key}
                className="ref-segment-fill"
                style={{
                  width: `${(segment.value / grandTotal) * 100}%`,
                  background: segment.color,
                }}
                title={`${segment.label}: ${segment.value}`}
              />
            )
        )}
      </div>

      <div className="ref-segment-legend">
        {segments.map((segment) => (
          <div
            className="ref-segment-legend-row"
            key={segment.key}
          >
            <span
              className="ref-segment-dot"
              style={{ background: segment.color }}
            />

            <span className="ref-segment-name">
              {segment.label}
            </span>

            <span className="ref-segment-value">
              {segment.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* =========================================================
   REVIEW PROGRESS RING
   (replaces the old second "Review Progress Trend" area
   chart — same reviewed/pending totals, shown as a progress
   ring instead of a fourth near-identical area chart)
   ========================================================= */

export function ReviewProgressRing({
  data = [],
}) {
  const totals = data.reduce(
    (acc, day) => {
      acc.reviewed += Number(day?.reviewed || 0);
      acc.pending += Number(day?.pending || 0);
      return acc;
    },
    { reviewed: 0, pending: 0 }
  );

  const total = totals.reviewed + totals.pending;
  const pct = total
    ? Math.round((totals.reviewed / total) * 100)
    : 0;

  const radius = 62;
  const circumference = 2 * Math.PI * radius;
  const offset =
    circumference - (pct / 100) * circumference;

  return (
    <div className="ref-progress-ring-wrap">
      <svg
        viewBox="0 0 160 160"
        className="ref-progress-ring"
        aria-label={`${pct}% reviewed`}
      >
        <circle
          cx="80"
          cy="80"
          r={radius}
          className="ref-progress-ring-track"
        />

        <circle
          cx="80"
          cy="80"
          r={radius}
          className="ref-progress-ring-value"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: offset,
          }}
          transform="rotate(-90 80 80)"
        />

        <text
          x="80"
          y="76"
          textAnchor="middle"
          className="ref-progress-ring-pct"
        >
          {pct}%
        </text>

        <text
          x="80"
          y="94"
          textAnchor="middle"
          className="ref-progress-ring-caption"
        >
          Reviewed
        </text>
      </svg>

      <div className="ref-progress-ring-legend">
        <span>
          <i style={{ background: "#5baeb4" }} />
          Reviewed
          <b>{totals.reviewed}</b>
        </span>

        <span>
          <i style={{ background: "#dbe2e4" }} />
          Pending
          <b>{totals.pending}</b>
        </span>
      </div>
    </div>
  );
}

/* =========================================================
   SINGLE-SERIES TREND CHART
   (shared by any panel that needs one line/area over time,
   e.g. Alert history, Gmail activity, etc.)
   ========================================================= */

export function TrendAreaChart({
  data = [],
  dataKey = "value",
  labelKey = "label",
  color = "#5b8dee",
  valueLabel = "value",
  emptyMessage = "No data yet.",
}) {
  const hasData =
    data.length > 0 &&
    data.some(
      (item) => Number(item?.[dataKey] || 0) > 0
    );

  if (!data.length) {
    return (
      <p className="ref-empty-inline">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="ref-trend-chart">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart
          data={data}
          margin={{ top: 12, right: 8, left: -16, bottom: 0 }}
        >
          <defs>
            <linearGradient
              id="ref-trend-fill"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={color} stopOpacity=".28" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>

          <CartesianGrid
            vertical={false}
            strokeDasharray="3 3"
            stroke="rgba(0,0,0,.06)"
          />

          <XAxis
            dataKey={labelKey}
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

          <Tooltip
            formatter={(value) => [value, valueLabel]}
          />

          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            fill="url(#ref-trend-fill)"
          />
        </AreaChart>
      </ResponsiveContainer>

      {!hasData && (
        <p className="ref-empty-inline ref-empty-overlay">
          {emptyMessage}
        </p>
      )}
    </div>
  );
}

/* =========================================================
   RANKED BAR LIST (shared by Top Sender Domains and
   Threat Categories — same visual pattern, different data
   and accent color)
   ========================================================= */

function RankedBarList({
  data = [],
  getLabel,
  getValue,
  icon: Icon,
  emptyMessage,
  variant = "default",
}) {
  if (!data.length) {
    return (
      <p className="ref-empty-inline">
        {emptyMessage}
      </p>
    );
  }

  const max = Math.max(
    ...data.map((item) => getValue(item)),
    1
  );

  return (
    <div className="ref-domain-list">
      {data.map((item, index) => {
        const value = getValue(item);

        return (
          <div
            className="ref-domain-row"
            key={`${getLabel(item)}-${index}`}
          >
            <div className="ref-domain-name">
              <Icon size={13} strokeWidth={1.8} />
              <span>{getLabel(item)}</span>
            </div>

            <div className="ref-domain-bar-track">
              <div
                className={`ref-domain-bar-fill ${
                  variant === "risk" ? "is-risk" : ""
                }`}
                style={{
                  width: `${(value / max) * 100}%`,
                }}
              />
            </div>

            <div className="ref-domain-count">
              {value}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* =========================================================
   TOP SENDER DOMAINS
   ========================================================= */

export function TopSenderDomains({
  data = [],
}) {
  return (
    <RankedBarList
      data={data}
      getLabel={(item) => item.domain}
      getValue={(item) => item.count}
      icon={Globe}
      emptyMessage="No sender domains yet — analyze an email to see where alerts are coming from."
    />
  );
}

/* =========================================================
   THREAT CATEGORIES (from real analyzer findings)
   ========================================================= */

export function ThreatCategoryBars({
  data = [],
}) {
  return (
    <RankedBarList
      data={data.filter((item) => item.value > 0)}
      getLabel={(item) => item.name}
      getValue={(item) => item.value}
      icon={AlertTriangle}
      emptyMessage="No threat categories detected yet — analyze an email to see what's being flagged."
      variant="risk"
    />
  );
}

/* =========================================================
   CONTENT RISK (URLs / attachments / header findings —
   real counts from the analyzer, with the suspicious share
   highlighted)
   ========================================================= */

export function ContentRiskPanel({
  data = [],
}) {
  const hasSignal = data.some(
    (item) => item.total > 0
  );

  if (!hasSignal) {
    return (
      <p className="ref-empty-inline">
        No content risk signals yet — analyze an email to see URL,
        attachment and header findings.
      </p>
    );
  }

  return (
    <div className="ref-content-risk-list">
      {data.map((item) => {
        const pct = item.total
          ? Math.round(
              (item.suspicious / item.total) * 100
            )
          : 0;

        return (
          <div
            className="ref-content-risk-row"
            key={item.name}
          >
            <div className="ref-content-risk-top">
              <span className="ref-content-risk-label">
                {item.name}
              </span>

              <span className="ref-content-risk-count">
                <strong>{item.total}</strong> found
                {item.suspicious > 0 && (
                  <em>
                    {" "}
                    · {item.suspicious} suspicious
                  </em>
                )}
              </span>
            </div>

            <div className="ref-content-risk-track">
              <div
                className="ref-content-risk-fill"
                style={{
                  width: `${item.total ? 100 : 0}%`,
                }}
              />
              {item.suspicious > 0 && (
                <div
                  className="ref-content-risk-fill is-flagged"
                  style={{
                    width: `${pct}%`,
                  }}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* =========================================================
   SMALL CHART HEADER
   ========================================================= */

export function WeekButton() {
  return (
    <button
      type="button"
      className="ref-week"
    >
      Week
      <ChevronDown
        size={13}
      />
    </button>
  );
}

/* =========================================================
   ICON EXPORTS
   ========================================================= */

export {
  AlertTriangle,
  Users,
};
