// In-browser mock of the Xplore API for frontend development.
// Everything it returns is ILLUSTRATIVE: fixture: true, evidence_status "illustrative",
// engine/execution_mode/runtime/video all null. It must never be presented as a result.
//
// Testing hooks (append to the page URL before clicking "Run comparison"):
//   ?mock_fail=firm   -> that candidate fails (parent becomes "partial")
//   ?mock_fail=all    -> every candidate fails (parent becomes "failed")

import catalogFixture from "../../../shared/catalog.fixture.json";
import completedFixture from "../../../shared/experiment.fixture.json";
import partialFixture from "../../../shared/experiment.partial.fixture.json";
import type {
  Catalog,
  CandidateId,
  Experiment,
  ExperimentRequest,
  ExperimentStatus,
  Run,
  RunStatus,
  Selection,
  SelectionEntry,
  TestDefinition,
} from "../types/contract";
import { ApiRequestError } from "./errors";
import type { XploreApi } from "./types";

const catalog = catalogFixture as unknown as Catalog;
const STATIC_FIXTURES: Record<string, Experiment> = {
  "fixture-completed": completedFixture as unknown as Experiment,
  "fixture-partial": partialFixture as unknown as Experiment,
};
const FIXTURE_RUNS = new Map<CandidateId, Run>(
  (completedFixture as unknown as Experiment).runs.map((run) => [run.candidate_id, run]),
);

const QUEUE_MS = 1500;
const RUN_MS = 2500;
const STORAGE_KEY = "xplore.mock.experiments.v1";

interface MockRecord {
  request: ExperimentRequest;
  createdAt: number;
  fail: string | null;
}

function loadStore(): Record<string, MockRecord> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as Record<string, MockRecord>;
  } catch {
    return {};
  }
}

function saveStore(store: Record<string, MockRecord>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function delay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));
}

function reject(status: number, code: string, message: string): never {
  throw new ApiRequestError(status, code, message);
}

function simKey(request: ExperimentRequest): string {
  return JSON.stringify([request.test_id, [...request.candidate_ids].sort(), request.load_multiplier]);
}

function validate(request: ExperimentRequest): TestDefinition {
  const test = catalog.tests.find((t) => t.test_id === request.test_id);
  if (!test) reject(422, "unknown_test", `Unknown test_id "${request.test_id}".`);
  const ids = request.candidate_ids;
  if (!Array.isArray(ids) || ids.length === 0) reject(422, "no_candidates", "Select at least one candidate.");
  if (ids.length > test.max_candidates) reject(422, "too_many_candidates", `At most ${test.max_candidates} candidates.`);
  if (new Set(ids).size !== ids.length) reject(422, "duplicate_candidates", "Candidate IDs must be unique.");
  for (const id of ids) {
    if (!test.candidates.some((c) => c.candidate_id === id)) reject(422, "unknown_candidate", `Unknown candidate "${id}".`);
  }
  const { load, target } = test;
  if (!(request.load_multiplier >= load.min && request.load_multiplier <= load.max)) {
    reject(422, "load_out_of_range", `Load multiplier must be between ${load.min} and ${load.max}.`);
  }
  const tgt = request.target_max_deformation_pct;
  if (!(tgt >= target.min && tgt <= target.max)) {
    reject(422, "target_out_of_range", `Target must be between ${target.min}% and ${target.max}%.`);
  }
  for (const cost of Object.values(request.prototype_costs_gbp ?? {})) {
    if (cost !== null && !(cost >= 0)) reject(422, "invalid_cost", "Prototype costs must be zero or positive.");
  }
  return test;
}

/** Illustrative run: fixture curve scaled by the load multiplier. Not a simulation. */
function illustrativeRun(candidateId: CandidateId, status: RunStatus, load: number): Run {
  const base = FIXTURE_RUNS.get(candidateId);
  const empty: Run = {
    candidate_id: candidateId,
    status,
    engine: null,
    execution_mode: null,
    cache_key: null,
    metric_id: base?.metric_id ?? "compression_pct",
    deformation_pct: null,
    time_series: null,
    video_url: null,
    still_url: null,
    runtime_seconds: null,
    error: null,
  };
  if (status === "failed") {
    return {
      ...empty,
      error: { code: "numerical_instability", message: "Illustrative failure (mock): candidate excluded from the recommendation." },
    };
  }
  if (status !== "completed" || !base?.time_series) return empty;
  const values = base.time_series.deformation_pct.map((v) => Math.min(95, Math.round(v * load * 100) / 100));
  return {
    ...empty,
    cache_key: `fixture-${candidateId}-x${load}`,
    deformation_pct: Math.max(...values),
    time_series: { ...base.time_series, deformation_pct: values },
  };
}

