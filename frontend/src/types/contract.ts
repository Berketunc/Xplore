// TypeScript mirror of shared/experiment.schema.json (contract v1.0).
// Keep in sync with the schema; Person B owns the wire format.

export type SchemaVersion = "1.0";
export type CandidateId = string;

export type EvidenceStatus = "simulation_only" | "physically_compared" | "illustrative";
export type Engine = "powersim" | "analytical_baseline" | null;
export type ExecutionMode = "live" | "cached" | null;
export type ExperimentStatus = "queued" | "running" | "completed" | "partial" | "failed";
export type RunStatus = "queued" | "running" | "completed" | "failed";
export type Protocol = "compression" | "deflection";
export type Outcome = "meets_target" | "exceeds_target" | "not_evaluated";

export const TERMINAL_STATUSES: ReadonlySet<ExperimentStatus> = new Set(["completed", "partial", "failed"]);

export interface UnitSystem {
  kind: "dimensionless" | "dimensional";
  deformation: string;
  load: string;
  time: string;
  notes?: string;
}

export interface MetricDefinition {
  metric_id: string;
  label: string;
  unit: "%";
  definition: string;
  aggregation: "peak" | "settled_mean";
  window_description?: string;
}

export interface Range {
  label: string;
  unit: string;
  min: number;
  max: number;
  step?: number;
  default: number;
}

export interface CandidateDefinition {
  candidate_id: CandidateId;
  label: string;
  description: string;
  parameter: { name: string; value: number; unit: string };
}

export interface SceneDefinition {
  scene_id: string;
  display_name: string;
  description: string;
  source?: string;
  calibration: "illustrative" | "dimensionless" | "dimensional";
  preview_url?: string | null;
}

export interface TestDefinition {
  test_id: string;
  title: string;
  protocol: Protocol;
  availability: "available" | "proposed";
  engine: "powersim" | "analytical_baseline";
  scene: SceneDefinition;
  metric: MetricDefinition;
  load: Range;
  target: Range;
  candidates: CandidateDefinition[];
  max_candidates: number;
  unit_system: UnitSystem;
  assumptions: string[];
}

export interface Catalog {
  schema_version: SchemaVersion;
  fixture?: boolean;
  tests: TestDefinition[];
}

export interface ExperimentRequest {
  schema_version: SchemaVersion;
  test_id: string;
  candidate_ids: CandidateId[];
  load_multiplier: number;
  target_max_deformation_pct: number;
  prototype_costs_gbp?: Record<CandidateId, number | null>;
}

export interface TimeSeries {
  t: number[];
  deformation_pct: number[];
  t_unit: string;
  sample_interval: number;
}

export interface RunError {
  code: string;
  message: string;
}

export interface Run {
  candidate_id: CandidateId;
  status: RunStatus;
  engine: Engine;
  execution_mode: ExecutionMode;
  cache_key: string | null;
  metric_id: string;
  deformation_pct: number | null;
  time_series: TimeSeries | null;
  video_url: string | null;
  still_url?: string | null;
  runtime_seconds: number | null;
  error: RunError | null;
}

export interface SelectionEntry {
  candidate_id: CandidateId;
  outcome: Outcome;
  deformation_pct: number | null;
  prototype_cost_gbp: number | null;
  rank: number | null;
}

export interface Selection {
  rule_id: string;
  rule_description: string;
  metric_id: string;
  target_max_deformation_pct: number;
  provisional: boolean;
  cost_ranking_available: boolean;
  candidates: SelectionEntry[];
  shortlist: CandidateId[];
  recommended_candidate_id: CandidateId | null;
  notes: string[];
}

export interface Versions {
  api?: string | null;
  runner?: string | null;
  powersim_commit?: string | null;
}

export interface Experiment {
  schema_version: SchemaVersion;
  experiment_id: string;
  fixture?: boolean;
  status: ExperimentStatus;
  completed_runs: number;
  total_runs: number;
  runs: Run[];
  selection: Selection | null;
  evidence_status: EvidenceStatus;
  request?: ExperimentRequest;
  unit_system?: UnitSystem;
  assumptions?: string[];
  created_at?: string;
  completed_at?: string | null;
  versions?: Versions;
  checkpoint_id?: string | null;
  config_hash?: string | null;
  error?: RunError | null;
  physical_validation?: Record<string, unknown>;
  /** Additive backend field: numerical sensitivity of the reported metric. */
  numerical_quality?: NumericalQuality;
}

export interface NumericalQuality {
  status: string;
  note?: string;
  timestep_relative_change?: number;
  timestep_goal_relative_change?: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
