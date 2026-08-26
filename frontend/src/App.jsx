import { useState } from "react";
import IntakeConsole from "./components/IntakeConsole";
import StatusPill from "./components/StatusPill";

function App() {
  const [sealedCases, setSealedCases] = useState([]);

  return (
    <main className="min-h-screen bg-ink text-ink-text p-6">
      <div className="mx-auto max-w-xl">
        <h1 className="font-display text-3xl font-bold text-parchment">
          MailingGuard
        </h1>
        <p className="mt-1 mb-6 text-sm text-muted">
          Security &amp; Integrity — email intake console
        </p>

        <IntakeConsole onSealed={(c) => setSealedCases((prev) => [...prev, c])} />

        {sealedCases.length > 0 && (
          <div className="mt-6 space-y-2">
            <h2 className="font-display text-sm text-parchment">Sealed this session</h2>
            {sealedCases.map((c) => (
              <div key={c.caseId} className="flex items-center justify-between text-xs">
                <span className="font-mono text-muted">{c.caseId}</span>
                <StatusPill tone="verified">Sealed</StatusPill>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

export default App;
