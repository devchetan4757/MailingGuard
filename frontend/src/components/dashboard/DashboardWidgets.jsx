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
   BREAKDOWN LINE CHART
   ========================================================= */

export function BreakdownChart({
  variant = "one",
  data = [],
}) {
  // variant "one" -> severity trend: High risk (red) vs Low risk (green)
  // variant "two" -> review trend: Reviewed vs Pending
  const seriesA =
    variant === "one" ? "red" : "reviewed";
  const seriesB =
    variant === "one" ? "green" : "pending";

  const colorA =
    variant === "one" ? "#e0685f" : "#62b7bc";
  const colorB =
    variant === "one" ? "#e8c56b" : "#8d83b9";

  const labelA =
    variant === "one" ? "High risk" : "Reviewed";
  const labelB =
    variant === "one" ? "Low risk" : "Pending";

  const chartData =
    data.length > 0
      ? data
      : [{ label: "", [seriesA]: 0, [seriesB]: 0 }];

  const pill =
    variant === "one" ? "RISK" : "REVIEW";

  return (
    <div className="ref-line-chart">
      <ResponsiveContainer width="100%" height={150}>
        <AreaChart
          data={chartData}
          margin={{ top: 8, right: 6, left: 6, bottom: 0 }}
        >
          <defs>
            <linearGradient
              id={`area-${variant}-a`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={colorA} stopOpacity=".28" />
              <stop offset="100%" stopColor={colorA} stopOpacity=".02" />
            </linearGradient>

            <linearGradient
              id={`area-${variant}-b`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={colorB} stopOpacity=".24" />
              <stop offset="100%" stopColor={colorB} stopOpacity=".02" />
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
              name === seriesA ? labelA : labelB,
            ]}
            labelFormatter={(label) => label}
          />

          <Area
            type="monotone"
            dataKey={seriesA}
            stroke={colorA}
            strokeWidth={2}
            fill={`url(#area-${variant}-a)`}
          />

          <Area
            type="monotone"
            dataKey={seriesB}
            stroke={colorB}
            strokeWidth={2}
            fill={`url(#area-${variant}-b)`}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="ref-chart-pill">
        {pill}
      </div>
    </div>
  );
}

/* =========================================================
   OPERATIONS STACKED AREA CHART
   ========================================================= */

export function OperationsChart({
  data = [],
}) {
  const chartData =
    data.length > 0
      ? data
      : [{ label: "", red: 0, yellow: 0, green: 0 }];

  return (
    <div className="ref-stacked-wrap">
      <div className="ref-legend">
        <span>
          <i className="legend-b" />
          Threats
        </span>

        <span>
          <i className="legend-c" />
          Suspicious
        </span>

        <span>
          <i className="legend-d" />
          Safe
        </span>
      </div>

      <ResponsiveContainer width="100%" height={190}>
        <AreaChart
          data={chartData}
          margin={{ top: 8, right: 6, left: 6, bottom: 0 }}
        >
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#9aa3a6" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />

          <Tooltip />

          <Area
            type="monotone"
            dataKey="red"
            stackId="ops"
            name="Threats"
            stroke="#e0685f"
            fill="#e0685f"
            fillOpacity={0.55}
          />

          <Area
            type="monotone"
            dataKey="yellow"
            stackId="ops"
            name="Suspicious"
            stroke="#e8c56b"
            fill="#e8c56b"
            fillOpacity={0.5}
          />

          <Area
            type="monotone"
            dataKey="green"
            stackId="ops"
            name="Safe"
            stroke="#62b7bc"
            fill="#62b7bc"
            fillOpacity={0.45}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/* =========================================================
   FLAGGED SECTIONS TREND (highlighted/important sections)
   ========================================================= */

export function FlaggedSectionsChart({
  data = [],
}) {
  const chartData =
    data.length > 0
      ? data
      : [{ label: "", high: 0, medium: 0, low: 0 }];

  return (
    <div className="ref-stacked-wrap">
      <div className="ref-legend">
        <span>
          <i className="legend-b" />
          Critical
        </span>

        <span>
          <i className="legend-c" />
          Moderate
        </span>

        <span>
          <i className="legend-d" />
          Minor
        </span>
      </div>

      <ResponsiveContainer width="100%" height={190}>
        <AreaChart
          data={chartData}
          margin={{ top: 8, right: 6, left: 6, bottom: 0 }}
        >
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
              name === "high"
                ? "Critical"
                : name === "medium"
                  ? "Moderate"
                  : "Minor",
            ]}
          />

          <Area
            type="monotone"
            dataKey="high"
            stackId="flags"
            name="high"
            stroke="#e0685f"
            fill="#e0685f"
            fillOpacity={0.55}
          />

          <Area
            type="monotone"
            dataKey="medium"
            stackId="flags"
            name="medium"
            stroke="#e8c56b"
            fill="#e8c56b"
            fillOpacity={0.5}
          />

          <Area
            type="monotone"
            dataKey="low"
            stackId="flags"
            name="low"
            stroke="#62b7bc"
            fill="#62b7bc"
            fillOpacity={0.45}
          />
        </AreaChart>
      </ResponsiveContainer>
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
   TOP SENDER DOMAINS
   ========================================================= */

export function TopSenderDomains({
  data = [],
}) {
  if (!data.length) {
    return (
      <p className="ref-empty-inline">
        No sender domains yet — analyze an email to see where alerts are
        coming from.
      </p>
    );
  }

  const max = Math.max(
    ...data.map((item) => item.count),
    1
  );

  return (
    <div className="ref-domain-list">
      {data.map((item) => (
        <div
          className="ref-domain-row"
          key={item.domain}
        >
          <div className="ref-domain-name">
            <Globe size={13} strokeWidth={1.8} />
            <span>{item.domain}</span>
          </div>

          <div className="ref-domain-bar-track">
            <div
              className="ref-domain-bar-fill"
              style={{
                width: `${(item.count / max) * 100}%`,
              }}
            />
          </div>

          <div className="ref-domain-count">
            {item.count}
          </div>
        </div>
      ))}
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
