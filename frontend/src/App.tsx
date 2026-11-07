import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, EXAMPLE_EXPERIMENT_ID, toApiError, type ApiRequestError } from "./api/client";
import { AssumptionsPanel } from "./components/AssumptionsPanel";
import { CandidateResults } from "./components/CandidateResults";
import { ComparisonTable } from "./components/ComparisonTable";
import { DeformationChart, type ChartSeries } from "./components/DeformationChart";
import { ExperimentStatusBar } from "./components/ExperimentStatusBar";
import { ExplanationPanel } from "./components/ExplanationPanel";
import { initialSetup, SetupForm, setupFromRequest, type SetupState } from "./components/SetupForm";
import { Card, Pill, Spinner } from "./components/ui";
import { useCatalog } from "./hooks/useCatalog";
import { useExperiment } from "./hooks/useExperiment";
import { seriesColor } from "./lib/colors";
import { dateTime, multiplier } from "./lib/format";
import { loadRecent, rememberExperiment, type RecentExperiment } from "./lib/recent";
import { TERMINAL_STATUSES, type ExperimentRequest } from "./types/contract";

const idFromUrl = () => new URLSearchParams(window.location.search).get("experiment");

function setUrlExperiment(id: string | null) {
  const url = new URL(window.location.href);
  if (id) url.searchParams.set("experiment", id);
  else url.searchParams.delete("experiment");
  window.history.pushState(null, "", url);
}

const timeAxisLabel = (unit: string | undefined) =>
  unit === "simulation_s" ? "Simulation time (s)" : unit === "frame" ? "Frame" : (unit ?? "Time");

