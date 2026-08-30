/**
 * Wraps gmailApi.getGmailMessageContent with loading/error state for
 * the mail reader modal — separate from useAnalyzeGmailMessage since
 * "open and read" and "hand over to analysis" are different actions
 * that can happen independently (and even at the same time, on
 * different rows).
 */

import { useCallback, useState } from "react";
import { getGmailMessageContent } from "../api/gmailApi";

export function useGmailMessageContent() {
  const [message, setMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const open = useCallback(async (messageId) => {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await getGmailMessageContent(messageId);
      setMessage(result);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const close = useCallback(() => {
    setMessage(null);
    setError(null);
  }, []);

  return { message, isLoading, error, open, close };
}
