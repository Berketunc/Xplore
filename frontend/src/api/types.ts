import type { Catalog, Experiment, ExperimentRequest } from "../types/contract";

export type ApiMode = "mock" | "live";

export interface XploreApi {
  mode: ApiMode;
  baseUrl: string | null;
  getCatalog(): Promise<Catalog>;
  createExperiment(request: ExperimentRequest): Promise<Experiment>;
  getExperiment(id: string): Promise<Experiment>;
  /** Turn a (possibly relative) artifact URL from the API into a browser URL. */
  resolveArtifactUrl(url: string | null | undefined): string | null;
}