/** Mock-only mirror of the backend's deterministic rule (plan §5, target-then-cost-v1). */
function mockSelection(request: ExperimentRequest, runs: Run[]): Selection {
  const target = request.target_max_deformation_pct;
  const costs = request.prototype_costs_gbp ?? {};
  const costOf = (id: CandidateId) => (typeof costs[id] === "number" ? (costs[id] as number) : null);

  const entries: SelectionEntry[] = runs.map((run) => ({
    candidate_id: run.candidate_id,
    outcome:
      run.status !== "completed" || run.deformation_pct === null
        ? "not_evaluated"
        : run.deformation_pct <= target
          ? "meets_target"
          : "exceeds_target",
    deformation_pct: run.status === "completed" ? run.deformation_pct : null,
    prototype_cost_gbp: costOf(run.candidate_id),
    rank: null,
  }));

  const qualifying = entries.filter((e) => e.outcome === "meets_target");
  const costRanking = qualifying.length > 0 && qualifying.every((e) => e.prototype_cost_gbp !== null);
  const byDeformationThenId = (a: SelectionEntry, b: SelectionEntry) =>
    (a.deformation_pct ?? 0) - (b.deformation_pct ?? 0) || a.candidate_id.localeCompare(b.candidate_id);
  const ordered = [...qualifying].sort((a, b) =>
    costRanking ? (a.prototype_cost_gbp ?? 0) - (b.prototype_cost_gbp ?? 0) || byDeformationThenId(a, b) : byDeformationThenId(a, b),
  );
  if (costRanking) ordered.forEach((e, i) => (e.rank = i + 1));

  const failed = runs.filter((r) => r.status !== "completed").map((r) => r.candidate_id);
  const notes: string[] = [];
  if (failed.length) notes.push(`${failed.join(", ")} did not complete, so this shortlist is provisional.`);
  if (qualifying.length === 0) notes.push("No completed candidate meets the target.");
  else if (!costRanking) notes.push("Not every qualifying candidate has a prototype cost, so no cost ranking is available.");

  return {
    rule_id: "target-then-cost-v1",
    rule_description: (completedFixture as unknown as Experiment).selection?.rule_description ?? "",
    metric_id: runs[0]?.metric_id ?? "compression_pct",
    target_max_deformation_pct: target,
    provisional: failed.length > 0,
    cost_ranking_available: costRanking,
    candidates: entries,
    shortlist: ordered.map((e) => e.candidate_id),
    recommended_candidate_id: costRanking ? ordered[0].candidate_id : null,
    notes,
  };
}

function buildExperiment(id: string, record: MockRecord, now: number): Experiment {
  const { request } = record;
  const test = catalog.tests.find((t) => t.test_id === request.test_id)!;
  const elapsed = now - record.createdAt;

  const runs = request.candidate_ids.map((candidateId, i) => {
    const start = QUEUE_MS + i * RUN_MS;
    let status: RunStatus = "queued";
    if (elapsed >= start + RUN_MS) status = record.fail === "all" || record.fail === candidateId ? "failed" : "completed";
    else if (elapsed >= start) status = "running";
    return illustrativeRun(candidateId, status, request.load_multiplier);
  });

  const done = runs.every((r) => r.status === "completed" || r.status === "failed");
  const completedCount = runs.filter((r) => r.status === "completed").length;
  let status: ExperimentStatus = elapsed < QUEUE_MS ? "queued" : "running";
  if (done) status = completedCount === runs.length ? "completed" : completedCount === 0 ? "failed" : "partial";

  const finishedAt = record.createdAt + QUEUE_MS + runs.length * RUN_MS;
  return {
    schema_version: "1.0",
    experiment_id: id,
    fixture: true,
    status,
    completed_runs: completedCount,
    total_runs: runs.length,
    runs,
    selection: done ? mockSelection(request, runs) : null,
    evidence_status: "illustrative",
    request,
    unit_system: test.unit_system,
    assumptions: test.assumptions,
    created_at: new Date(record.createdAt).toISOString(),
    completed_at: done ? new Date(finishedAt).toISOString() : null,
    versions: { api: null, runner: null, powersim_commit: null },
    checkpoint_id: null,
    config_hash: null,
    error: status === "failed" ? { code: "all_runs_failed", message: "Illustrative failure (mock): no candidate completed." } : null,
  };
}

export function createMockApi(): XploreApi {
  return {
    mode: "mock",
    baseUrl: null,
    getCatalog: () => delay(catalog),
    async createExperiment(request) {
      validate(request);
      const store = loadStore();
      const fail = new URLSearchParams(window.location.search).get("mock_fail");
      // Mirror the backend cache: identical simulation inputs finish immediately.
      const previous = Object.values(store).find((r) => simKey(r.request) === simKey(request) && r.fail === fail);
      const now = Date.now();
      const createdAt = previous ? now - (QUEUE_MS + request.candidate_ids.length * RUN_MS) : now;
      const id = `mock-${now.toString(36)}${Math.random().toString(36).slice(2, 6)}`;
      store[id] = { request, createdAt, fail };
      saveStore(store);
      return delay(buildExperiment(id, store[id], now));
    },
    async getExperiment(id) {
      if (STATIC_FIXTURES[id]) return delay(STATIC_FIXTURES[id]);
      const record = loadStore()[id];
      if (!record) reject(404, "not_found", `No experiment with ID "${id}".`);
      return delay(buildExperiment(id, record, Date.now()));
    },
    resolveArtifactUrl: (url) => url ?? null,
  };
}
