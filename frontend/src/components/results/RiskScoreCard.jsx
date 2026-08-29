/**
 * Epic 2 owner.
 * PROPS CONTRACT: { riskScore: number, severity: "green"|"yellow"|"red" }
 * Most important information, top of the results page - see UI structure
 * PDF page 3. Don't bury this below other panels.
 */

import Badge from "./Badge";

const RING_COLOR = {
  green: "border-verified",
  yellow: "border-caution",
  red: "border-flagged",
};

export default function RiskScoreCard({ riskScore, severity }) {
  return (
    <div className="flex items-center gap-4 border border-graphite/15 rounded-sm p-4">
      <div className={`w-16 h-16 rounded-full border-4 flex items-center justify-center font-mono text-lg ${RING_COLOR[severity]}`}>
        {riskScore}
      </div>
      <div>
        <p className="font-serif text-base text-graphite">Fraud risk score</p>
        <Badge severity={severity}>
          {severity === "red" ? "high risk" : severity === "yellow" ? "medium risk" : "low risk"}
        </Badge>
      </div>
    </div>
  );
}
