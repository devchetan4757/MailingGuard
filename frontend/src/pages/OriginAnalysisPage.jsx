// src/pages/OriginAnalysisPage.jsx

import { useNavigate } from "react-router-dom";
import {
  Radar,
  Server,
  Globe2,
  Building2,
  ShieldAlert,
  ShieldCheck,
  ArrowRight,
  Hash,
  Network,
  MapPinned,
  FileDown,
  Clock3,
  Route,
  CircleDot,
} from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel } from "../components/dashboard/DashboardWidgets";
import TraceMap from "../components/results/TraceMap";

/*
 * Small, neutral country marker.
 * We intentionally avoid emoji flags because they render differently
 * across Android/browser platforms and can look like unrelated UI.
 */
function CountryMarker({ country }) {
  if (!country) return null;

  const value = String(country).trim();
  const code =
    value.length === 2
      ? value.toUpperCase()
      : value
          .split(/\s+/)
          .filter(Boolean)
          .slice(0, 2)
          .map((part) => part[0])
          .join("")
          .toUpperCase();

  return (
    <span
      className="ref-origin-country-marker"
      title={`Country: ${value}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 30,
        height: 20,
        padding: "0 7px",
        border: "1px solid rgba(148,163,184,.24)",
        borderRadius: 5,
        background: "rgba(148,163,184,.08)",
        color: "#cbd5e1",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: ".06em",
        lineHeight: 1,
        flexShrink: 0,
      }}
    >
      {code || "??"}
    </span>
  );
}

function formatDelay(hop) {
  const value =
    hop.delay_ms ??
    hop.delivery_delay_ms ??
    hop.latency_ms ??
    hop.delay;

  if (value === null || value === undefined || value === "") return null;

  const ms = Number(value);

  if (!Number.isFinite(ms)) return String(value);
  if (ms < 1000) return `${Math.round(ms)} ms`;

  return `${(ms / 1000).toFixed(ms >= 10000 ? 0 : 1)} s`;
}

function getHopSignals(hop) {
  const signals = [];

  if (hop.blacklisted) signals.push("Blacklist");
  if (hop.isVpnOrHosting || hop.vpn || hop.hosting) signals.push("Hosting/VPN");
  if (hop.geo_mismatch) signals.push("Geo mismatch");
  if (hop.suspicious) signals.push("Suspicious");
  if (hop.flagged && signals.length === 0) signals.push("Flagged");

  return signals;
}

export default function OriginAnalysisPage() {
  const navigate = useNavigate();
  const { currentCase } = useCaseContext();

  if (!currentCase) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <header className="reference-page-head">
            <h1>
              Origin <span>Analysis</span>
            </h1>
          </header>

          <section className="ref-panel ref-analysis-empty">
            <Radar size={30} strokeWidth={1.6} />
            <h3>No email analyzed yet</h3>
            <p>
              Upload an email from the dashboard to see where it actually came
              from — sending IP, server location, and network reputation.
            </p>

            <button
              type="button"
              className="ref-empty-cta"
              onClick={() => navigate("/")}
            >
              Go to Dashboard
              <ArrowRight size={16} />
            </button>
          </section>
        </div>
      </main>
    );
  }

  const origin = currentCase.origin || {};
  const originTrace = currentCase.origin_trace || {};
  const originAnalysis = currentCase.origin_analysis || {};
  const traceHops = Array.isArray(originTrace.hops)
    ? originTrace.hops
    : [];

  const traceSummary = originTrace.summary || {};
  const originRisk = originAnalysis.risk || {};
  const correlation = originAnalysis.correlation || {};

  const flagged = Boolean(
    origin.isVpnOrHosting ||
      origin.blacklisted ||
      traceSummary.overall_suspicious
  );

  const suspiciousHopCount =
    traceSummary.suspicious_hops ??
    traceHops.filter((hop) => hop.flagged || hop.suspicious).length;

  const publicHopCount =
    traceSummary.public_hops ??
    traceHops.filter((hop) => !hop.internal).length;

  const internalHopCount =
    traceSummary.internal_hops ??
    traceHops.filter((hop) => hop.internal).length;

  const delayedHopCount = traceHops.filter((hop) => {
    const delay = Number(
      hop.delay_ms ??
        hop.delivery_delay_ms ??
        hop.latency_ms ??
        hop.delay
    );

    return Number.isFinite(delay) && delay >= 5000;
  }).length;

  const countryPath = [
    ...new Set(
      traceHops
        .map((hop) => hop.country)
        .filter(Boolean)
        .map((country) => String(country))
    ),
  ];

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head">
          <h1>
            Origin <span>Analysis</span>
          </h1>

          <div className="reference-head-actions">
            <span className="ref-origin-eyebrow-tag ref-origin-eyebrow-live">
              <Radar size={12} />
              CASE #{currentCase.caseId}
            </span>
          </div>
        </header>

        <div
          className="ref-origin-verdict"
          data-severity={flagged ? "flagged" : "clean"}
        >
          <div className="ref-origin-verdict-badge">
            {flagged ? (
              <ShieldAlert size={22} />
            ) : (
              <ShieldCheck size={22} />
            )}
          </div>

          <div className="ref-origin-verdict-copy">
            <h2>
              {flagged
                ? "This origin looks suspicious"
                : "This origin looks clean"}
            </h2>

            <p>
              <strong>{origin.ip || "Unknown IP"}</strong>
              {origin.city
                ? ` · ${origin.city}, ${origin.country || "—"}`
                : " · location unavailable"}
            </p>
          </div>

          <div className="ref-origin-verdict-tags">
            <span
              className={`ref-origin-verdict-tag ${
                origin.isVpnOrHosting ? "tone-warn" : "tone-ok"
              }`}
            >
              {origin.isVpnOrHosting
                ? "Hosting / VPN"
                : "Residential / corp"}
            </span>

            <span
              className={`ref-origin-verdict-tag ${
                origin.blacklisted ? "tone-warn" : "tone-ok"
              }`}
            >
              {origin.blacklisted ? "Blacklisted" : "Not blacklisted"}
            </span>
          </div>
        </div>

        <div className="ref-grid-two">
          <DashboardPanel title="Sending origin">
            <div className="ref-origin-fields">
              <div className="ref-origin-field ref-origin-field--headline">
                <div className="ref-origin-field-icon">
                  <Network size={14} />
                </div>

                <div className="ref-origin-field-text">
                  <span>IP address</span>
                  <strong>{origin.ip || "—"}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-icon">
                  <MapPinned size={14} />
                </div>

                <div className="ref-origin-field-text">
                  <span>Hostname</span>
                  <strong>{origin.hostname || "—"}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-icon">
                  <Building2 size={14} />
                </div>

                <div className="ref-origin-field-text">
                  <span>ISP / Organization</span>
                  <strong>{origin.isp || "—"}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-icon">
                  <Hash size={14} />
                </div>

                <div className="ref-origin-field-text">
                  <span>ASN</span>
                  <strong>{origin.asn || "—"}</strong>
                </div>
              </div>
            </div>
          </DashboardPanel>

          <DashboardPanel title="Server location">
            <TraceMap origin={origin} trace={originTrace} />
          </DashboardPanel>
        </div>

        <div className="ref-grid-two">
          <DashboardPanel
            title="Origin risk"
            right={
              <span className="ref-panel-number">
                {originRisk.origin_points ?? 0}
              </span>
            }
          >
            <div className="ref-origin-fields">
              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Base score</span>
                  <strong>{originRisk.base_score ?? "?"}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Origin contribution</span>
                  <strong>+{originRisk.origin_points ?? 0}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Final score</span>
                  <strong>{originRisk.total_score ?? "?"}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Maximum Origin contribution</span>
                  <strong>
                    {originRisk.origin_max_contribution ?? "?"}
                  </strong>
                </div>
              </div>
            </div>
          </DashboardPanel>

          <DashboardPanel
            title="Trace summary"
            right={
              <span className="ref-panel-number">
                {traceHops.length}
              </span>
            }
          >
            <div className="ref-origin-fields">
              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Public hops</span>
                  <strong>{publicHopCount}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Internal hops</span>
                  <strong>{internalHopCount}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Suspicious hops</span>
                  <strong>{suspiciousHopCount}</strong>
                </div>
              </div>

              <div className="ref-origin-field">
                <div className="ref-origin-field-text">
                  <span>Delayed hops</span>
                  <strong>{delayedHopCount}</strong>
                </div>
              </div>
            </div>
          </DashboardPanel>
        </div>

        <DashboardPanel
          title="Received hop trace"
          right={
            <span className="ref-panel-number">
              {traceHops.length}
            </span>
          }
        >
          {traceHops.length === 0 ? (
            <p className="ref-empty-inline">
              No Received-chain hops were returned for this case.
            </p>
          ) : (
            <div className="ref-related-list">
              {traceHops.map((hop, index) => {
                const signals = getHopSignals(hop);
                const delay = formatDelay(hop);

                return (
                  <div
                    className="ref-related-row"
                    key={`${hop.ip || "hop"}-${index}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                    }}
                  >
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        border: "1px solid rgba(148,163,184,.24)",
                        background: hop.flagged
                          ? "rgba(248,113,113,.08)"
                          : "rgba(148,163,184,.06)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <CircleDot size={13} />
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>
                          Hop {index + 1} · {hop.ip || "Unknown IP"}
                        </strong>

                        {!hop.internal && (
                          <CountryMarker country={hop.country} />
                        )}
                      </div>

                      <span>
                        {hop.internal
                          ? "Internal / private relay"
                          : `${hop.city || "Unknown city"}${
                              hop.country ? `, ${hop.country}` : ""
                            }`}
                        {" · "}
                        {hop.asn || "ASN unavailable"}
                      </span>

                      {(hop.hostname || delay || signals.length > 0) && (
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            alignItems: "center",
                            flexWrap: "wrap",
                            marginTop: 7,
                          }}
                        >
                          {hop.hostname && (
                            <span
                              style={{
                                fontSize: 11,
                                color: "var(--text-muted, #94a3b8)",
                              }}
                            >
                              {hop.hostname}
                            </span>
                          )}

                          {delay && (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                                fontSize: 10,
                                padding: "3px 7px",
                                borderRadius: 4,
                                border:
                                  "1px solid rgba(148,163,184,.2)",
                                color: "#94a3b8",
                              }}
                            >
                              <Clock3 size={10} />
                              {delay}
                            </span>
                          )}

                          {signals.map((signal) => (
                            <span
                              key={signal}
                              style={{
                                fontSize: 10,
                                padding: "3px 7px",
                                borderRadius: 4,
                                border:
                                  "1px solid rgba(248,113,113,.22)",
                                color: "#fca5a5",
                                background: "rgba(248,113,113,.06)",
                              }}
                            >
                              {signal}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <span
                      className={`ref-origin-verdict-tag ${
                        hop.flagged ? "tone-warn" : "tone-ok"
                      }`}
                    >
                      {hop.flagged ? "Flagged" : "Clean"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </DashboardPanel>

        <DashboardPanel title="Route intelligence">
          <div className="ref-origin-fields">
            <div className="ref-origin-field">
              <div className="ref-origin-field-icon">
                <Route size={14} />
              </div>

              <div className="ref-origin-field-text">
                <span>Countries traversed</span>
                <strong>
                  {countryPath.length
                    ? countryPath.join(" → ")
                    : "Unavailable"}
                </strong>
              </div>
            </div>

            <div className="ref-origin-field">
              <div className="ref-origin-field-icon">
                <Globe2 size={14} />
              </div>

              <div className="ref-origin-field-text">
                <span>Unique countries</span>
                <strong>{countryPath.length}</strong>
              </div>
            </div>

            <div className="ref-origin-field">
              <div className="ref-origin-field-icon">
                <Network size={14} />
              </div>

              <div className="ref-origin-field-text">
                <span>Unique ASNs</span>
                <strong>
                  {
                    new Set(
                      traceHops
                        .map((hop) => hop.asn)
                        .filter(Boolean)
                    ).size
                  }
                </strong>
              </div>
            </div>

            <div className="ref-origin-field">
              <div className="ref-origin-field-icon">
                <Clock3 size={14} />
              </div>

              <div className="ref-origin-field-text">
                <span>Delayed hops</span>
                <strong>{delayedHopCount}</strong>
              </div>
            </div>
          </div>
        </DashboardPanel>

        <DashboardPanel title="Correlation">
          <div className="ref-origin-fields">
            <div className="ref-origin-field">
              <div className="ref-origin-field-text">
                <span>Matching IP count</span>
                <strong>{correlation.ip_count ?? 0}</strong>
              </div>
            </div>

            <div className="ref-origin-field">
              <div className="ref-origin-field-text">
                <span>Matching ASN count</span>
                <strong>{correlation.asn_count ?? 0}</strong>
              </div>
            </div>

            <div className="ref-origin-field">
              <div className="ref-origin-field-text">
                <span>Recent related cases</span>
                <strong>
                  {(correlation.recent_case_ids || []).length}
                </strong>
              </div>
            </div>
          </div>
        </DashboardPanel>

        {originRisk.origin_breakdown && (
          <DashboardPanel title="Risk signals">
            <ul className="ref-signal-list">
              {Object.entries(originRisk.origin_breakdown).map(
                ([key, active]) => (
                  <li
                    className={`ref-signal-item level-${
                      active ? "high" : "low"
                    }`}
                    key={key}
                  >
                    <span className="ref-signal-icon">
                      {active ? (
                        <ShieldAlert size={14} />
                      ) : (
                        <ShieldCheck size={14} />
                      )}
                    </span>

                    <span>
                      {key.replaceAll("_", " ")}
                      {active ? " · detected" : " · not detected"}
                    </span>
                  </li>
                )
              )}
            </ul>
          </DashboardPanel>
        )}

        {originTrace.geo_failures?.length > 0 && (
          <DashboardPanel title="Geo lookup warnings">
            <ul className="ref-signal-list">
              {originTrace.geo_failures.map((failure, index) => (
                <li
                  className="ref-signal-item level-medium"
                  key={`${failure.ip}-${index}`}
                >
                  <span className="ref-signal-icon">
                    <ShieldAlert size={14} />
                  </span>

                  <span>
                    {failure.ip}:{" "}
                    {failure.message ||
                      "Geolocation lookup failed"}
                  </span>
                </li>
              ))}
            </ul>
          </DashboardPanel>
        )}

        <DashboardPanel title="Network signals">
          <ul className="ref-signal-list">
            <li
              className={`ref-signal-item level-${
                origin.isVpnOrHosting ? "medium" : "low"
              }`}
            >
              <span className="ref-signal-icon">
                {origin.isVpnOrHosting ? (
                  <ShieldAlert size={14} />
                ) : (
                  <ShieldCheck size={14} />
                )}
              </span>

              <span>
                {origin.isVpnOrHosting
                  ? "Origin IP resolves to a hosting/VPN provider, not a residential or corporate network."
                  : "Origin IP looks like a normal residential or corporate network."}
              </span>
            </li>

            <li
              className={`ref-signal-item level-${
                origin.blacklisted ? "high" : "low"
              }`}
            >
              <span className="ref-signal-icon">
                {origin.blacklisted ? (
                  <ShieldAlert size={14} />
                ) : (
                  <ShieldCheck size={14} />
                )}
              </span>

              <span>
                {origin.blacklisted
                  ? "This IP appears on a known spam / abuse blacklist."
                  : "No blacklist matches found for this IP."}
              </span>
            </li>
          </ul>
        </DashboardPanel>

        <div
          className="ref-origin-footer"
          data-severity={flagged ? "flagged" : "clean"}
        >
          <div className="ref-origin-footer-icon">
            <Server size={14} />
          </div>

          <div className="ref-origin-footer-icon">
            <Globe2 size={14} />
          </div>

          <div className="ref-origin-footer-icon">
            <Building2 size={14} />
          </div>

          <span>
            {flagged
              ? "This origin carries at least one network-level red flag — cross-check it against the AI Deep Analysis page before closing the case."
              : "No network-level red flags on this origin."}
          </span>
        </div>

        <div className="ref-analysis-actions">
          <button
            type="button"
            className="ref-download-btn"
            onClick={() => navigate("/reports")}
          >
            <FileDown size={16} />
            Preview &amp; download full report
          </button>
        </div>
      </div>
    </main>
  );
}
