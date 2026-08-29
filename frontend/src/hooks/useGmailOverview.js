/**
 * Fetches Gmail connection status + mailbox dashboard data so the
 * numbers can be merged into the existing dashboard cards/charts
 * (stat row, Top Sender Domains, Alert Volume) instead of powering
 * a separate Gmail-only section.
 *
 * Dashboard data streams in progressively (10-20-30... messages at
 * a time) instead of blocking until all (up to 100) messages have
 * loaded, so the graphs/overview update live rather than sitting
 * on a long first-load wait.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getGmailStatus,
  clearGmailCache,
  streamGmailDashboard,
} from "../api/gmailApi";

export function useGmailOverview() {
  const [status, setStatus] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  // { loaded, total } while a chunked load is in progress, else null
  const [loadProgress, setLoadProgress] = useState(null);
  const [error, setError] = useState(null);

  const streamRef = useRef(null);

  const refetch = useCallback(() => {
    setError(null);

    // Cancel any stream already in flight before starting another.
    streamRef.current?.abort();

    return getGmailStatus()
      .then((statusData) => {
        setStatus(statusData);

        // Nothing to stream until Gmail is actually connected.
        if (statusData?.connected !== true) {
          setDashboard(null);
          setLoadProgress(null);
          setIsLoading(false);
          return null;
        }

        return new Promise((resolve) => {
          streamRef.current = streamGmailDashboard(
            ({ event, data }) => {
              if (event === "progress") {
                setDashboard(data);
                setLoadProgress({
                  loaded: data.loaded,
                  total: data.total,
                });
                setIsLoading(false);
              } else if (event === "complete") {
                setDashboard(data);
                setLoadProgress(null);
                setIsLoading(false);
                resolve();
              } else if (event === "error") {
                setError(data.message);
                setLoadProgress(null);
                setIsLoading(false);
                resolve();
              }
            }
          );
        });
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    setIsLoading(true);
    refetch();

    return () => streamRef.current?.abort();
  }, [refetch]);

  const sync = useCallback(async () => {
    setIsSyncing(true);
    setError(null);

    try {
      // Force a fresh chunked load instead of the old
      // fetch-everything-then-respond sync: clear the cache,
      // then refetch() will stream fresh batches in live.
      await clearGmailCache();
      await refetch();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSyncing(false);
    }
  }, [refetch]);

  const connected =
    status?.connected === true &&
    dashboard?.connected !== false;

  return {
    status,
    dashboard,
    connected,
    isLoading,
    isSyncing,
    loadProgress,
    error,
    sync,
    refetch,
  };
}
