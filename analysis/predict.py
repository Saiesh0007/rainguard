"""Heavy-rain outlook for Mumbai: will tomorrow be a heavy-rain day, and how far can the forecast be trusted?

WHAT THIS PREDICTS - AND WHAT IT DOES NOT
  Target: tomorrow is a heavy-rain day in Mumbai, i.e. IMD gridded rain >= 64.5 mm (IMD's "heavy" class)
  in either Mumbai cell (rain_daily.py). This is the trigger BMC prepares pumps and teams for. It is NOT
  a waterlogging prediction: no free source records dated, located waterlogging (docs/data_audit.md).
  City-wide only - one value per day, no neighbourhood differences.

PART A - Observed-rain model, monsoon days (June-September), 1971-2025, chronological split
  train 1971-2008 | validate 2009-2016 (model choice) | test 2017-2025 (touched once, after refitting
  the chosen model on train + validate). Features use only rain up to and including today.
  B0 climatology   train share of heavy days for tomorrow's month
  B1 persistence   train share of heavy tomorrows given today heavy / not heavy
  M1 logistic      log1p(today's rain)
  M2 logistic      M1 + log1p(rain over the last 3 days) + month
  Metrics: Brier score, Brier skill score vs B0 (with a 95% interval from resampling test years),
  ROC AUC, and reliability by probability bin.

PART B - The live forecast's track record, monsoons 2024-2025 (the archive starts in 2024)
  Open-Meteo "previous day 1" forecasts (issued about a day ahead) for the Santacruz point, summed over
  the IMD rain day, compared with the observed IMD heavy-rain flag for that day. This is what the app's
  forecast card quotes: "when the forecast said this much, a heavy-rain day followed X of N times".

IMD's date D is the 24 hours ending 08:30 IST on D (rain_daily_checks.json: the 26 July 2005 storm is
recorded on 27 July). So "today" = the 24 h just measured at 08:30, and "tomorrow" = the next 24 h: the
outlook is made at 08:30 IST from rain already observed. Forecast hours are summed over the same window.

Output: data/processed/outlook.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
HEAVY_MM = 64.5
MONSOON = [6, 7, 8, 9]
SPLIT = {"train": (1971, 2008), "validate": (2009, 2016), "test": (2017, 2025)}
SEED = 20261022
N_BOOT = 2000
BINS = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0001]
FC_BINS = [0, 15.6, 35, 64.5, 1e9]
FC_BIN_LABEL = ["under 15.6 mm", "15.6-35 mm", "35-64.5 mm", "64.5 mm or more"]


# ---------- data ----------
def daily_table() -> pd.DataFrame:
    d = pd.read_csv(PROC / "rain_daily_imd.csv", parse_dates=["date"]).set_index("date")
    r = d.city_max_mm
    t = pd.DataFrame({"rain_today": r, "rain_3d": r.rolling(3).sum(), "rain_tomorrow": r.shift(-1)})
    t["heavy_today"] = (t.rain_today >= HEAVY_MM).astype(int)
    t["y"] = (t.rain_tomorrow >= HEAVY_MM).astype(float).where(t.rain_tomorrow.notna())
    t["month_tomorrow"] = (t.index + pd.Timedelta(days=1)).month
    t["year"] = t.index.year
    t = t[t.month_tomorrow.isin(MONSOON)].dropna(subset=["y", "rain_today", "rain_3d"])
    return t


def design(t: pd.DataFrame, model: str) -> np.ndarray:
    cols = [np.ones(len(t)), np.log1p(t.rain_today.values)]
    if model == "M2":
        cols.append(np.log1p(t.rain_3d.values))
        cols += [(t.month_tomorrow.values == m).astype(float) for m in MONSOON[1:]]
    return np.column_stack(cols)


# ---------- models ----------
def fit_logistic(X: np.ndarray, y: np.ndarray, ridge: float = 1e-4) -> np.ndarray:
    """Newton-Raphson for L2-regularised logistic regression (intercept not penalised)."""
    beta = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], ridge)
    pen[0] = 0
    for _ in range(100):
        p = 1 / (1 + np.exp(-X @ beta))
        grad = X.T @ (p - y) + pen * beta
        hess = (X * (p * (1 - p))[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(hess, grad)
        beta -= step
        if np.abs(step).max() < 1e-9:
            break
    return beta


def predict_logistic(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-X @ beta))


def climatology(train: pd.DataFrame, t: pd.DataFrame) -> np.ndarray:
    return t.month_tomorrow.map(train.groupby("month_tomorrow").y.mean()).values


def persistence(train: pd.DataFrame, t: pd.DataFrame) -> np.ndarray:
    return t.heavy_today.map(train.groupby("heavy_today").y.mean()).values


def predict_all(train: pd.DataFrame, t: pd.DataFrame) -> dict[str, np.ndarray]:
    out = {"B0_climatology": climatology(train, t), "B1_persistence": persistence(train, t)}
    for m in ("M1", "M2"):
        beta = fit_logistic(design(train, m), train.y.values)
        out[f"{m}_logistic"] = predict_logistic(beta, design(t, m))
    return out


# ---------- metrics ----------
def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def auc(p: np.ndarray, y: np.ndarray) -> float:
    r = pd.Series(p).rank().values
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def bss_interval(p: np.ndarray, ref: np.ndarray, y: np.ndarray, years: np.ndarray) -> list[float]:
    """95% interval of the Brier skill score from resampling whole years (keeps within-season dependence)."""
    rng = np.random.default_rng(SEED)
    uniq = np.unique(years)
    by_year = {yr: np.flatnonzero(years == yr) for yr in uniq}
    vals = []
    for _ in range(N_BOOT):
        ix = np.concatenate([by_year[yr] for yr in rng.choice(uniq, len(uniq))])
        vals.append(1 - brier(p[ix], y[ix]) / brier(ref[ix], y[ix]))
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def scores(preds: dict[str, np.ndarray], t: pd.DataFrame, with_ci: bool) -> dict:
    y = t.y.values
    ref = preds["B0_climatology"]
    res = {}
    for name, p in preds.items():
        e = {"brier": round(brier(p, y), 4), "brier_skill_vs_climatology": round(1 - brier(p, y) / brier(ref, y), 3),
             "auc": round(auc(p, y), 3)}
        if with_ci and name != "B0_climatology":
            e["brier_skill_95ci"] = bss_interval(p, ref, y, t.year.values)
        res[name] = e
    return res


def reliability(p: np.ndarray, y: np.ndarray) -> list[dict]:
    b = pd.cut(p, BINS, right=False)
    g = pd.DataFrame({"p": p, "y": y, "bin": b}).groupby("bin", observed=True)
    return [{"bin": f"{iv.left:.2f}-{min(iv.right, 1):.2f}", "n": int(len(x)), "mean_predicted": round(float(x.p.mean()), 3),
             "observed_share": round(float(x.y.mean()), 3)} for iv, x in g]


def part_a() -> dict:
    t = daily_table()
    split = {k: t[t.year.between(*v)] for k, v in SPLIT.items()}
    val = scores(predict_all(split["train"], split["validate"]), split["validate"], with_ci=False)
    logistic = [m for m in val if m.endswith("logistic")]
    chosen = min(logistic, key=lambda m: val[m]["brier"])
    if val[chosen]["brier"] >= min(val["B0_climatology"]["brier"], val["B1_persistence"]["brier"]):
        chosen = min(("B0_climatology", "B1_persistence"), key=lambda m: val[m]["brier"])

    fit = pd.concat([split["train"], split["validate"]])
    test_preds = predict_all(fit, split["test"])
    test = scores(test_preds, split["test"], with_ci=True)
    y = split["test"].y.values
    p = test_preds[chosen]
    model_key = chosen.split("_")[0]
    beta = fit_logistic(design(fit, model_key), fit.y.values) if chosen.endswith("logistic") else None

    # persistence in plain words, from the fitting years (what an officer can use with BMC's own gauges)
    cond = fit.groupby("heavy_today").y.mean()
    return {
        "target": f"Tomorrow is a heavy-rain day: IMD gridded rain >= {HEAVY_MM} mm in either Mumbai cell",
        "season": "June-September (by tomorrow's date)",
        "timing": "Issued at 08:30 IST from the 24 h just measured; predicts the next 24 h (IMD rain day)",
        "split_years": SPLIT,
        "n_days": {k: int(len(v)) for k, v in split.items()},
        "heavy_share": {k: round(float(v.y.mean()), 3) for k, v in split.items()},
        "validation": val,
        "chosen_on_validation": chosen,
        "test": test,
        "test_reliability_chosen": reliability(p, y),
        "chosen_coefficients": None if beta is None else {
            "names": ["intercept", "log1p_rain_today"] + (["log1p_rain_3d", "jul", "aug", "sep"] if model_key == "M2" else []),
            "values": [round(float(b), 4) for b in beta]},
        "persistence_1971_2016": {
            "p_heavy_tomorrow_if_heavy_today": round(float(cond.get(1, np.nan)), 3),
            "p_heavy_tomorrow_if_not_heavy_today": round(float(cond.get(0, np.nan)), 3),
            "n_heavy_today": int((fit.heavy_today == 1).sum()),
        },
    }


# ---------- part B ----------
def part_b() -> dict:
    day = pd.read_csv(PROC / "forecast_day1_santacruz.csv", parse_dates=["date"]).set_index("date")
    day = day.forecast_day1_mm.rename("fc_mm")
    obs = pd.read_csv(PROC / "rain_daily_imd.csv", parse_dates=["date"]).set_index("date").city_max_mm
    d = pd.concat([day, obs], axis=1, join="inner").dropna()
    d = d[d.index.month.isin(MONSOON)]
    d["heavy"] = d.city_max_mm >= HEAVY_MM
    d["bin"] = pd.cut(d.fc_mm, FC_BINS, right=False, labels=FC_BIN_LABEL)
    table = [{"forecast": str(b), "n_days": int(len(x)), "heavy_days": int(x.heavy.sum()),
              "heavy_share": None if len(x) == 0 else round(float(x.heavy.mean()), 3)}
             for b, x in d.groupby("bin", observed=False)]
    flag = d.fc_mm >= HEAVY_MM
    hits, misses, false_alarms = int((flag & d.heavy).sum()), int((~flag & d.heavy).sum()), int((flag & ~d.heavy).sum())
    return {
        "source": "Open-Meteo Previous Runs API, precipitation_previous_day1, Santacruz point (19.0896 N, 72.8656 E)",
        "period": f"{d.index.min():%Y-%m-%d} to {d.index.max():%Y-%m-%d}, June-September only",
        "years": sorted(int(y) for y in d.index.year.unique()),
        "n_days": int(len(d)),
        "observed_heavy_days": int(d.heavy.sum()),
        "by_forecast_amount": table,
        "forecast_ge_64_5mm": {"hits": hits, "misses": misses, "false_alarms": false_alarms,
                               "probability_of_detection": round(hits / (hits + misses), 3) if hits + misses else None,
                               "false_alarm_ratio": round(false_alarms / (hits + false_alarms), 3) if hits + false_alarms else None},
        "correlation_fc_vs_observed": round(float(np.corrcoef(d.fc_mm, d.city_max_mm)[0, 1]), 3),
        "caveat": "Two monsoons only; one forecast point vs the wetter of two 25 km observed cells. "
                  "Shares are descriptive frequencies, not a validated probability model.",
    }


def main() -> None:
    out = {"heavy_mm": HEAVY_MM, "observed_model": part_a(), "forecast_track_record": part_b()}
    (PROC / "outlook.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
