import { useCallback, useRef } from "react";
import { api } from "../api/client";
import type { Experiment, Run, SelectionEntry, TestDefinition } from "../types/contract";
import { seriesColor } from "../lib/colors";
import { engineLabel, executionLabel, gbp, multiplier, pct, RUN_STATUS_LABEL, seconds } from "../lib/format";
import { OutcomeBadge, Pill, SeriesKey, Spinner } from "./ui";

interface Props {
  experiment: Experiment;
  test: TestDefinition | undefined;
}

export function CandidateResults({ experiment, test }: Props) {
  const videos = useRef(new Map<string, HTMLVideoElement>());
  const register = useCallback((id: string, el: HTMLVideoElement | null) => {
    if (el) videos.current.set(id, el);
    else videos.current.delete(id);
  }, []);

  const hasVideo = experiment.runs.some((r) => r.status === "completed" && r.video_url);
  const all = () => [...videos.current.values()];
  const playAll = () => all().forEach((v) => void v.play().catch(() => undefined));
  const pauseAll = () => all().forEach((v) => v.pause());
  const restartAll = () =>
    all().forEach((v) => {
      v.currentTime = 0;
      void v.play().catch(() => undefined);
    });

  return (
    <div>
      {hasVideo && (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-ink-2">All videos:</span>
          {(
            [
              ["Play", playAll],
              ["Pause", pauseAll],
              ["Restart together", restartAll],
            ] as const
          ).map(([label, fn]) => (
            <button key={label} type="button" onClick={fn} className="rounded-md border border-hairline px-2.5 py-1 text-ink hover:bg-surface-2">
              {label}
            </button>
          ))}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {experiment.runs.map((run) => (
          <CandidateCard
            key={run.candidate_id}
            run={run}
            test={test}
            entry={experiment.selection?.candidates.find((c) => c.candidate_id === run.candidate_id) ?? null}
            recommended={experiment.selection?.recommended_candidate_id === run.candidate_id}
            fixture={!!experiment.fixture}
            register={register}
          />
        ))}
      </div>
    </div>
  );
}

interface CardProps {
  run: Run;
  test: TestDefinition | undefined;
  entry: SelectionEntry | null;
  recommended: boolean;
  fixture: boolean;
  register: (id: string, el: HTMLVideoElement | null) => void;
}

function CandidateCard({ run, test, entry, recommended, fixture, register }: CardProps) {
  const candidate = test?.candidates.find((c) => c.candidate_id === run.candidate_id);
  const color = seriesColor(test?.candidates ?? [], run.candidate_id);
  const videoUrl = api.resolveArtifactUrl(run.video_url);
  const stillUrl = api.resolveArtifactUrl(run.still_url);
  const done = run.status === "completed";

  return (
    <article className={`flex flex-col rounded-xl border bg-surface p-4 ${recommended ? "border-ink/40 ring-1 ring-ink/20" : "border-hairline"}`}>
      <header className="flex min-h-14 items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
            <SeriesKey color={color} />
            {candidate?.label ?? run.candidate_id}
          </h3>
          {candidate && (
            <p className="mt-0.5 text-xs text-ink-2">
              {multiplier(candidate.parameter.value)} {candidate.parameter.unit.replace(/^x\s*/i, "")}
            </p>
          )}
        </div>
        {recommended && <Pill tone="good">Shortlist #1</Pill>}
      </header>

      <div className="mt-3 aspect-square overflow-hidden rounded-lg bg-surface-2">
        {done && videoUrl ? (
          <video
            ref={(el) => register(run.candidate_id, el)}
            src={videoUrl}
            poster={stillUrl ?? undefined}
            controls
            muted
            playsInline
            preload="metadata"
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-xs text-ink-muted">
            {run.status === "running" && <Spinner className="h-5 w-5" />}
            {run.status === "queued" && "Waiting to run"}
            {run.status === "running" && "Simulating…"}
            {run.status === "failed" && "No video: run failed"}
            {done && (fixture ? "No video in illustrative fixture" : "Video not available for this run")}
          </div>
        )}
      </div>

      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-ink-2">{test?.metric.label ?? "Deformation"}</dt>
          <dd className="text-2xl font-semibold text-ink">{done ? pct(run.deformation_pct) : "—"}</dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-ink-2">Target</dt>
          <dd>{done ? <OutcomeBadge outcome={entry?.outcome ?? null} /> : <span className="text-xs text-ink-muted">{RUN_STATUS_LABEL[run.status]}</span>}</dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-ink-2">Prototype cost</dt>
          <dd className="tabular text-ink">{gbp(entry?.prototype_cost_gbp)}</dd>
        </div>
      </dl>

      {run.error && (
        <p className="mt-3 rounded-lg bg-critical/10 p-2 text-xs text-ink" role="alert">
          <strong className="font-semibold">{run.error.code}:</strong> {run.error.message}
        </p>
      )}

      <p className="mt-auto pt-3 text-xs text-ink-muted">
        {engineLabel(run.engine)} · {executionLabel(run.execution_mode)} · runtime {seconds(run.runtime_seconds)}
      </p>
    </article>
  );
}
