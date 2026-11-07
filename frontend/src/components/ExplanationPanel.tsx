import type { Experiment, TestDefinition } from "../types/contract";
import { explainExperiment } from "../lib/explain";
import { Card, Pill } from "./ui";

export function ExplanationPanel({ experiment, test }: { experiment: Experiment; test: TestDefinition | undefined }) {
  const explanation = explainExperiment(experiment, test);
  if (!explanation) return null;
  const selection = experiment.selection;

  return (
    <Card
      title="Shortlist and explanation"
      aside={<Pill>From recorded results</Pill>}
    >
      <p className="text-base font-semibold text-ink">{explanation.headline}</p>
      <div className="mt-3 space-y-2 text-sm text-ink-2">
        {explanation.paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
      {explanation.nextStep && (
        <p className="mt-4 rounded-lg bg-surface-2 p-3 text-sm text-ink">
          <span className="font-semibold">Suggested next step: </span>
          {explanation.nextStep}
        </p>
      )}
      {selection && (
        <details className="mt-4 text-xs text-ink-2">
          <summary className="cursor-pointer hover:text-ink">Selection rule ({selection.rule_id})</summary>
          <p className="mt-2">{selection.rule_description}</p>
          {selection.notes.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4">
              {selection.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}
        </details>
      )}
    </Card>
  );
}
