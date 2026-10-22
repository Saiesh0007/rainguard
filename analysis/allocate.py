"""Weekly inspection plan: pick K places for the inspection teams, at most CAP per ward.

Rule (greedy, transparent): walk down the priority order (score.py; ties broken by location_id) and
take each place unless its ward already has CAP places in the plan; stop at K. The cap stops one
high-history ward from absorbing every team. app/src/lib/allocate.ts implements the same rule and
tests/allocate.test.ts checks the two agree.

Robustness: the plan is rebuilt for the same 2,000 random weightings used in score.py. Each place gets
the share of weightings that put it in the plan; places in >= 80% are the "stable core" a planner can
commit to whatever weights they prefer.

Outputs: data/processed/allocation.json, plan_frequency column in data/processed/priority_scores.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from score import COMPONENTS, DEFAULT_WEIGHTS, N_DRAWS, SEED, components, jaccard, ranks, score

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
K = 20
CAP = 3
STABLE = 0.8


def plan(rank: pd.Series, ward: pd.Series, ids: pd.Series, k: int = K, cap: int = CAP) -> list[int]:
    order = pd.DataFrame({"rank": rank, "id": ids}).sort_values(["rank", "id"]).index
    taken: list[int] = []
    per_ward: dict[str, int] = {}
    for i in order:
        w = ward[i]
        if per_ward.get(w, 0) >= cap:
            continue
        taken.append(i)
        per_ward[w] = per_ward.get(w, 0) + 1
        if len(taken) == k:
            break
    return taken


def main() -> None:
    loc = pd.read_csv(PROC / "location_features.csv")
    c = components(loc)
    base_rank = ranks(score(c, DEFAULT_WEIGHTS))
    base = plan(base_rank, loc.ward, loc.location_id)
    uncapped = plan(base_rank, loc.ward, loc.location_id, cap=K)

    rng = np.random.default_rng(SEED)
    draws = rng.dirichlet(np.ones(len(COMPONENTS)), size=N_DRAWS)
    freq = np.zeros(len(loc))
    overlaps = []
    for w in draws:
        p = plan(ranks(score(c, dict(zip(COMPONENTS, w)))), loc.ward, loc.location_id)
        freq[p] += 1
        overlaps.append(jaccard(set(base), set(p)))
    freq /= N_DRAWS

    scores = pd.read_csv(PROC / "priority_scores.csv")
    scores["plan_frequency"] = pd.Series(freq, index=loc.location_id).reindex(scores.location_id).round(3).values
    scores.to_csv(PROC / "priority_scores.csv", index=False)

    wards_in_plan = loc.ward[base].nunique()
    out = {
        "k": K, "cap_per_ward": CAP, "n_weight_draws": N_DRAWS, "seed": SEED,
        "rule": f"Walk down the priority order and take each place unless its ward already has {CAP}; stop at {K}.",
        "default_plan": loc.location_id[base].tolist(),
        "wards_in_default_plan": int(wards_in_plan),
        "wards_in_uncapped_top_k": int(loc.ward[list(uncapped)].nunique()),
        "plan_jaccard_vs_default": {"median": round(float(np.median(overlaps)), 2),
                                    "p5": round(float(np.percentile(overlaps, 5)), 2)},
        "stable_core_threshold": STABLE,
        "stable_core": loc.location_id[freq >= STABLE].tolist(),
    }
    (PROC / "allocation.json").write_text(json.dumps(out, indent=2))
    print({k: v for k, v in out.items() if k not in ("default_plan", "stable_core")},
          "stable core:", len(out["stable_core"]))


if __name__ == "__main__":
    main()
