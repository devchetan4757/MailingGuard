import { useMemo, useState } from "react";
import { AlertTriangle, Clock3, MapPin, ShieldCheck } from "lucide-react";

const VIEW_W = 760;
const VIEW_H = 360;
const PAD = 44;

function validCoord(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function project(points) {
  if (!points.length) return [];
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const latSpan = Math.max(maxLat - minLat, 8);
  const lonSpan = Math.max(maxLon - minLon, 12);
  const centerLat = (minLat + maxLat) / 2;
  const centerLon = (minLon + maxLon) / 2;
  const span = Math.max(latSpan, lonSpan * 0.55);
  const safeSpan = Math.min(350, Math.max(span * 1.35, 12));
  return points.map((p) => ({
    ...p,
    x: VIEW_W / 2 + ((p.lon - centerLon) / safeSpan) * (VIEW_W - PAD * 2),
    y: VIEW_H / 2 - ((p.lat - centerLat) / safeSpan) * (VIEW_H - PAD * 2),
  }));
}

function formatDelay(seconds) {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function hopFlag(hop) {
  return Boolean(
    hop.flagged ||
    hop.hosting ||
    hop.proxy ||
    hop.blacklist?.listed ||
    (hop.suspicious_flags || []).length
  );
}

export default function TraceMap({ origin = {}, trace = {}, compact = false }) {
  const [selected, setSelected] = useState(null);
  const hops = Array.isArray(trace.hops) ? trace.hops : [];
  const summary = trace.summary || {};

  const points = useMemo(() => project(
    hops
      .filter((hop) => validCoord(hop.lat) && validCoord(hop.lon))
      .map((hop) => ({ ...hop, flagged: hopFlag(hop) }))
  ), [hops]);

  const fallback = validCoord(origin.lat) && validCoord(origin.lon ?? origin.lng)
    ? [{ ...origin, lon: origin.lon ?? origin.lng, flagged: hopFlag(origin), order: 0 }]
    : [];
  const plotted = points.length ? points : project(fallback);
  const selectedHop = selected == null ? null : plotted[selected] || null;
  const flagged = Boolean(summary.overall_suspicious || hopFlag(origin));
  const routeLength = plotted.length;

  return (
    <div className={`ref-tracemap${compact ? " ref-tracemap--compact" : ""}`}>
      <div className="ref-tracemap-canvas" style={{ position: "relative", overflow: "hidden" }}>
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Interactive Received-header origin route"
          style={{ width: "100%", height: "auto", display: "block" }}
        >
          <defs>
            <linearGradient id="originRouteBg" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stopColor="#f8fafc" />
              <stop offset="100%" stopColor="#eef2f7" />
            </linearGradient>
            <filter id="originGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <marker id="routeArrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
              <path d="M0,0 L7,3.5 L0,7 z" fill="currentColor" />
            </marker>
          </defs>

          <rect width={VIEW_W} height={VIEW_H} fill="url(#originRouteBg)" />
          {[...Array(9)].map((_, i) => {
            const x = (VIEW_W / 8) * i;
            return <line key={`v-${i}`} x1={x} y1="0" x2={x} y2={VIEW_H} stroke="#d8dee8" strokeDasharray="2 8" />;
          })}
          {[...Array(6)].map((_, i) => {
            const y = (VIEW_H / 5) * i;
            return <line key={`h-${i}`} x1="0" y1={y} x2={VIEW_W} y2={y} stroke="#d8dee8" strokeDasharray="2 8" />;
          })}

          {plotted.length > 1 && plotted.slice(0, -1).map((point, i) => {
            const next = plotted[i + 1];
            return (
              <line
                key={`route-${i}`}
                x1={point.x} y1={point.y} x2={next.x} y2={next.y}
                stroke={point.flagged || next.flagged ? "#c82026" : "#111827"}
                strokeWidth="2.5"
                strokeDasharray="7 5"
                opacity="0.72"
                markerEnd="url(#routeArrow)"
                style={{ color: point.flagged || next.flagged ? "#c82026" : "#111827" }}
              />
            );
          })}

          {plotted.map((point, index) => {
            const active = selected === index;
            return (
              <g
                key={`${point.ip || "hop"}-${index}`}
                onClick={() => setSelected(active ? null : index)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSelected(active ? null : index); }}
                style={{ cursor: "pointer" }}
              >
                <circle cx={point.x} cy={point.y} r={active ? 15 : 11} fill={point.flagged ? "#c82026" : "#111827"} opacity="0.10" />
                <circle cx={point.x} cy={point.y} r={active ? 8 : 6} fill={point.flagged ? "#c82026" : "#111827"} filter={point.flagged ? "url(#originGlow)" : undefined} />
                <circle cx={point.x} cy={point.y} r="2" fill="#fff" />
                <text x={point.x + 10} y={point.y - 10} fontSize="11" fontWeight="700" fill="#111827">
                  H{index + 1}
                </text>
              </g>
            );
          })}

          {!plotted.length && (
            <g>
              <text x={VIEW_W / 2} y={VIEW_H / 2 - 5} textAnchor="middle" fontSize="15" fontWeight="700" fill="#475569">
                No geolocation coordinates available
              </text>
              <text x={VIEW_W / 2} y={VIEW_H / 2 + 20} textAnchor="middle" fontSize="11" fill="#64748b">
                The Received chain is still available below for investigation.
              </text>
            </g>
          )}
        </svg>

        <div style={{ position: "absolute", left: 12, top: 12, display: "flex", gap: 7, flexWrap: "wrap" }}>
          <span className="ref-origin-verdict-tag tone-ok">{routeLength} plotted hop{routeLength === 1 ? "" : "s"}</span>
          {summary.cross_border_hops > 0 && <span className="ref-origin-verdict-tag tone-warn">{summary.cross_border_hops} country transition{summary.cross_border_hops === 1 ? "" : "s"}</span>}
        </div>

        <div className={`ref-tracemap-status${flagged ? " is-flagged" : ""}`}>
          <span className="ref-tracemap-status-dot" />
          {flagged ? "Signals detected" : "No route flags"}
        </div>
      </div>

      {selectedHop && (
        <div className="ref-panel" style={{ marginTop: 10, padding: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <div>
              <strong>Hop {selectedHop.order + 1}: {selectedHop.ip || "Internal / unknown"}</strong>
              <div style={{ marginTop: 4, fontSize: 12, opacity: 0.72 }}>
                {selectedHop.hostname || selectedHop.reverse || "No hostname"} · {selectedHop.city || "Unknown city"}{selectedHop.country ? `, ${selectedHop.country}` : ""}
              </div>
            </div>
            <span className={`ref-origin-verdict-tag ${hopFlag(selectedHop) ? "tone-warn" : "tone-ok"}`}>
              {hopFlag(selectedHop) ? "Flagged" : "Clean"}
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginTop: 10, fontSize: 11 }}>
            <span><b>ASN</b><br />{selectedHop.asn || "—"}</span>
            <span><b>Network</b><br />{selectedHop.isp || selectedHop.org || "—"}</span>
            <span><b>Delay</b><br />{formatDelay(selectedHop.chain_delay_seconds)}</span>
          </div>
          {(selectedHop.suspicious_flags || []).length > 0 && (
            <div style={{ marginTop: 9, fontSize: 11 }}>
              <b>Signals:</b> {selectedHop.suspicious_flags.map((f) => f.reason.replaceAll("_", " ")).join(" · ")}
            </div>
          )}
        </div>
      )}

      <div className="ref-tracemap-readout">
        <strong>{origin.ip || "Unknown origin IP"}</strong>
        <span>{origin.city ? `${origin.city}, ${origin.country || "?"}` : "Location unavailable"}</span>
        <span>{routeLength ? "Click a hop to inspect network, ASN, timing and signals." : "No public geolocation point was returned."}</span>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 7, fontSize: 11 }}>
          <span><MapPin size={12} /> {summary.public_hops ?? 0} public</span>
          <span><ShieldCheck size={12} /> {summary.suspicious_hops ?? 0} suspicious</span>
          <span><AlertTriangle size={12} /> {summary.blacklisted_hops ?? 0} blacklisted</span>
          <span><Clock3 size={12} /> {formatDelay(summary.max_delay_seconds)} max delay</span>
        </div>
      </div>
    </div>
  );
}
