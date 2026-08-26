import { useRef, useState } from "react";
import { validateUpload } from "../api/integrityApi";
import StatusPill from "./StatusPill";

const CHECKLIST = [
  { key: "extension", label: "File is a .eml" },
  { key: "size", label: "Under 2MB" },
  { key: "empty", label: "Not empty" },
  { key: "parse", label: "Parses as a valid email" },
  { key: "headers", label: "Has a From header" },
];

/** Maps a backend rejection reason to the checklist step it failed at. */
function stageForReason(reason) {
  if (!reason) return CHECKLIST.length;
  if (reason.includes("Unsupported file type")) return 0;
  if (reason.includes("exceeds the 2MB")) return 1;
  if (reason.includes("empty")) return 2;
  if (reason.includes("could not be parsed")) return 3;
  if (reason.includes("From")) return 4;
  return 0;
}

function IntakeConsole({ onSealed }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | running | done
  const [passedCount, setPassedCount] = useState(0);
  const [result, setResult] = useState(null); // { valid, reason, case }

  async function runIntake(file) {
    setStatus("running");
    setResult(null);
    setPassedCount(0);

    let response;
    let error = null;
    try {
      response = await validateUpload(file);
    } catch (err) {
      error = err.message || "Could not reach the intake service.";
    }

    const failStage = error ? 0 : stageForReason(response.reason);

    for (let i = 0; i < CHECKLIST.length; i++) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 220));
      setPassedCount(i + 1);
      if (!error && i === failStage - 1 && !response.valid) break;
      if (i === failStage && (error || !response.valid)) break;
    }

    await new Promise((resolve) => setTimeout(resolve, 200));

    if (error) {
      setResult({ valid: false, reason: error, case: null });
    } else {
      setResult(response);
      if (response.valid && response.case) {
        onSealed?.(response.case);
      }
    }
    setStatus("done");
  }

  function handleFiles(fileList) {
    const file = fileList?.[0];
    if (file) runIntake(file);
  }

  return (
    <div className="rounded-lg border border-ink-line bg-ink-panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-lg font-semibold text-parchment">
          Intake Tray
        </h2>
        <span className="font-mono text-[11px] text-muted">.eml · ≤2MB</span>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-md border-2 border-dashed px-4 py-8 text-center transition-colors ${
          dragOver
            ? "border-brass bg-brass-dim/10"
            : "border-ink-line hover:border-brass-dim"
        }`}
      >
        <p className="font-display text-base text-ink-text">
          Drop an .eml here
        </p>
        <p className="mt-1 text-xs text-muted">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept=".eml"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {status !== "idle" && (
        <div className="mt-5 space-y-2">
          {CHECKLIST.map((item, i) => {
            const reached = i < passedCount;
            const isFailure =
              status === "done" &&
              result &&
              !result.valid &&
              i === passedCount - 1;
            return (
              <div
                key={item.key}
                className="flex items-center gap-2.5 text-sm"
              >
                <span
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border font-mono text-[10px] ${
                    isFailure
                      ? "border-sealwax bg-sealwax/20 text-sealwax"
                      : reached
                      ? "border-verdigris bg-verdigris/20 text-verdigris"
                      : "border-ink-line text-muted"
                  }`}
                >
                  {isFailure ? "×" : reached ? "✓" : ""}
                </span>
                <span
                  className={
                    reached ? "text-ink-text" : "text-muted"
                  }
                >
                  {item.label}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {status === "done" && result && (
        <div className="mt-4 border-t border-ink-line pt-4">
          {result.valid ? (
            <div className="flex items-center justify-between">
              <StatusPill tone="verified">Sealed into ledger</StatusPill>
              <span className="font-mono text-[11px] text-muted">
                {result.case?.caseId}
              </span>
            </div>
          ) : (
            <div className="space-y-1">
              <StatusPill tone="broken">Rejected</StatusPill>
              <p className="text-xs text-parchment-dim">{result.reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default IntakeConsole;
