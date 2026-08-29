/**
 * Epic 3 owner.
 * PROPS CONTRACT: {
 *   relatedCases: { caseId, similarity, matchedOn }[],
 *   onSelect: (caseId: string) => void
 * }
 * The signature feature - keep it visually separated from other panels
 * (see UI structure PDF, page 3).
 */

import EmptyState from "../shared/EmptyState";

export default function RelatedCasesPanel({ relatedCases, onSelect }) {
  if (relatedCases.length === 0) {
    return (
      <EmptyState
        title="No related cases yet"
        body="This is the first time we've seen anything like this sender or content."
      />
    );
  }

  return (
    <div className="border border-graphite/15 rounded-sm p-4">
      {relatedCases.map((rc) => (
        <div key={rc.caseId} className="flex justify-between items-center py-2 border-b border-graphite/10 last:border-0">
          <span className="font-mono text-sm">
            #{rc.caseId} · {rc.similarity} similarity · {rc.matchedOn.join(", ")}
          </span>
          <button
            onClick={() => onSelect(rc.caseId)}
            className="text-xs border border-graphite/30 rounded-sm px-2 py-1"
          >
            View
          </button>
        </div>
      ))}
    </div>
  );
}
