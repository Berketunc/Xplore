"""Deterministic shortlist; the assistant only explains these decisions."""

import math


def select_candidates(runs, candidate_ids, target_max_deformation_pct, costs):
    target = float(target_max_deformation_pct)
    if not math.isfinite(target) or target < 0:
        raise ValueError("Target must be a finite, nonnegative percentage")
    if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Requested candidate IDs must be nonempty and unique")
    by_id = {run["candidate_id"]: run for run in runs}
    if len(by_id) != len(runs) or set(by_id) - set(candidate_ids):
        raise ValueError("Run IDs must be unique members of the request")
    decisions = []
    qualifying = []
    incomplete = []
    for candidate_id in candidate_ids:
        run = by_id.get(candidate_id, {})
        value = run.get("deformation_pct")
        if run.get("status") != "completed" or value is None:
            outcome = "unavailable"
            incomplete.append(candidate_id)
        elif not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError("Completed measurements must be finite and nonnegative")
        else:
            outcome = "meets_target" if value <= target else "exceeds_target"
            if outcome == "meets_target":
                qualifying.append(candidate_id)
        decisions.append({"candidate_id": candidate_id, "outcome": outcome})
    for value in costs.values():
        if value is not None and (not math.isfinite(float(value)) or float(value) < 0):
            raise ValueError("Prototype costs must be finite and nonnegative")
    missing_costs = [candidate_id for candidate_id in qualifying if costs.get(candidate_id) is None]
    cost_ranking = None
    if qualifying and not missing_costs:
        cost_ranking = sorted(qualifying, key=lambda cid: (costs[cid], by_id[cid]["deformation_pct"], cid))
    return {
        "rule_id": "deformation-target-then-prototype-cost-v1",
        "target_max_deformation_pct": target,
        "decisions": decisions,
        "qualifying_candidate_ids": qualifying,
        "cost_ranking": cost_ranking,
        "recommended_candidate_id": cost_ranking[0] if cost_ranking else None,
        "missing_cost_candidate_ids": missing_costs,
        "unavailable_candidate_ids": incomplete,
        "provisional": bool(incomplete),
    }
