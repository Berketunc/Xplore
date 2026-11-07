// Deterministic, template-based explanation assembled only from the experiment record
// and the backend's selection. No language model; no numbers that aren't in the record.

import type { Experiment, TestDefinition } from "../types/contract";
import { EVIDENCE_LABEL, gbp, listJoin, multiplier, pct } from "./format";

export interface Explanation {
  headline: string;
  paragraphs: string[];
  nextStep: string | null;
}

export function explainExperiment(experiment: Experiment, test: TestDefinition | undefined): Explanation | null {
  const { status, selection, runs } = experiment;
  if (status === "queued" || status === "running") return null;

  const label = (id: string) => test?.candidates.find((c) => c.candidate_id === id)?.label ?? id;
  const metricName = (test?.metric.label ?? "Deformation").toLowerCase();
  const evidence = EVIDENCE_LABEL[experiment.evidence_status];
  const load = experiment.request?.load_multiplier;
  const loadText = load !== undefined ? ` at a load multiplier of ${multiplier(load)}` : "";

  if (status === "failed" || !selection) {
    const errors = runs.filter((r) => r.error).map((r) => `${label(r.candidate_id)}: ${r.error!.message}`);
    return {
      headline: "No recommendation: the comparison did not produce results.",
      paragraphs: [
        "No candidate completed, so there are no measurements to compare and no shortlist.",
        ...(experiment.error ? [experiment.error.message] : []),
        ...errors,
      ],
      nextStep: "Check the failure details above and rerun the comparison once the issue is resolved.",
    };
  }

  const target = selection.target_max_deformation_pct;
  const completed = selection.candidates.filter((c) => c.outcome !== "not_evaluated");
  const meets = selection.candidates.filter((c) => c.outcome === "meets_target").map((c) => label(c.candidate_id));
  const exceeds = selection.candidates.filter((c) => c.outcome === "exceeds_target").map((c) => label(c.candidate_id));
  const notEvaluated = selection.candidates.filter((c) => c.outcome === "not_evaluated").map((c) => label(c.candidate_id));

  const paragraphs: string[] = [];
  paragraphs.push(
    `Measured ${metricName}${loadText}: ` +
      completed.map((c) => `${label(c.candidate_id)} ${pct(c.deformation_pct)}`).join(", ") +
      `. The target is at most ${pct(target, 0)}.`,
  );

  const outcomeParts: string[] = [];
  if (meets.length) outcomeParts.push(`${listJoin(meets)} ${meets.length === 1 ? "meets" : "meet"} the target`);
  if (exceeds.length) outcomeParts.push(`${listJoin(exceeds)} ${exceeds.length === 1 ? "exceeds" : "exceed"} it`);
  if (outcomeParts.length) paragraphs.push(`${outcomeParts.join("; ")}.`);
  if (notEvaluated.length) {
    paragraphs.push(
      `${listJoin(notEvaluated)} did not complete and ${notEvaluated.length === 1 ? "was" : "were"} excluded, so this shortlist is provisional.`,
    );
  }

  let headline: string;
  let nextStep: string | null;
  const recommended = selection.recommended_candidate_id;
  if (selection.shortlist.length === 0) {
    headline = `No candidate meets the ${pct(target, 0)} target.`;
    paragraphs.push("Xplore does not pick a winner when nothing qualifies.");
    nextStep =
      "Run a bounded follow-up within the supported settings, such as a lower load multiplier or a firmer scenario, or review whether the target reflects the product requirement.";
  } else if (recommended) {
    const entry = selection.candidates.find((c) => c.candidate_id === recommended);
    headline = `${selection.provisional ? "Provisional shortlist: " : ""}${label(recommended)} is the lowest-cost candidate that meets the target.`;
    const others = selection.shortlist.filter((id) => id !== recommended).map(label);
    paragraphs.push(
      `Among qualifying candidates, ${label(recommended)} has the lowest prototype cost you entered (${gbp(entry?.prototype_cost_gbp)})` +
        (others.length ? `, ahead of ${listJoin(others)}.` : "."),
    );
    nextStep = `Physically test ${label(recommended)} next under the same loading protocol to check the simulated ${metricName}.`;
  } else {
    headline = `${listJoin(selection.shortlist.map(label))} ${selection.shortlist.length === 1 ? "meets" : "meet"} the target; no cost ranking is available.`;
    paragraphs.push(
      "Not every qualifying candidate has a prototype cost, so Xplore can't rank them by cost. They are listed by lower deformation instead.",
    );
    nextStep = "Add prototype costs for the qualifying candidates to get a cost-based shortlist, or choose a next physical test from the qualifying set.";
  }

  paragraphs.push(
    experiment.fixture || experiment.evidence_status === "illustrative"
      ? "Evidence: illustrative preview built from fixture data. These are not simulation results."
      : `Evidence: ${evidence}. Deformation is geometry-based; transmitted force, energy absorption, recovery and repeated loading were not evaluated.`,
  );

  return { headline, paragraphs, nextStep };
}
