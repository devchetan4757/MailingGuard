import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import { divIcon } from "leaflet";
import { useEffect } from "react";
import "../../styles/analysis.css";

function MapViewport({ lat, lng }) {
  const map = useMap();

  useEffect(() => {
    if (
      typeof lat === "number" &&
      typeof lng === "number" &&
      !Number.isNaN(lat) &&
      !Number.isNaN(lng)
    ) {
      map.setView([lat, lng], 6);
    }
  }, [lat, lng, map]);

  return null;
}

const locationBeaconIcon = divIcon({
  className: "trace-map-beacon-icon",
  html: `
    <span class="trace-map-beacon">
      <span class="trace-map-beacon__ring"></span>
      <span class="trace-map-beacon__dot"></span>
    </span>
  `,
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

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
      ? traceHops.map((hop, index) => ({
          ...hop,
          flagged: Boolean(
            hop.flagged ||
            hop.blacklisted ||
            hop.isVpnOrHosting ||
            hop.hosting ||
            hop.proxy ||
            (index === 0 && flagged)
          ),
        }))
      : hasCoords
        ? [{
            ...origin,
            lat: origin.lat,
            lon: origin.lng,
            flagged,
          }]
        : [];

  const route = plottedHops.map((hop) => [
    hop.lat,
    hop.lon,
  ]);

  const defaultCenter = hasCoords
    ? [origin.lat, origin.lng]
    : [20, 0];

  return (
    <div
      className={`ref-tracemap${
        compact ? " ref-tracemap--compact" : ""
      }`}
    >
      <div
        className={`ref-tracemap-canvas${
          flagged ? " is-flagged" : ""
        }`}
      >
        <MapContainer
          center={defaultCenter}
          zoom={hasCoords ? 6 : 2}
          scrollWheelZoom={true}
            attributionControl={false}
          style={{
            width: "100%",
            height: compact ? "260px" : "360px",
            minHeight: compact ? "260px" : "360px",
          }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
{hasCoords && (
            <MapViewport
              lat={origin.lat}
              lng={origin.lng}
            />
          )}

          {route.length > 1 && (
            <Polyline
              positions={route}
              interactive={false}
              pathOptions={{
                weight: 3,
                opacity: 0.8,
              }}
            />
          )}

          {plottedHops.map((hop, index) => {
            const hopFlagged = Boolean(hop.flagged);

            return (
              <div key={`${hop.ip || "hop"}-${index}`}>
                <Marker
                  position={[hop.lat, hop.lon]}
                  icon={locationBeaconIcon}
                  interactive={false}
                  zIndexOffset={1000}
                />
              </div>
            );
          })}
        </MapContainer>

        <div
          className={`ref-tracemap-status${
            flagged ? " is-flagged" : ""
          }`}
        >
          <span className="ref-tracemap-status-dot" />
          {flagged ? "Flagged" : "Clean"}
        </div>
      </div>

      <div className="ref-tracemap-readout">
        <strong>{origin.ip || "Unknown IP"}</strong>
        <span>
          {origin.city
            ? `${origin.city}, ${origin.country || "?"}`
            : "Location unavailable"}
        </span>

        {plottedHops.length > 1 && (
          <span>
            {plottedHops.length} geolocated hops connected
          </span>
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





