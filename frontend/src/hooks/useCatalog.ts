import { useCallback, useEffect, useState } from "react";
import { api, toApiError, type ApiRequestError } from "../api/client";
import type { Catalog } from "../types/contract";

export function useCatalog() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<ApiRequestError | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    api
      .getCatalog()
      .then((c) => !cancelled && setCatalog(c))
      .catch((e) => !cancelled && setError(toApiError(e)));
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { catalog, error, retry };
}
