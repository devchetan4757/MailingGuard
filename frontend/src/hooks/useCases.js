/**
 * Epic 4 owner — wraps casesApi with loading/error state for HistoryPage.
 */

import { useCallback, useEffect, useState } from "react";
import { listCases } from "../api/casesApi";

export function useCases() {
  const [cases, setCases] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Only the initial mount sets isLoading — subsequent refetch() calls
  // (e.g. after an upload) update `cases` in place without blanking
  // whatever's already on screen.
  const refetch = useCallback(() => {
    setError(null);
    return listCases()
      .then(setCases)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    setIsLoading(true);
    refetch().finally(() => setIsLoading(false));
  }, [refetch]);

  return { cases, isLoading, error, refetch };
}
