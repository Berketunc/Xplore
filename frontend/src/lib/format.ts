import type { Engine, EvidenceStatus, ExecutionMode, ExperimentStatus, RunStatus } from "../types/contract";

export const pct = (value: number | null | undefined, digits = 1) =>
  value === null || value === undefined || !Number.isFinite(value) ? "—" : `${value.toFixed(digits)}%`;

export const gbp = (value: number | null | undefined) =>
  value === null || value === undefined || !Number.isFinite(value) ? "—" : `£${value.toFixed(2)}`;

export const seconds = (value: number | null | undefined) => {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (value < 60) return `${value.toFixed(1)} s`;
  return `${Math.floor(value / 60)} min ${Math.round(value % 60)} s`;
};

export const multiplier = (value: number) => `${Number.isInteger(value) ? value.toFixed(1) : value}×`;

export const dateTime = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
};

export const EVIDENCE_LABEL: Record<EvidenceStatus, string> = {
  simulation_only: "Simulation result · physical validation pending",
  physically_compared: "Compared with a physical experiment",
  illustrative: "Illustrative preview",
};

export const engineLabel = (engine: Engine) =>
  engine === "powersim" ? "PowerSim" : engine === "analytical_baseline" ? "Analytical baseline" : "No engine (fixture)";

export const executionLabel = (mode: ExecutionMode) =>
  mode === "live" ? "Live run" : mode === "cached" ? "Cached run" : "—";

export const EXPERIMENT_STATUS_LABEL: Record<ExperimentStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  partial: "Partially completed",
  failed: "Failed",
};

export const RUN_STATUS_LABEL: Record<RunStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

export const listJoin = (items: string[]) =>
  items.length <= 1 ? (items[0] ?? "") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
