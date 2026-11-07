import type { Experiment, TestDefinition } from "../types/contract";
import { seriesColor } from "../lib/colors";
import { engineLabel, executionLabel, gbp, multiplier, pct, RUN_STATUS_LABEL, seconds } from "../lib/format";
import { OutcomeBadge, SeriesKey } from "./ui";

export function ComparisonTable({ experiment, test }: { experiment: Experiment; test: TestDefinition | undefined }) {
  const selection = experiment.selection;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-b border-hairline text-left text-xs text-ink-2">
            <th className="py-2 pr-3 font-medium">Candidate</th>
            <th className="py-2 pr-3 font-medium">Stiffness</th>
            <th className="py-2 pr-3 text-right font-medium">{test?.metric.label ?? "Deformation"}</th>
            <th className="py-2 pr-3 font-medium">Target {selection ? `(≤ ${pct(selection.target_max_deformation_pct, 0)})` : ""}</th>
            <th className="py-2 pr-3 text-right font-medium">Cost</th>
            <th className="py-2 pr-3 text-right font-medium">Shortlist</th>
            <th className="py-2 font-medium">Run</th>
          </tr>
        </thead>
        <tbody>
          {experiment.runs.map((run) => {
            const candidate = test?.candidates.find((c) => c.candidate_id === run.candidate_id);
            const entry = selection?.candidates.find((c) => c.candidate_id === run.candidate_id);
            const position = selection ? selection.shortlist.indexOf(run.candidate_id) : -1;
            return (
              <tr key={run.candidate_id} className="border-b border-hairline last:border-0">
                <td className="py-2.5 pr-3">
                  <span className="flex items-center gap-2 font-medium text-ink">
                    <SeriesKey color={seriesColor(test?.candidates ?? [], run.candidate_id)} />
                    {candidate?.label ?? run.candidate_id}
                  </span>
                </td>
                <td className="tabular py-2.5 pr-3 text-ink-2">{candidate ? multiplier(candidate.parameter.value) : "—"}</td>
                <td className="tabular py-2.5 pr-3 text-right font-semibold text-ink">
                  {run.status === "completed" ? pct(run.deformation_pct) : "—"}
                </td>
                <td className="py-2.5 pr-3">
                  {entry ? <OutcomeBadge outcome={entry.outcome} /> : <span className="text-xs text-ink-muted">{RUN_STATUS_LABEL[run.status]}</span>}
                </td>
                <td className="tabular py-2.5 pr-3 text-right text-ink-2">{gbp(entry?.prototype_cost_gbp ?? experiment.request?.prototype_costs_gbp?.[run.candidate_id])}</td>
                <td className="tabular py-2.5 pr-3 text-right text-ink">{position >= 0 ? `#${position + 1}` : "—"}</td>
                <td className="py-2.5 text-xs text-ink-2">
                  {RUN_STATUS_LABEL[run.status]} · {engineLabel(run.engine)} · {executionLabel(run.execution_mode)} · {seconds(run.runtime_seconds)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
