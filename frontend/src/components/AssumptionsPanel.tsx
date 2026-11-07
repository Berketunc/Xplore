import type { Experiment, TestDefinition } from "../types/contract";
import { EVIDENCE_LABEL } from "../lib/format";
import { Card } from "./ui";

export function AssumptionsPanel({ test, experiment }: { test: TestDefinition; experiment: Experiment | null }) {
  const units = experiment?.unit_system ?? test.unit_system;
  const assumptions = experiment?.assumptions ?? test.assumptions;
  const v = experiment?.versions;

  return (
    <Card title="Assumptions, units and provenance">
      <div className="grid gap-6 text-sm md:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Assumptions</h3>
          <ul className="mt-2 list-disc space-y-1.5 pl-4 text-ink-2">
            {assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Metric</h3>
            <p className="mt-2 text-ink-2">
              <span className="font-medium text-ink">{test.metric.label}.</span> {test.metric.definition}
            </p>
            {test.metric.window_description && <p className="mt-1 text-ink-2">{test.metric.window_description}</p>}
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Units</h3>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-ink-2">
              <dt className="text-ink-muted">System</dt>
              <dd>{units.kind}</dd>
              <dt className="text-ink-muted">Deformation</dt>
              <dd>{units.deformation}</dd>
              <dt className="text-ink-muted">Load</dt>
              <dd>{units.load}</dd>
              <dt className="text-ink-muted">Time</dt>
              <dd>{units.time}</dd>
            </dl>
            {units.notes && <p className="mt-1 text-xs text-ink-muted">{units.notes}</p>}
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Provenance</h3>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-ink-2">
              <dt className="text-ink-muted">Evidence</dt>
              <dd>{experiment ? EVIDENCE_LABEL[experiment.evidence_status] : "—"}</dd>
              <dt className="text-ink-muted">Scene source</dt>
              <dd>{test.scene.source ?? "—"}</dd>
              <dt className="text-ink-muted">PowerSim commit</dt>
              <dd className="font-mono text-xs">{v?.powersim_commit ?? "—"}</dd>
              <dt className="text-ink-muted">Runner / API</dt>
              <dd className="font-mono text-xs">
                {v?.runner ?? "—"} / {v?.api ?? "—"}
              </dd>
              <dt className="text-ink-muted">Checkpoint</dt>
              <dd className="font-mono text-xs break-all">{experiment?.checkpoint_id ?? "—"}</dd>
              <dt className="text-ink-muted">Config hash</dt>
              <dd className="font-mono text-xs break-all">{experiment?.config_hash ?? "—"}</dd>
            </dl>
          </div>
        </div>
      </div>
    </Card>
  );
}
