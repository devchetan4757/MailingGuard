/**
 * Wraps gmailApi.analyzeGmailMessage with loading/error state, the
 * same shape as useAnalyzeEmail — except state is keyed by message
 * id so the Gmail mail list can show a spinner on just the one row
 * being handed over, instead of blocking the whole list.
 */

import { useState } from "react";
import { analyzeGmailMessage } from "../api/gmailApi";

export function useAnalyzeGmailMessage() {
  const [pendingId, setPendingId] = useState(null);
  const [error, setError] = useState(null);

  async function analyze(messageId) {
    setPendingId(messageId);
    setError(null);
    try {
      const result = await analyzeGmailMessage(messageId);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setPendingId(null);
    }
  }

  return { analyze, pendingId, error };
}
