import { BrainCircuit } from "lucide-react";
import { COLORS } from "./theme";

export default function AiBadge({ label = "AI insight" }) {
  return (
    <span
      className="flex items-center gap-1 rounded-full px-2 py-1 text-[9px] font-semibold"
      style={{
        color: COLORS.ai,
        backgroundColor: "rgba(139,111,255,.12)",
      }}
    >
      <BrainCircuit size={11} strokeWidth={2} />
      {label}
    </span>
  );
}
