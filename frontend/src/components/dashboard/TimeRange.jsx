import { COLORS } from "./theme";

export default function TimeRange() {
  return (
    <div
      className="flex items-center rounded-[5px] border p-0.5"
      style={{
        borderColor: COLORS.border,
        backgroundColor: "#0A0E1B",
      }}
    >
      {["7D", "30D", "90D"].map((item, index) => (
        <button
          key={item}
          type="button"
          className="rounded-[4px] px-2.5 py-1 text-[9px] font-medium"
          style={{
            backgroundColor:
              index === 0 ? COLORS.elevated : "transparent",
            color:
              index === 0
                ? COLORS.accent
                : COLORS.muted,
          }}
        >
          {item}
        </button>
      ))}
    </div>
  );
}
