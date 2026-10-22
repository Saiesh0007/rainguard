"""Honest evaluation of what the available data can and cannot support.

A. Ward-level explanation of historical waterlogging-incident burden (n = 24 wards)
   Target  : incident_class (1-7 ordinal bin digitised from BMC's ward map).
   Methods : B0 median baseline | B1 population | B2 population + area
             M1 B2 + terrain (median elevation, low-lying share)
             M2 M1 + count of BMC-listed waterlogging spots
   Protocol: leave-one-ward-out cross-validation, ordinary least squares on standardised
             features, predictions clipped to [1, 7]. Metrics: MAE (classes) and Spearman rho.
             A permutation test (1,000 shuffles of the target) gives the chance that a
             model's LOO MAE is this good by luck. This is EXPLANATORY, cross-sectional
             validation - not a forecast; there is no time dimension in the ward data.

B. Location-level terrain check (within-ward case-control)
   For every listed location with a point/street geocode, compare its TPI and elevation
   with all 500 m grid cells of the SAME ward (percentile). If terrain carried no signal,
   percentiles would be uniform with median 0.5. One-sample Wilcoxon test vs 0.5.

Output: data/processed/evaluation.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
SEED = 20261022
N_PERM = 1000

MODELS = {
    "B0_median": [],
    "B1_population": ["log_pop"],
    "B2_population_area": ["log_pop", "log_area"],
    "M1_plus_terrain": ["log_pop", "log_area", "median_elevation_m", "low_lying_share"],
    "M2_plus_listed_spots": ["log_pop", "log_area", "median_elevation_m", "low_lying_share", "log_spots"],
}


def loo_predict(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    n = len(y)
    pred = np.empty(n)
    for i in range(n):
        tr = np.arange(n) != i
        if X.shape[1] == 0:
            pred[i] = np.median(y[tr])
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd[sd == 0] = 1
        A = np.column_stack([np.ones(tr.sum()), (X[tr] - mu) / sd])
        coef, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
        pred[i] = np.r_[1, (X[i] - mu) / sd] @ coef
    return np.clip(pred, 1, 7)


def ward_evaluation() -> dict:
    w = pd.read_csv(PROC / "ward_stats.csv")
    w["log_pop"] = np.log(w.population_2011)
    w["log_area"] = np.log(w.area_km2)
    w["log_spots"] = np.log1p(w.bmc_fpg2026_spots)
    y = w.incident_class.values.astype(float)
    rng = np.random.default_rng(SEED)
    res = {}
    for name, cols in MODELS.items():
        X = w[cols].values.astype(float) if cols else np.empty((len(w), 0))
        pred = loo_predict(X, y)
        mae = float(np.mean(np.abs(pred - y)))
        # a constant baseline has no ranking, so Spearman is undefined (LOO medians vary only as an artefact)
        rho = float(stats.spearmanr(pred, y).statistic) if cols else float("nan")
        entry = {"features": cols, "loo_mae_classes": round(mae, 3),
                 "loo_spearman": None if np.isnan(rho) else round(rho, 3),
                 "within_one_class": round(float(np.mean(np.abs(np.round(pred) - y) <= 1)), 3)}
        if cols:
            perm = [np.mean(np.abs(loo_predict(X, p) - p)) for p in (rng.permutation(y) for _ in range(N_PERM))]
            entry["permutation_p_value"] = round(float((np.sum(np.array(perm) <= mae) + 1) / (N_PERM + 1)), 4)
        res[name] = entry
    base = res["B0_median"]["loo_mae_classes"]
    for v in res.values():
        v["mae_change_vs_B0"] = round(v["loo_mae_classes"] - base, 3)
    rho_pop = stats.spearmanr(w.population_2011, w.incident_class)
    rho_spots = stats.spearmanr(w.bmc_fpg2026_spots, w.incident_class)
    return {"n_wards": int(len(w)), "target": "incident_class (1-7)", "class_counts":
            w.incident_class.value_counts().sort_index().to_dict(), "models": res,
            "spearman_population_vs_class": {"rho": round(float(rho_pop.statistic), 3),
                                             "p": round(float(rho_pop.pvalue), 4)},
            "spearman_listed_spots_vs_class": {"rho": round(float(rho_spots.statistic), 3),
                                               "p": round(float(rho_spots.pvalue), 4)}}


def terrain_case_control() -> dict:
    loc = pd.read_csv(PROC / "location_features.csv")
    out = {}
    for label, mask in {"point_or_street": loc.geocode_precision.isin(["point", "street"]),
                        "area_only": loc.geocode_precision == "area"}.items():
        sub = loc[mask & loc.tpi_pct_in_ward.notna()]
        entry = {"n": int(len(sub))}
        for col in ["tpi_pct_in_ward", "elev_pct_in_ward"]:
            v = sub[col].values
            test = stats.wilcoxon(v - 0.5) if len(v) >= 10 else None
            entry[col] = {"median": round(float(np.median(v)), 3), "mean": round(float(np.mean(v)), 3),
                          "share_below_0.5": round(float(np.mean(v < 0.5)), 3),
                          "wilcoxon_p_vs_0.5": None if test is None else round(float(test.pvalue), 5)}
        out[label] = entry
    return out


def main() -> None:
    out = {"ward_level": ward_evaluation(), "location_terrain_case_control": terrain_case_control()}
    (PROC / "evaluation.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
