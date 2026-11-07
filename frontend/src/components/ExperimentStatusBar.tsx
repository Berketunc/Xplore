import type { ApiRequestError } from "../api/client";
import type { Experiment, TestDefinition } from "../types/contract";
import { seriesColor } from "../lib/colors";
import { dateTime, EXPERIMENT_STATUS_LABEL, RUN_STATUS_LABEL } from "../lib/format";
import { EvidenceBadge, Pill, Spinner } from "./ui";

interface Props {
  experiment: Experiment;
  test: TestDefinition | undefined;
  pollError: ApiRequestError | null;
}

export function ExperimentStatusBar({ experiment, test, pollError }: Props) {
  const { status, completed_runs, total_runs, runs } = experiment;
  const active = status === "queued" || status === "running";
  const failedRuns = runs.filter((r) => r.status === "failed").length;
  const label = (id: string) => test?.candidates.find((c) => c.candidate_id === id)?.label ?? id;

  const summary =
    status === "queued"
      ? "Waiting for a simulation worker"
      : status === "failed"
        ? "No run completed"
        : `${completed_runs} of ${total_runs} runs completed${failedRuns ? `, ${failedRuns} failed` : ""}`;

  return (
    <div className="rounded-xl border border-hairline bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
              status === "completed"
                ? "bg-good/15 text-ink"
                : status === "failed"
                  ? "bg-critical/15 text-ink"
                  : status === "partial"
                    ? "bg-warning/20 text-ink"
                    : "bg-surface-2 text-ink"
            }`}
            role="status"
            aria-live="polite"
          >
            {active && <Spinner />}
            {EXPERIMENT_STATUS_LABEL[status]}
          </span>
          <span className="text-sm text-ink-2">{summary}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <EvidenceBadge status={experiment.evidence_status} fixture={experiment.fixture} />
          <Pill>
            ID <span className="font-mono">{experiment.experiment_id}</span>
          </Pill>
        </div>
      </div>

      {runs.length > 0 && (
        <ol className="mt-3 flex flex-wrap gap-2" aria-label="Candidate runs">
          {runs.map((run) => (
            <li
              key={run.candidate_id}
              className="flex items-center gap-2 rounded-lg border border-hairline px-2.5 py-1 text-xs text-ink-2"
            >
              <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: seriesColor(test?.candidates ?? [], run.candidate_id) }} />
              <span className="font-medium text-ink">{label(run.candidate_id)}</span>
              {run.status === "running" && <Spinner className="text-ink-muted" />}
              <span className={run.status === "failed" ? "text-critical" : ""}>{RUN_STATUS_LABEL[run.status]}</span>
            </li>
          ))}
        </ol>
      )}

      <p className="mt-3 text-xs text-ink-muted">
        Created {dateTime(experiment.created_at)}
        {experiment.completed_at ? ` · finished ${dateTime(experiment.completed_at)}` : ""}
      </p>

      {pollError && (
        <p className="mt-2 text-xs text-critical" role="alert">
          {pollError.status === 404
            ? `Experiment not found: ${pollError.message}`
            : `Connection problem while checking status (${pollError.message}). Retrying…`}
        </p>
      )}
    </div>
  );
}
