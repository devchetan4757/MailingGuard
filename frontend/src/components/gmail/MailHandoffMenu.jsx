/**
 * Small per-row "Analyze" trigger on the Gmail mail list.
 *
 * Lets a loaded message be handed over to the analysis pipeline without
 * leaving the Gmail page first — the message's raw content is fetched +
 * analyzed on the backend, and the caller (GmailPage) navigates to the
 * parsing page once the case is ready. From there the user can choose
 * to go deeper into AI Deep Analysis or Origin Analysis themselves.
 *
 * Deliberately dumb: no fetching here, just emits onSelect().
 */

import { Loader2, Send } from "lucide-react";

export default function MailHandoffMenu({ isBusy, onSelect }) {
  return (
    <button
      type="button"
      className="gmail-handoff-trigger"
      aria-label="Analyze this email"
      disabled={isBusy}
      onClick={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      {isBusy ? (
        <Loader2 size={12} className="gmail-spin" />
      ) : (
        <Send size={12} />
      )}
      {isBusy ? "Sending…" : "Analyze"}
    </button>
  );
}
