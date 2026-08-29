// src/pages/OriginAnalysisPage.jsx
/**
 * Third interface. Not about the email content (that's AI Deep Analysis) —
 * this is the "outer" analysis: where the email actually came from
 * (sending IP, server/hosting location, network reputation).
 *
 * Boilerplate: origin currently only carries { ip, city, country,
 * isVpnOrHosting } from the API. The extra fields below (hostname, asn,
 * isp, blacklisted) are optional-chained with "—" fallbacks so this page
 * is ready to light up as soon as the backend adds them — nothing here
 * needs to change on this end when that happens.
 */

import { useNavigate } from "react-router-dom";
import {
  Radar,
  Server,
  MapPin,
  Globe2,
  Building2,
  ShieldAlert,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";

import { useCaseContext } from "../context/CaseContext";
import { DashboardPanel } from "../components/dashboard/DashboardWidgets";

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
            <button type="button" className="ref-empty-cta" onClick={() => navigate("/")}>
              Go to Dashboard
              <ArrowRight size={16} />
            </button>
          </section>
        </div>
      </main>
    );
  }

  const origin = currentCase.origin || {};
  const flagged = Boolean(origin.isVpnOrHosting || origin.blacklisted);

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">
        <header className="reference-page-head">
          <h1>
            Origin <span>Analysis</span>
          </h1>

          <div className="reference-head-actions">
            <span className="ref-origin-eyebrow-tag">CASE #{currentCase.caseId}</span>
          </div>
        </header>

        <div className="ref-grid-two">
          <DashboardPanel title="Sending origin">
            <div className="ref-origin-fields">
              <div className="ref-origin-field">
                <span>IP address</span>
                <strong>{origin.ip || "—"}</strong>
              </div>
              <div className="ref-origin-field">
                <span>Hostname</span>
                <strong>{origin.hostname || "—"}</strong>
              </div>
              <div className="ref-origin-field">
                <span>ISP / Organization</span>
                <strong>{origin.isp || "—"}</strong>
              </div>
              <div className="ref-origin-field">
                <span>ASN</span>
                <strong>{origin.asn || "—"}</strong>
              </div>
            </div>
          </DashboardPanel>

          <DashboardPanel title="Server location">
            <div className="ref-origin-map">
              <div className="ref-origin-map-pin">
                <MapPin size={20} />
              </div>
              <strong>
                {origin.city ? `${origin.city}, ${origin.country}` : "Location unavailable"}
              </strong>
              <span>{origin.region || "Region not reported"}</span>
            </div>
          </DashboardPanel>
        </div>

        <DashboardPanel title="Network signals">
          <ul className="ref-signal-list">
            <li className={`ref-signal-item level-${origin.isVpnOrHosting ? "medium" : "low"}`}>
              {origin.isVpnOrHosting ? <ShieldAlert size={15} /> : <ShieldCheck size={15} />}
              <span>
                {origin.isVpnOrHosting
                  ? "Origin IP resolves to a hosting/VPN provider, not a residential or corporate network."
                  : "Origin IP looks like a normal residential or corporate network."}
              </span>
            </li>

            <li className={`ref-signal-item level-${origin.blacklisted ? "high" : "low"}`}>
              {origin.blacklisted ? <ShieldAlert size={15} /> : <ShieldCheck size={15} />}
              <span>
                {origin.blacklisted
                  ? "This IP appears on a known spam / abuse blacklist."
                  : "No blacklist matches found for this IP."}
              </span>
            </li>
          </ul>
        </DashboardPanel>

        <div className="ref-origin-footer">
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
      </div>
    </main>
  );
}
