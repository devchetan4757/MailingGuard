/**
 * Epic 3 owner.
 * PROPS CONTRACT: { origin: { ip, country, city, isVpnOrHosting } }
 * TODO (Epic 3): swap the placeholder box below for a real map (e.g.
 * react-leaflet or a static map image) with a pin at the origin location.
 */

export default function TraceMap({ origin }) {
  return (
    <div className="border border-graphite/15 rounded-sm p-4 h-40 flex flex-col items-center justify-center text-center">
      <div className="w-3 h-3 rounded-full bg-graphite" />
      <p className="text-xs mt-2 font-mono">
        {origin.ip} {origin.city ? `· ${origin.city}, ${origin.country}` : ""}
      </p>
      {origin.isVpnOrHosting && (
        <p className="text-xs text-caution mt-1">hosting provider — flagged</p>
      )}
    </div>
  );
}
