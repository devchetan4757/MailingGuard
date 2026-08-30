/**
 * Epic 3 — origin visualization.
 *
 * PROPS CONTRACT: { origin: { ip, country, city, lat, lng, isVpnOrHosting },
 *                    compact?: boolean }
 *
 * Renders an equirectangular lat/lng plot with the origin pinned at its
 * true coordinates. We don't have a coastline dataset bundled (and no
 * network access to fetch one honestly), so rather than fake a world map
 * silhouette, this draws an accurate graticule (lat/lng grid, equator +
 * prime meridian highlighted) and plots the pin precisely, styled like an
 * instrument readout (corner coordinates, signal rings) rather than a
 * plain box. If the backend ever ships a tile/coastline source, swap the
 * <svg> body below for it — the projection math (lngToX / latToY) stays
 * the same.
 */

const VIEW_W = 360;
const VIEW_H = 180;

function lngToX(lng) {
  return ((lng + 180) / 360) * VIEW_W;
}

function latToY(lat) {
  return ((90 - lat) / 180) * VIEW_H;
}

const GRID_LINES_LNG = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150];
const GRID_LINES_LAT = [-60, -30, 0, 30, 60];

function hemi(value, positiveLabel, negativeLabel) {
  return `${Math.abs(value).toFixed(2)}° ${value >= 0 ? positiveLabel : negativeLabel}`;
}

export default function TraceMap({
  origin = {},
  trace = {},
  compact = false,
}) {
  const hasCoords =
    typeof origin.lat === "number" &&
    typeof origin.lng === "number" &&
    !Number.isNaN(origin.lat) &&
    !Number.isNaN(origin.lng);

  const flagged = Boolean(
    origin.isVpnOrHosting ||
    origin.blacklisted ||
    trace.summary?.overall_suspicious
  );

  const traceHops = Array.isArray(trace.hops)
    ? trace.hops.filter(
        (hop) =>
          typeof hop.lat === "number" &&
          typeof hop.lon === "number" &&
          !Number.isNaN(hop.lat) &&
          !Number.isNaN(hop.lon)
      )
    : [];

  const plottedHops =
    traceHops.length > 0
      ? traceHops
      : hasCoords
        ? [{
            ...origin,
            lat: origin.lat,
            lon: origin.lng,
            flagged,
          }]
        : [];

  const points = plottedHops.map((hop) => ({
    ...hop,
    x: lngToX(hop.lon),
    y: latToY(hop.lat),
  }));

  const pinX = hasCoords ? lngToX(origin.lng) : null;
  const pinY = hasCoords ? latToY(origin.lat) : null;

  return (
    <div className={`ref-tracemap${compact ? " ref-tracemap--compact" : ""}`}>
      <div className={`ref-tracemap-canvas${flagged ? " is-flagged" : ""}`}>
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={
            hasCoords
              ? `Origin location plotted at latitude ${origin.lat.toFixed(2)}, longitude ${origin.lng.toFixed(2)}`
              : "Origin location unavailable"
          }
        >
          <defs>
            <radialGradient id="tracemap-vignette" cx="50%" cy="42%" r="75%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
            </radialGradient>
          </defs>

          <rect x="0" y="0" width={VIEW_W} height={VIEW_H} className="ref-tracemap-bg" />
          <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="url(#tracemap-vignette)" />

          {GRID_LINES_LNG.map((lng) => (
            <line
              key={`lng-${lng}`}
              x1={lngToX(lng)}
              y1={0}
              x2={lngToX(lng)}
              y2={VIEW_H}
              className="ref-tracemap-grid"
            />
          ))}

          {GRID_LINES_LAT.map((lat) => (
            <line
              key={`lat-${lat}`}
              x1={0}
              y1={latToY(lat)}
              x2={VIEW_W}
              y2={latToY(lat)}
              className="ref-tracemap-grid"
            />
          ))}

          {/* Prime meridian + equator, emphasized */}
          <line x1={lngToX(0)} y1={0} x2={lngToX(0)} y2={VIEW_H} className="ref-tracemap-axis" />
          <line x1={0} y1={latToY(0)} x2={VIEW_W} y2={latToY(0)} className="ref-tracemap-axis" />

          {points.length > 1 && (
            <polyline
              points={points.map((point) => `${point.x},${point.y}`).join(" ")}
              className="ref-tracemap-route"
              fill="none"
            />
          )}

          {points.map((point, index) => (
            <g
              key={`${point.ip || "point"}-${index}`}
              className={point.flagged ? "ref-tracemap-pin is-flagged" : "ref-tracemap-pin"}
            >
              <circle
                cx={point.x}
                cy={point.y}
                r={index === 0 ? "8" : "6"}
                className="ref-tracemap-ring ref-tracemap-ring--inner"
              />
              {point.flagged && (
                <circle
                  cx={point.x}
                  cy={point.y}
                  r="7"
                  className="ref-tracemap-pulse"
                />
              )}
              <circle cx={point.x} cy={point.y} r="2.8" className="ref-tracemap-dot" />
              <circle cx={point.x} cy={point.y} r="1" className="ref-tracemap-dot-core" />
            </g>
          ))}

          {hasCoords && (
            <>
              <line x1={pinX} y1="0" x2={pinX} y2={VIEW_H} className="ref-tracemap-crosshair" />
              <line x1="0" y1={pinY} x2={VIEW_W} y2={pinY} className="ref-tracemap-crosshair" />
            </>
          )}

          <rect
            x="0.5"
            y="0.5"
            width={VIEW_W - 1}
            height={VIEW_H - 1}
            className="ref-tracemap-border"
          />
        </svg>

        {points.length > 0 && (
          <div className="ref-tracemap-coords">
            <span>{hemi(points[0].lat, "N", "S")}</span>
            <span>{hemi(points[0].lon, "E", "W")}</span>
          </div>
        )}

        <div className={`ref-tracemap-status${flagged ? " is-flagged" : ""}`}>
          <span className="ref-tracemap-status-dot" />
          {flagged ? "Flagged" : "Clean"}
        </div>
      </div>

      <div className="ref-tracemap-readout">
        <strong>{origin.ip || "Unknown IP"}</strong>
        <span>
          {origin.city ? `${origin.city}, ${origin.country || "?"}` : "Location unavailable"}
        </span>
        {points.length > 1 && (
          <span>{points.length} geolocated hops connected</span>
        )}
        {flagged && (
          <span className="ref-tracemap-flag">
            network signal flagged
          </span>
        )}
      </div>
    </div>
  );
}
