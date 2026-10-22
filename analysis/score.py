"""Transparent inspection-prioritisation score for listed waterlogging locations.

This is a RULE-BASED PRIORITISATION SCORE, not a probability and not a validated
forecast. It orders officially listed locations so a civic team can decide what to
inspect first before the monsoon. Every component is shown in the app.

Components (each scaled 0-1, higher = inspect sooner):
  ward_burden    (incident_class - 1) / 6, from BMC's ward-wise waterlogging-incident map
                 (historical, ward-level - identical for every location in a ward). It mostly
                 follows ward population (rho = 0.835), i.e. it measures exposure and reporting.
  ward_excess    incident class above or below what ward population alone predicts (features.py),
                 min-max scaled across wards. Optional (default weight 0): it isolates "more incidents
                 than population explains" but rests on a 24-ward fit and a binned target.
  corroboration  (number of independent official lists naming the place - 1) / 2, i.e.
                 0 = one list, 0.5 = two, 1 = all three (BMC FPG 2026, BEST Annex IX,
                 Mumbai Traffic Police diversion table)
  low_lying      1 - within-ward percentile of the location's TPI (DEM-estimated); only for
                 point/street-precision geocodes, otherwise MISSING
  listing_density min(neighbours_1km, 10) / 10 - other listed records within 1 km

Missing components are excluded and the remaining weights renormalised (never imputed).
Default weights: 1/3 each for ward_burden, corroboration and listing_density; 0 for low_lying and
ward_excess. Sensitivity: 2,000 random weightings (Dirichlet(1,1,1,1,1)),
plus leave-one-component-out ablations.

Outputs: data/processed/priority_scores.csv, data/processed/score_sensitivity.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
COMPONENTS = ["ward_burden", "ward_excess", "corroboration", "low_lying", "listing_density"]
# low_lying gets weight 0 by default: evaluate.py found no significant terrain difference between
# listed locations and the rest of their ward (docs/evaluation.md), so it is offered in the civic
# view as an optional, explicitly unvalidated factor rather than silently driving the ranking.
# ward_excess is also 0 by default: for inspection planning, wards where many people are exposed should
# count (ward_burden); the population-adjusted view is offered as an explicit alternative, not hidden.
DEFAULT_WEIGHTS = {"ward_burden": 1 / 3, "ward_excess": 0.0, "corroboration": 1 / 3, "low_lying": 0.0,
                   "listing_density": 1 / 3}
# The population-adjusted alternative: swap ward_burden for ward_excess, everything else unchanged.
ADJUSTED_WEIGHTS = {**DEFAULT_WEIGHTS, "ward_burden": 0.0, "ward_excess": 1 / 3}
TOP_K = 20
N_DRAWS = 2000
SEED = 20261022


def components(loc: pd.DataFrame) -> pd.DataFrame:
    c = pd.DataFrame(index=loc.index)
    c["ward_burden"] = (loc.incident_class - 1) / 6
    ex = loc.incident_excess
    c["ward_excess"] = (ex - ex.min()) / (ex.max() - ex.min())
    c["corroboration"] = (loc.n_sources - 1) / 2
    precise = loc.geocode_precision.isin(["point", "street"])
    c["low_lying"] = np.where(precise & loc.tpi_pct_in_ward.notna(), 1 - loc.tpi_pct_in_ward, np.nan)
    c["listing_density"] = np.where(loc.neighbours_1km.notna(), np.minimum(loc.neighbours_1km, 10) / 10, np.nan)
    return c


def score(c: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    w = pd.Series(weights)[COMPONENTS]
    vals = c[COMPONENTS]
    wmat = vals.notna().mul(w, axis=1)
    total = wmat.sum(axis=1)
    return (100 * (vals.fillna(0) * wmat).sum(axis=1) / total.where(total > 0)).fillna(0)


def jaccard(a: set, b: set) -> float:
    # tied scores can put more than TOP_K places at rank <= TOP_K, so compare sets, not counts
    return len(a & b) / len(a | b) if a | b else 1.0


def ranks(s: pd.Series) -> pd.Series:
    # round first so floating-point noise never splits genuine ties (the app's TypeScript does the same)
    return s.round(6).rank(ascending=False, method="min")


def main() -> None:
    loc = pd.read_csv(PROC / "location_features.csv")
    c = components(loc)
    base = score(c, DEFAULT_WEIGHTS)
    base_rank = ranks(base)

    rng = np.random.default_rng(SEED)
    draws = rng.dirichlet(np.ones(len(COMPONENTS)), size=N_DRAWS)
    in_top = np.zeros(len(loc))
    rhos, overlaps, rank_mat = [], [], np.zeros((N_DRAWS, len(loc)))
    top_base = set(base_rank[base_rank <= TOP_K].index)
    for i, w in enumerate(draws):
        s = score(c, dict(zip(COMPONENTS, w)))
        r = ranks(s)
        rank_mat[i] = r.values
        in_top += (r <= TOP_K).values
        rhos.append(stats.spearmanr(base, s).statistic)
        overlaps.append(jaccard(top_base, set(r[r <= TOP_K].index)))

    ablation = {}
    for comp in COMPONENTS:
        # drop one of the four original components, the others equal; ward_excess stays off as in the default
        if comp == "ward_excess":
            continue
        w = {k: (0.0 if k in (comp, "ward_excess") else 1 / 3) for k in COMPONENTS}
        s = score(c, w)
        r = ranks(s)
        ablation[comp] = {"spearman_vs_default": round(float(stats.spearmanr(base, s).statistic), 3),
                          "top20_jaccard": round(jaccard(top_base, set(r[r <= TOP_K].index)), 2)}

    adj = score(c, ADJUSTED_WEIGHTS)
    adj_rank = ranks(adj)
    population_adjusted = {
        "weights": ADJUSTED_WEIGHTS,
        "spearman_vs_default": round(float(stats.spearmanr(base, adj).statistic), 3),
        "top20_jaccard_vs_default": round(jaccard(top_base, set(adj_rank[adj_rank <= TOP_K].index)), 2),
    }

    out = loc[["location_id"]].copy()
    for k in COMPONENTS:
        out[k] = c[k]  # full precision: the app re-scores from these and must match exactly
    out["components_available"] = c[COMPONENTS].notna().sum(axis=1)
    out["priority_score"] = base.round(1)
    out["priority_rank"] = base_rank.astype(int)
    out["top20_frequency"] = (in_top / N_DRAWS).round(3)
    out["rank_p10"] = np.percentile(rank_mat, 10, axis=0).astype(int)
    out["rank_p90"] = np.percentile(rank_mat, 90, axis=0).astype(int)
    n = len(out)
    out["priority_tier"] = np.select(
        [out.priority_rank <= round(0.2 * n), out.priority_rank <= round(0.5 * n)], ["A", "B"], "C")
    out.to_csv(PROC / "priority_scores.csv", index=False)

    sens = {
        "n_locations": n, "top_k": TOP_K, "n_weight_draws": N_DRAWS, "seed": SEED,
        "default_weights": DEFAULT_WEIGHTS,
        "component_coverage": {k: int(c[k].notna().sum()) for k in COMPONENTS},
        "spearman_default_vs_random_weights": {
            "median": round(float(np.median(rhos)), 3), "p5": round(float(np.percentile(rhos, 5)), 3)},
        "top20_jaccard_default_vs_random_weights": {
            "median": round(float(np.median(overlaps)), 2), "p5": round(float(np.percentile(overlaps, 5)), 2)},
        "locations_in_top20_in_at_least_80pct_of_draws": int((out.top20_frequency >= 0.8).sum()),
        "ablation_drop_one_component": ablation,
        "population_adjusted_alternative": population_adjusted,
        "tier_rule": "A = top 20% of ranks, B = next 30%, C = remaining 50% (relative order, not risk level)",
    }
    (PROC / "score_sensitivity.json").write_text(json.dumps(sens, indent=2))
    print(json.dumps(sens, indent=2))


if __name__ == "__main__":
    main()
