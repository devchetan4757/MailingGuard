/**
 * Epic 1 owner (or whoever owns UploadPage) — wraps emailApi.analyzeEmail
 * with loading/error state for the email analysis flow.
 */

import { useState } from "react";
import { analyzeEmail } from "../api/emailApi";

export function useAnalyzeEmail() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  async function analyze(file) {
    setIsLoading(true);
    setError(null);
    try {
      const result = await analyzeEmail(file);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }

  return { analyze, isLoading, error };
}
