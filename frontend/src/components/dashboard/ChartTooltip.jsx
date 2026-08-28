import { COLORS } from "./theme";

export default function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div
      className="rounded-[6px] border px-3 py-2 shadow-xl"
      style={{
        backgroundColor: "#0A0E1B",
        borderColor: COLORS.border,
      }}
    >
      <div
        className="mb-1 text-[9px]"
        style={{ color: COLORS.muted }}
      >
        {label}
      </div>

      {payload.map((entry) => (
        <div
          key={entry.dataKey}
          className="text-[10px]"
          style={{ color: COLORS.text }}
        >
          {entry.name}:{" "}
          <span style={{ color: entry.color || COLORS.accent }}>
            {entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}
