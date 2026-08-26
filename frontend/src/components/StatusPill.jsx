const TONES = {
  verified: "bg-verdigris-dim/40 text-verdigris border-verdigris-dim",
  broken: "bg-sealwax-dim/40 text-sealwax border-sealwax-dim",
  pending: "bg-ink-line/60 text-muted border-ink-line",
  flagged: "bg-brass-dim/30 text-brass border-brass-dim",
};

/** Small uppercase label used across the module for case/chain state. */
function StatusPill({ tone = "pending", children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider ${TONES[tone]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export default StatusPill;
