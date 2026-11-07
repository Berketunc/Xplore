import { useCallback, useEffect, useState } from "react";
import { api, toApiError, type ApiRequestError } from "../api/client";
import { TERMINAL_STATUSES, type Experiment } from "../types/contract";

const POLL_MS = 2000;
const MAX_BACKOFF_MS = 15000;

/**
 * Polls GET /v1/experiments/{id} about every 2 s and stops at a terminal state
 * (completed, partial, failed). Network errors back off and retry; 404 stops.
 * The last good record is kept while retrying so the view doesn't flash.
 */
export function useExperiment(id: string | null) {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [error, setError] = useState<ApiRequestError | null>(null);

  useEffect(() => {
    setError(null);
    setExperiment((prev) => (prev && prev.experiment_id === id ? prev : null));
    if (!id) return;

    let cancelled = false;
    let timer: number | undefined;
    let failures = 0;

    const tick = async () => {
      try {
        const next = await api.getExperiment(id);
        if (cancelled) return;
        failures = 0;
        setExperiment(next);
        setError(null);
        if (!TERMINAL_STATUSES.has(next.status)) timer = window.setTimeout(tick, POLL_MS);
      } catch (e) {
        if (cancelled) return;
        const err = toApiError(e);
        setError(err);
        if (err.status === 404) return;
        failures += 1;
        timer = window.setTimeout(tick, Math.min(POLL_MS * 2 ** failures, MAX_BACKOFF_MS));
      }
    };
    void tick();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [id]);

  /** Seed the view with a record we already have (e.g. the 202 response) before polling. */
  const prime = useCallback((record: Experiment) => setExperiment(record), []);

  return { experiment, error, prime };
}
