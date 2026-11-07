import type { ApiErrorBody, Catalog, Experiment, ExperimentRequest } from "../types/contract";
import { ApiRequestError } from "./errors";
import type { XploreApi } from "./types";

/** Client for Person B's FastAPI service (contract v1.0, plan §7). */
export function createLiveApi(baseUrl: string): XploreApi {
  const base = baseUrl.replace(/\/+$/, "");

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetch(base + path, {
        ...init,
        headers: {
          Accept: "application/json",
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
        },
      });
    } catch {
      throw new ApiRequestError(0, "network_error", `Could not reach the Xplore API at ${base}.`);
    }

    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = null;
      }
    }

    if (!response.ok) {
      const contractError = (body as ApiErrorBody | null)?.error;
      if (contractError?.message) {
        throw new ApiRequestError(response.status, contractError.code, contractError.message, contractError.details);
      }
      // FastAPI's default validation error shape: {"detail": ...}
      const detail = (body as { detail?: unknown } | null)?.detail;
      const message =
        typeof detail === "string" ? detail : `The API rejected the request (HTTP ${response.status}).`;
      throw new ApiRequestError(response.status, `http_${response.status}`, message, detail);
    }

    if (body === null) {
      throw new ApiRequestError(response.status, "invalid_response", "The API returned an empty or non-JSON response.");
    }
    return body as T;
  }

  return {
    mode: "live",
    baseUrl: base,
    getCatalog: () => request<Catalog>("/v1/catalog"),
    createExperiment: (body: ExperimentRequest) =>
      request<Experiment>("/v1/experiments", { method: "POST", body: JSON.stringify(body) }),
    getExperiment: (id: string) => request<Experiment>(`/v1/experiments/${encodeURIComponent(id)}`),
    resolveArtifactUrl: (url) => {
      if (!url) return null;
      if (/^https?:\/\//i.test(url)) return url;
      return base + (url.startsWith("/") ? url : `/${url}`);
    },
  };
}
