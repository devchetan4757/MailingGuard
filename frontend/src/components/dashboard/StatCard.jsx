import { COLORS } from "./theme";

export default function StatCard({
  icon: Icon,
  label,
  value,
  delta,
  danger = false,
}) {
  return (
    <div
      className="group flex min-h-[112px] flex-col justify-between rounded-[7px] border p-5 transition-colors"
      style={{
        backgroundColor: COLORS.card,
        borderColor: COLORS.border,
      }}
    >
      <div className="flex items-center justify-between">
        <div
          className="flex items-center gap-2 text-[11px] font-medium"
          style={{ color: COLORS.secondary }}
        >
          <Icon
            size={15}
            strokeWidth={1.8}
            style={{ color: COLORS.accent }}
          />

          <span>{label}</span>
        </div>

        {delta && (
          <span
            className="rounded-full px-2 py-1 text-[9px] font-bold"
            style={{
              color: danger ? COLORS.red : COLORS.accent,
              backgroundColor: danger
                ? "rgba(255,77,109,.12)"
                : "rgba(47,224,255,.10)",
            }}
          >
            {delta}
          </span>
        )}
      </div>

      <div
        className="text-[31px] font-medium leading-none tracking-[-0.055em] tabular-nums"
        style={{ color: COLORS.text }}
      >
        {value}
      </div>
    </div>
  );
}
