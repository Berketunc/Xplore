import type { FormEvent } from "react";
import type { ExperimentRequest, TestDefinition } from "../types/contract";
import { seriesColor } from "../lib/colors";
import { multiplier } from "../lib/format";
import { Card, Pill, SeriesKey, Spinner } from "./ui";

export interface SetupState {
  candidateIds: string[];
  load: number;
  target: string;
  costs: Record<string, string>;
}

export function initialSetup(test: TestDefinition): SetupState {
  return {
    candidateIds: test.candidates.slice(0, test.max_candidates).map((c) => c.candidate_id),
    load: test.load.default,
    target: String(test.target.default),
    costs: {},
  };
}

export function setupFromRequest(test: TestDefinition, request: ExperimentRequest): SetupState {
  const costs: Record<string, string> = {};
  for (const [id, cost] of Object.entries(request.prototype_costs_gbp ?? {})) {
    if (typeof cost === "number") costs[id] = String(cost);
  }
  return {
    candidateIds: request.candidate_ids.filter((id) => test.candidates.some((c) => c.candidate_id === id)),
    load: request.load_multiplier,
    target: String(request.target_max_deformation_pct),
    costs,
  };
}

function loadOptions(test: TestDefinition): number[] | null {
  const { min, max, step } = test.load;
  if (!step || step <= 0) return null;
  const count = Math.floor((max - min) / step + 1e-9) + 1;
  if (count > 8) return null;
  return Array.from({ length: count }, (_, i) => Math.round((min + i * step) * 1000) / 1000);
}

interface Validation {
  errors: { candidates?: string; target?: string; costs?: string };
  request: ExperimentRequest | null;
}

export function validateSetup(test: TestDefinition, state: SetupState): Validation {
  const errors: Validation["errors"] = {};
  if (state.candidateIds.length === 0) errors.candidates = "Select at least one candidate.";
  else if (state.candidateIds.length > test.max_candidates) errors.candidates = `Select at most ${test.max_candidates}.`;

  const target = Number(state.target);
  if (state.target.trim() === "" || !Number.isFinite(target)) errors.target = "Enter a target.";
  else if (target < test.target.min || target > test.target.max) errors.target = `Between ${test.target.min} and ${test.target.max}%.`;

  const costs: Record<string, number> = {};
  for (const id of state.candidateIds) {
    const raw = (state.costs[id] ?? "").trim();
    if (raw === "") continue;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) errors.costs = "Costs must be zero or a positive number.";
    else costs[id] = value;
  }

  if (Object.keys(errors).length) return { errors, request: null };
  // Keep catalog order so identical inputs produce identical requests (cache-friendly).
  const ordered = test.candidates.map((c) => c.candidate_id).filter((id) => state.candidateIds.includes(id));
  return {
    errors,
    request: {
      schema_version: "1.0",
      test_id: test.test_id,
      candidate_ids: ordered,
      load_multiplier: state.load,
      target_max_deformation_pct: target,
      ...(Object.keys(costs).length ? { prototype_costs_gbp: costs } : {}),
    },
  };
}

interface Props {
  test: TestDefinition;
  value: SetupState;
  onChange: (next: SetupState) => void;
  onSubmit: (request: ExperimentRequest) => void;
  submitting: boolean;
  running: boolean;
  blockedReason: string | null;
}

