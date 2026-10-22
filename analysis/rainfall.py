"""Rainfall context for Mumbai from two public sources, plus a reliability check.

Sources
  * IMD 0.25-degree gridded monthly rainfall for the grid point 19.00N 72.75E, 1901-2021,
    as republished by OpenCity (observation-based gridded analysis).
  * ERA5 reanalysis daily precipitation via the Open-Meteo Historical Weather API,
    1991-2025 (model-based estimate, ~25 km cells; both Mumbai reference points fall in
    the same cell, so there is ONE series for the whole city).

Outputs (data/processed/):
  rainfall_monthly_climatology.csv, rainfall_annual_extremes.csv, rainfall_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

# IMD daily rainfall intensity categories (mm in 24 h)
HEAVY, VERY_HEAVY, EXTREME = 64.5, 115.6, 204.5
MONTHS = ["Jan", "Feb", "Mar", "April", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]


def load_imd() -> pd.DataFrame:
    df = pd.read_csv(RAW / "imd_mumbai_monthly_1901_2021.csv")
    long = df.melt(id_vars="Year", value_vars=MONTHS, var_name="month_name", value_name="rain_mm")
    long["month"] = long.month_name.map({m: i + 1 for i, m in enumerate(MONTHS)})
    # sanity: recomputed annual totals must match the published Total column
    recomputed = long.groupby("Year").rain_mm.sum()
    max_err = float((recomputed - df.set_index("Year").Total).abs().max())
    assert max_err < 0.01, f"IMD monthly values do not sum to published totals (max err {max_err})"
    return long.rename(columns={"Year": "year"})[["year", "month", "rain_mm"]]


def load_era5() -> pd.DataFrame:
    j = json.loads((RAW / "open_meteo_era5_daily_santacruz.json").read_text())
    d = pd.DataFrame({"date": pd.to_datetime(j["daily"]["time"]), "rain_mm": j["daily"]["precipitation_sum"]})
    assert d.rain_mm.notna().all() and (d.rain_mm >= 0).all()
    assert d.date.is_unique and d.date.diff().dropna().eq(pd.Timedelta(days=1)).all(), "gaps in ERA5 series"
    meta = {"grid_lat": j["latitude"], "grid_lon": j["longitude"], "grid_elevation_m": j["elevation"]}
    return d, meta


def trend(years: np.ndarray, values: np.ndarray) -> dict:
    tau, p = stats.kendalltau(years, values)
    slope, intercept, lo, hi = stats.theilslopes(values, years)
    return {"kendall_tau": round(float(tau), 3), "p_value": round(float(p), 4),
            "theil_sen_slope_per_decade": round(float(slope) * 10, 2),
            "slope_95ci_per_decade": [round(float(lo) * 10, 2), round(float(hi) * 10, 2)]}


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    imd = load_imd()
    era5, meta = load_era5()

    # --- climatology (IMD, 1901-2021) ---
    clim = imd.groupby("month").rain_mm.agg(["mean", "median"]).round(1)
    annual_imd = imd.groupby("year").rain_mm.sum()
    jjas_share = float(imd[imd.month.between(6, 9)].rain_mm.sum() / imd.rain_mm.sum())
    clim.to_csv(PROC / "rainfall_monthly_climatology.csv")

    # --- ERA5 daily extremes 1991-2025 ---
    era5["year"] = era5.date.dt.year
    era5["month"] = era5.date.dt.month
    ann = era5.groupby("year").agg(
        total_mm=("rain_mm", "sum"), max_day_mm=("rain_mm", "max"),
        heavy_days=("rain_mm", lambda s: int((s >= HEAVY).sum())),
        very_heavy_days=("rain_mm", lambda s: int((s >= VERY_HEAVY).sum())),
        extreme_days=("rain_mm", lambda s: int((s >= EXTREME).sum())),
    ).round(1)
    # share of each monsoon's rain that fell on its 10 wettest days
    jjas = era5[era5.month.between(6, 9)]
    top10 = jjas.groupby("year").rain_mm.apply(lambda s: s.nlargest(10).sum() / s.sum())
    ann["top10_day_share_jjas"] = top10.round(3)
    ann.to_csv(PROC / "rainfall_annual_extremes.csv")

    # --- reliability: ERA5 vs IMD monthly totals over the overlap 1991-2021 ---
    era5_m = era5.groupby(["year", "month"]).rain_mm.sum().rename("era5_mm")
    imd_m = imd.set_index(["year", "month"]).rain_mm.rename("imd_mm")
    both = pd.concat([era5_m, imd_m], axis=1, join="inner").dropna()
    wet = both[both.index.get_level_values("month").isin([6, 7, 8, 9])]
    r, _ = stats.pearsonr(both.era5_mm, both.imd_mm)
    ann_both = both.groupby(level="year").sum()
    jul26_2005 = float(era5.loc[era5.date == "2005-07-26", "rain_mm"].iloc[0])

    summary = {
        "imd": {
            "source": "IMD gridded monthly rainfall, grid point 19.00N 72.75E, via OpenCity",
            "years": [int(imd.year.min()), int(imd.year.max())],
            "mean_annual_mm": round(float(annual_imd.mean()), 0),
            "jjas_share_of_annual": round(jjas_share, 3),
            "wettest_month": int(clim["mean"].idxmax()),
            "annual_total_trend_1901_2021": trend(annual_imd.index.values, annual_imd.values),
        },
        "era5": {
            "source": "ERA5 reanalysis daily precipitation via Open-Meteo Historical Weather API",
            **meta,
            "years": [int(era5.year.min()), int(era5.year.max())],
            "days": int(len(era5)),
            "mean_heavy_days_per_year": round(float(ann.heavy_days.mean()), 2),
            "mean_very_heavy_days_per_year": round(float(ann.very_heavy_days.mean()), 2),
            "mean_extreme_days_per_year": round(float(ann.extreme_days.mean()), 2),
            "median_top10_day_share_jjas": round(float(ann.top10_day_share_jjas.median()), 3),
            "heavy_days_trend": trend(ann.index.values, ann.heavy_days.values),
            "max_day": {"date": str(era5.loc[era5.rain_mm.idxmax(), "date"].date()),
                        "mm": round(float(era5.rain_mm.max()), 1)},
            "2005_07_26_mm": round(jul26_2005, 1),
            "2005_07_26_reference_mm": 944,
            "2005_07_26_reference_source": "BMC Flood Preparedness Guidelines 2026, p.17 (Santacruz record)",
        },
        "era5_vs_imd_monthly_1991_2021": {
            "n_months": int(len(both)),
            "pearson_r_all_months": round(float(r), 3),
            "pearson_r_jjas_months": round(float(stats.pearsonr(wet.era5_mm, wet.imd_mm)[0]), 3),
            "mean_annual_era5_mm": round(float(ann_both.era5_mm.mean()), 0),
            "mean_annual_imd_mm": round(float(ann_both.imd_mm.mean()), 0),
            "era5_to_imd_ratio": round(float(ann_both.era5_mm.sum() / ann_both.imd_mm.sum()), 3),
        },
    }
    (PROC / "rainfall_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
