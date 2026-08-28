/**
 * Epic 4 owner.
 * PROPS CONTRACT: { caseSummary: { caseId, riskScore, severity, analyzedAt }, onClick: () => void }
 * Same score badge colour logic as the results screen (master doc, section 9).
 */

import Badge from "../results/Badge";

export default function HistoryListItem({ caseSummary, onClick }) {
  return (
    <div
      onClick={onClick}
      className="grid grid-cols-[90px_60px_1fr_140px_20px] items-center py-2 border-b border-graphite/10 cursor-pointer font-mono text-sm"
    >
      <span>#{caseSummary.caseId}</span>
      <Badge severity={caseSummary.severity}>{caseSummary.riskScore}</Badge>
      <span />
      <span className="text-xs text-graphite/60">{caseSummary.analyzedAt}</span>
      <span>›</span>
    </div>
  );
}
