import { createLiveApi } from "./live";
import { createMockApi } from "./mock";
import type { ApiMode, XploreApi } from "./types";

export { ApiRequestError, toApiError } from "./errors";
export type { ApiMode, XploreApi } from "./types";

const mode: ApiMode = import.meta.env.VITE_API_MODE === "live" ? "live" : "mock";

export const api: XploreApi =
  mode === "live" ? createLiveApi(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") : createMockApi();

/** Genuine saved example for the demo (live), or the illustrative fixture (mock). */
export const EXAMPLE_EXPERIMENT_ID: string | null =
  import.meta.env.VITE_EXAMPLE_EXPERIMENT_ID || (mode === "mock" ? "fixture-completed" : null);
