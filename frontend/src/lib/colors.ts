import type { CandidateDefinition, CandidateId } from "../types/contract";

/**
 * Colour follows the entity, never its rank: a candidate's slot is its position in the
 * catalog, so filtering or re-ordering never repaints it. Slots map to --series-N CSS vars
 * (validated categorical palette; first three pass all-pairs CVD checks in light and dark).
 */
export function seriesColor(candidates: CandidateDefinition[], id: CandidateId): string {
  const index = candidates.findIndex((c) => c.candidate_id === id);
  return `var(--series-${(index < 0 ? 0 : index % 8) + 1})`;
}