export default function App() {
  const { catalog, error: catalogError, retry } = useCatalog();
  const test = catalog?.tests.find((t) => t.availability === "available") ?? catalog?.tests[0];

  const [experimentId, setExperimentId] = useState<string | null>(idFromUrl);
  const { experiment, error: pollError, prime } = useExperiment(experimentId);
  const [setup, setSetup] = useState<SetupState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<ApiRequestError | null>(null);
  const [recent, setRecent] = useState<RecentExperiment[]>(loadRecent);
  const syncedId = useRef<string | null>(null);

  // Browser back/forward restores the experiment in the URL.
  useEffect(() => {
    const onPop = () => setExperimentId(idFromUrl());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    if (test && !setup) setSetup(initialSetup(test));
  }, [test, setup]);

  // When an experiment is opened (refresh, saved link, recent list), mirror its inputs in the form
  // and remember it locally.
  useEffect(() => {
    if (!test || !experiment || syncedId.current === experiment.experiment_id) return;
    syncedId.current = experiment.experiment_id;
    if (experiment.request) setSetup(setupFromRequest(test, experiment.request));
    const labels = (experiment.request?.candidate_ids ?? [])
      .map((id) => test.candidates.find((c) => c.candidate_id === id)?.label ?? id)
      .join(", ");
    const load = experiment.request
      ? ` · ${multiplier(experiment.request.load_multiplier)} load · target ${experiment.request.target_max_deformation_pct}%`
      : "";
    setRecent(
      rememberExperiment({
        id: experiment.experiment_id,
        savedAt: experiment.created_at ?? new Date().toISOString(),
        label: `${labels || test.title}${load}${experiment.fixture ? " · illustrative" : ""}`,
      }),
    );
  }, [experiment, test]);

  const openExperiment = useCallback((id: string | null) => {
    setSubmitError(null);
    setExperimentId(id);
    setUrlExperiment(id);
  }, []);

  const submit = async (request: ExperimentRequest) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await api.createExperiment(request);
      prime(created);
      openExperiment(created.experiment_id);
    } catch (e) {
      setSubmitError(toApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  const running = !!experiment && !TERMINAL_STATUSES.has(experiment.status);
  const blockedReason =
    api.mode === "live" && test?.availability === "proposed"
      ? "This test is still marked as proposed in the backend catalog. Submission opens once it is confirmed as available."
      : null;

  const chartSeries: ChartSeries[] = useMemo(() => {
    if (!experiment || !test) return [];
    return experiment.runs
      .filter((r) => r.status === "completed" && r.time_series)
      .map((r) => ({
        id: r.candidate_id,
        label: test.candidates.find((c) => c.candidate_id === r.candidate_id)?.label ?? r.candidate_id,
        color: seriesColor(test.candidates, r.candidate_id),
        t: r.time_series!.t,
        y: r.time_series!.deformation_pct,
      }));
  }, [experiment, test]);
  const tUnit = experiment?.runs.find((r) => r.time_series)?.time_series?.t_unit;

  return (
    <div className="min-h-screen">
      <header className="border-b border-hairline bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" className="h-8 w-8" />
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-ink">Xplore</h1>
              <p className="text-xs text-ink-2">Virtual material experiments</p>
            </div>
          </div>
          {api.mode === "mock" ? (
            <Pill tone="warning">Mock API · illustrative fixtures</Pill>
          ) : (
            <Pill>
              Live API · <span className="font-mono">{api.baseUrl}</span>
            </Pill>
          )}
        </div>
      </header>

      {api.mode === "mock" && (
        <div className="border-b border-hairline bg-warning/15">
          <p className="mx-auto max-w-7xl px-4 py-2 text-xs text-ink lg:px-8">
            <span aria-hidden>⚠ </span>
            <strong>Illustrative preview.</strong> This build uses fixture data from <code>shared/</code>, not simulation results.
            Set <code>VITE_API_MODE=live</code> to connect to the Xplore API.
          </p>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <p className="mb-6 max-w-3xl text-sm text-ink-2">
          Compare soft-material options under the same virtual experiment, check them against your deformation target, and
          decide which prototype to test physically next.
        </p>

        {!catalog && !catalogError && (
          <p className="flex items-center gap-2 text-sm text-ink-2">
            <Spinner /> Loading experiment catalog…
          </p>
        )}
        {catalogError && (
          <Card title="Couldn't load the experiment catalog">
            <p className="text-sm text-ink-2">{catalogError.message}</p>
            <button type="button" onClick={retry} className="mt-3 rounded-lg border border-hairline px-3 py-1.5 text-sm hover:bg-surface-2">
              Retry
            </button>
          </Card>
        )}
        {catalog && !test && <Card title="No supported experiments">The catalog doesn't list any tests yet.</Card>}

        {test && setup && (
          <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
            <aside className="space-y-4">
              <SetupForm
                test={test}
                value={setup}
                onChange={setSetup}
                onSubmit={submit}
                submitting={submitting}
                running={running}
                blockedReason={blockedReason}
              />
              {recent.length > 0 && (
                <Card title="Saved experiments">
                  <ul className="space-y-1">
                    {recent.map((r) => (
                      <li key={r.id}>
                        <button
                          type="button"
                          onClick={() => openExperiment(r.id)}
                          className={`w-full rounded-md px-2 py-1.5 text-left text-xs hover:bg-surface-2 ${
                            r.id === experimentId ? "bg-surface-2" : ""
                          }`}
                        >
                          <span className="block text-ink">{r.label}</span>
                          <span className="block text-ink-muted">
                            {dateTime(r.savedAt)} · <span className="font-mono">{r.id}</span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </aside>

            <section className="min-w-0 space-y-6">
              {submitError && (
                <div className="rounded-xl border border-critical/40 bg-critical/10 p-4 text-sm text-ink" role="alert">
                  <strong className="font-semibold">The comparison wasn't started.</strong> {submitError.message}
                </div>
              )}

              {experiment ? (
                <>
                  <ExperimentStatusBar experiment={experiment} test={test} pollError={pollError} />
                  <ExplanationPanel experiment={experiment} test={test} />
                  <Card title="Results by candidate" aside={experiment.selection?.provisional ? "Shortlist is provisional" : undefined}>
                    <CandidateResults experiment={experiment} test={test} />
                  </Card>
                  <Card
                    title={`${test.protocol === "compression" ? "Compression" : "Deflection"} over time`}
                    aside={`${test.unit_system.deformation} · reported metric: ${test.metric.label.toLowerCase()}`}
                  >
                    {chartSeries.length ? (
                      <DeformationChart
                        series={chartSeries}
                        target={experiment.selection?.target_max_deformation_pct ?? experiment.request?.target_max_deformation_pct ?? null}
                        metricLabel={test.protocol === "compression" ? "Compression" : "Deflection"}
                        timeLabel={timeAxisLabel(tUnit)}
                      />
                    ) : (
                      <p className="py-10 text-center text-sm text-ink-muted">
                        {running ? "Time series appear as each candidate completes." : "No completed time series to plot."}
                      </p>
                    )}
                  </Card>
                  <Card title="Comparison table">
                    <ComparisonTable experiment={experiment} test={test} />
                  </Card>
                </>
              ) : experimentId && pollError ? (
                <Card title="Couldn't open this experiment">
                  <p className="text-sm text-ink-2">{pollError.message}</p>
                  <button
                    type="button"
                    onClick={() => openExperiment(null)}
                    className="mt-3 rounded-lg border border-hairline px-3 py-1.5 text-sm hover:bg-surface-2"
                  >
                    Start a new comparison
                  </button>
                </Card>
              ) : experimentId ? (
                <p className="flex items-center gap-2 text-sm text-ink-2">
                  <Spinner /> Loading experiment…
                </p>
              ) : (
                <div className="rounded-xl border border-dashed border-axis bg-surface p-10 text-center">
                  <p className="text-sm font-medium text-ink">No comparison yet</p>
                  <p className="mt-1 text-sm text-ink-2">
                    Choose candidates, a load and your deformation target, then run the comparison.
                  </p>
                  {EXAMPLE_EXPERIMENT_ID && (
                    <button
                      type="button"
                      onClick={() => openExperiment(EXAMPLE_EXPERIMENT_ID)}
                      className="mt-4 rounded-lg border border-hairline px-3 py-1.5 text-sm text-ink hover:bg-surface-2"
                    >
                      {api.mode === "mock" ? "Open illustrative example" : "Open saved example"}
                    </button>
                  )}
                </div>
              )}

              <AssumptionsPanel test={test} experiment={experiment} />
            </section>
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-10 text-xs text-ink-muted lg:px-8">
        Simulation method and released scene assets:{" "}
        <a className="underline hover:text-ink" href="https://github.com/nttung1110/PowerSim" target="_blank" rel="noreferrer">
          PowerSim
        </a>
        , credited to its original authors. Xplore contributes the experiment workflow, measurements and comparison.
      </footer>
    </div>
  );
}
