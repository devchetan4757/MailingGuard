/**
 * Epic 2 owner (reads Epic 1's parsed header data).
 * PROPS CONTRACT: { headerChecks: { spf, dkim, dmarc, senderDomainMismatch } }
 * Explainable over flashy - every check shows plain-language reasoning
 * next to it, never a bare pass/fail.
 */

const LABELS = {
  spf: "SPF",
  dkim: "DKIM",
  dmarc: "DMARC",
};

const EXPLANATIONS = {
  spf: "Confirms the sending server was allowed to send on this domain's behalf.",
  dkim: "Confirms the message wasn't altered in transit.",
  dmarc: "Confirms the domain publishes a policy for handling failed checks.",
};

export default function HeaderChecklist({ headerChecks }) {
  const rows = ["spf", "dkim", "dmarc"];

  return (
    <div className="border border-graphite/15 rounded-sm p-4 font-mono text-sm">
      {rows.map((key) => (
        <div key={key} className="flex justify-between py-1">
          <span>
            {LABELS[key]}{" "}
            <span className={headerChecks[key] === "fail" ? "text-flagged" : "text-verified"}>
              {headerChecks[key]}
            </span>
          </span>
          <span className="text-graphite/50 text-xs">{EXPLANATIONS[key]}</span>
        </div>
      ))}
      {headerChecks.senderDomainMismatch && (
        <div className="text-flagged text-xs mt-2">
          Sender display name doesn't match the reply-to domain.
        </div>
      )}
    </div>
  );
}