export function SetupForm({ test, value, onChange, onSubmit, submitting, running, blockedReason }: Props) {
  const { errors, request } = validateSetup(test, value);
  const options = loadOptions(test);
  const disabled = submitting || running || !!blockedReason || !request;

  const toggleCandidate = (id: string) => {
    const selected = value.candidateIds.includes(id);
    if (!selected && value.candidateIds.length >= test.max_candidates) return;
    onChange({ ...value, candidateIds: selected ? value.candidateIds.filter((c) => c !== id) : [...value.candidateIds, id] });
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!disabled && request) onSubmit(request);
  };

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <Card
        title={test.title}
        aside={test.availability === "proposed" ? <Pill tone="warning">Proposed · not yet confirmed</Pill> : <Pill>Available</Pill>}
      >
        <p className="text-sm font-medium text-ink">{test.scene.display_name}</p>
        <p className="mt-1 text-sm text-ink-2">{test.scene.description}</p>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <dt className="text-ink-muted">Protocol</dt>
          <dd className="capitalize text-ink-2">{test.protocol}</dd>
          <dt className="text-ink-muted">Metric</dt>
          <dd className="text-ink-2">{test.metric.label}</dd>
          <dt className="text-ink-muted">Units</dt>
          <dd className="text-ink-2">{test.unit_system.kind === "dimensionless" ? "Relative (dimensionless)" : "Dimensional"}</dd>
        </dl>
      </Card>

      <Card title="Candidates" aside={`Choose up to ${test.max_candidates}`}>
        <fieldset>
          <legend className="sr-only">Candidate parameter scenarios</legend>
          <ul className="space-y-2">
            {test.candidates.map((c) => {
              const checked = value.candidateIds.includes(c.candidate_id);
              const full = !checked && value.candidateIds.length >= test.max_candidates;
              return (
                <li key={c.candidate_id}>
                  <label
                    className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                      checked ? "border-ink/30 bg-surface-2" : "border-hairline hover:bg-surface-2/60"
                    } ${full || running ? "cursor-not-allowed opacity-60" : ""}`}
                  >
                    <input
                      type="checkbox"
                      className="mt-1 accent-[var(--ink)]"
                      checked={checked}
                      disabled={full || running}
                      onChange={() => toggleCandidate(c.candidate_id)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2 text-sm font-medium text-ink">
                        <SeriesKey color={seriesColor(test.candidates, c.candidate_id)} />
                        {c.label}
                      </span>
                      <span className="mt-0.5 block text-xs text-ink-2">
                        {c.description} · {multiplier(c.parameter.value)} {c.parameter.unit.replace(/^x\s*/i, "")}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
          {errors.candidates && <p className="mt-2 text-xs text-critical">{errors.candidates}</p>}
        </fieldset>
      </Card>

      <Card title="Loading and target">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium text-ink-2" id="load-label">
              {test.load.label} <span className="text-ink-muted">({test.load.unit})</span>
            </p>
            {options ? (
              <div role="radiogroup" aria-labelledby="load-label" className="mt-2 inline-flex rounded-lg border border-hairline p-0.5">
                {options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    role="radio"
                    aria-checked={value.load === opt}
                    disabled={running}
                    onClick={() => onChange({ ...value, load: opt })}
                    className={`tabular rounded-md px-3 py-1.5 text-sm transition-colors ${
                      value.load === opt ? "bg-ink text-surface" : "text-ink-2 hover:bg-surface-2"
                    }`}
                  >
                    {multiplier(opt)}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type="number"
                aria-labelledby="load-label"
                className="mt-2 w-28 rounded-lg border border-hairline bg-surface px-3 py-1.5 text-sm"
                min={test.load.min}
                max={test.load.max}
                step={test.load.step ?? "any"}
                value={value.load}
                disabled={running}
                onChange={(e) => onChange({ ...value, load: Number(e.target.value) })}
              />
            )}
          </div>

          <label className="block">
            <span className="text-xs font-medium text-ink-2">{test.target.label}</span>
            <span className="mt-2 flex items-center gap-2">
              <input
                type="number"
                inputMode="decimal"
                className="tabular w-28 rounded-lg border border-hairline bg-surface px-3 py-1.5 text-sm"
                min={test.target.min}
                max={test.target.max}
                step={test.target.step ?? "any"}
                value={value.target}
                onChange={(e) => onChange({ ...value, target: e.target.value })}
              />
              <span className="text-sm text-ink-2">% maximum</span>
            </span>
            {errors.target && <span className="mt-1 block text-xs text-critical">{errors.target}</span>}
          </label>
        </div>
      </Card>

      <Card title="Prototype costs" aside="Optional · used to rank qualifying candidates">
        <div className="space-y-2">
          {test.candidates
            .filter((c) => value.candidateIds.includes(c.candidate_id))
            .map((c) => (
              <label key={c.candidate_id} className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-sm text-ink">
                  <SeriesKey color={seriesColor(test.candidates, c.candidate_id)} />
                  {c.label}
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-sm text-ink-muted">£</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    step="0.01"
                    placeholder="unknown"
                    className="tabular w-24 rounded-lg border border-hairline bg-surface px-3 py-1.5 text-right text-sm placeholder:text-ink-muted"
                    value={value.costs[c.candidate_id] ?? ""}
                    onChange={(e) => onChange({ ...value, costs: { ...value.costs, [c.candidate_id]: e.target.value } })}
                  />
                </span>
              </label>
            ))}
          {errors.costs && <p className="text-xs text-critical">{errors.costs}</p>}
        </div>
      </Card>

      <div className="space-y-2">
        <button
          type="submit"
          disabled={disabled}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-surface transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
        >
          {(submitting || running) && <Spinner />}
          {submitting ? "Submitting…" : running ? "Comparison in progress…" : "Run comparison"}
        </button>
        {blockedReason && <p className="text-xs text-ink-2">{blockedReason}</p>}
        <p className="text-xs text-ink-muted">
          The target and costs don't change the physics. Resubmitting with the same candidates and load reuses cached
          simulations when available.
        </p>
      </div>
    </form>
  );
}
