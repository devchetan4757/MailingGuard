import { COLORS } from "./theme";

export default function ChartHeaderValue({ value, label }) {
  return (
    <div className="mt-2 flex items-baseline gap-2">
      <span
        className="text-[27px] font-medium leading-none tracking-[-0.05em] tabular-nums"
        style={{ color: COLORS.text }}
      >
        {value}
      </span>

      <span
        className="text-[10px]"
        style={{ color: COLORS.muted }}
      >
        {label}
      </span>
    </div>
  );
}
