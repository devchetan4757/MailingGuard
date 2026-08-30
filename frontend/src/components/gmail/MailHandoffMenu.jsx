/**
 * Small per-row dropdown on the Gmail mail list.
 *
 * Lets a loaded message be "handed over" to one of the analysis
 * surfaces without leaving the Gmail page first — pick a target,
 * the message's raw content is fetched + analyzed on the backend,
 * and the caller (GmailPage) navigates to that surface once the
 * case is ready.
 *
 * Deliberately dumb: no fetching here, just emits onSelect(targetId).
 */

import { useEffect, useRef } from "react";
import { ChevronDown, Loader2, Radar, Send, Sparkles } from "lucide-react";

export const HANDOFF_TARGETS = [
  {
    id: "analyze",
    label: "AI Deep Analysis",
    description: "Headers, auth, links & AI risk signals",
    icon: Sparkles,
  },
  {
    id: "origin",
    label: "Origin Analysis",
    description: "Sending IP, server location & reputation",
    icon: Radar,
  },
];

export default function MailHandoffMenu({ isBusy, onSelect }) {
  const detailsRef = useRef(null);

  // Close this row's menu if the user clicks anywhere else, including
  // opening a different row's menu.
  useEffect(() => {
    function handleDocumentClick(event) {
      if (
        detailsRef.current &&
        !detailsRef.current.contains(event.target)
      ) {
        detailsRef.current.open = false;
      }
    }

    document.addEventListener("click", handleDocumentClick);
    return () =>
      document.removeEventListener("click", handleDocumentClick);
  }, []);

  function handleSelect(targetId) {
    if (detailsRef.current) detailsRef.current.open = false;
    onSelect(targetId);
  }

  return (
    <details
      className="gmail-handoff"
      ref={detailsRef}
      onClick={(event) => event.stopPropagation()}
    >
      <summary
        className="gmail-handoff-trigger"
        aria-label="Hand this email over for analysis"
      >
        {isBusy ? (
          <Loader2 size={12} className="gmail-spin" />
        ) : (
          <Send size={12} />
        )}
        {isBusy ? "Sending…" : "Analyze"}
        {!isBusy && (
          <ChevronDown size={11} className="gmail-handoff-caret" />
        )}
      </summary>

      <div className="gmail-handoff-menu" role="menu">
        {HANDOFF_TARGETS.map((target) => {
          const Icon = target.icon;

          return (
            <button
              key={target.id}
              type="button"
              role="menuitem"
              className={`gmail-handoff-item gmail-handoff-item--${target.id}`}
              disabled={isBusy}
              onClick={() => handleSelect(target.id)}
            >
              <Icon size={14} />
              <span>
                <strong>{target.label}</strong>
                <em>{target.description}</em>
              </span>
            </button>
          );
        })}
      </div>
    </details>
  );
}
