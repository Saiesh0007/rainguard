"""Exploratory analysis: compute every finding from processed data and save figures.

No number in a finding is typed by hand - each is computed below and written to
data/processed/eda_findings.json, which the README, docs and app read from.
Figures go to docs/figures/.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pymupdf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TR = ROOT / "data" / "transcribed"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "docs" / "figures"
BLUE_RAMP = ["#86b6ef", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#184f95", "#0d366b"]  # ordinal 1-7
S1, S2, MUTED = "#2a78d6", "#eb6834", "#8a8984"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#b5b4ae", "axes.labelcolor": "#52514e", "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "figure.dpi": 130})


def best_edition_similarity() -> dict:
    """Word-level similarity of BEST Annex IX across the three published editions."""
    def words(fname: str) -> list[str]:
        doc = pymupdf.open(RAW / "best" / fname)
        pages = [p.get_text() for p in doc]
        st = [i for i, p in enumerate(pages) if re.search(r"ANNEXURE\W*IX", p)][-1]
        en = next(i for i, p in enumerate(pages) if i > st and re.search(r"reporting protocol", p, re.I))
        body = " ".join(pages[st:en])
        body = re.sub(r"ANNEXURE\W*IX|WARD WISE IDENTIFIED LOW LA[YI]ING FLOODING PRONE AREAS|"
                      r"Sr\.\s*No\.|Ward|Name of Road|Location", "", body)
        return re.sub(r"\s+", " ", body).strip().split(" ")
    eds = {e: words(f"Disaster_Management_Protocol_Booklet_{e}.pdf") for e in ["2023_24", "2024_25", "2026"]}
    return {f"{a}_vs_{b}": round(SequenceMatcher(None, eds[a], eds[b], autojunk=False).ratio(), 3)
            for a, b in [("2023_24", "2024_25"), ("2024_25", "2026")]}


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    wards = pd.read_csv(PROC / "ward_stats.csv")
    loc = pd.read_csv(PROC / "location_features.csv")
    fpg = pd.read_csv(TR / "bmc_fpg2026_waterlogging_spots.csv")
    best = pd.read_csv(TR / "best_annex_ix_2026.csv")
    rain = json.loads((PROC / "rainfall_summary.json").read_text())
    clim = pd.read_csv(PROC / "rainfall_monthly_climatology.csv")
    ann = pd.read_csv(PROC / "rainfall_annual_extremes.csv")
    ev = json.loads((PROC / "evaluation.json").read_text())
    clean = json.loads((PROC / "cleaning_log.json").read_text(encoding="utf8"))
    verify = json.loads((PROC / "transcription_verification.json").read_text())

    findings = []

    # ---------- F1: ward burden concentration ----------
    top = wards[wards.incident_class == 7]
    hi = wards[wards.incident_class >= 6]
    island = ["A", "B", "C", "D", "E", "F/S", "F/N", "G/S", "G/N"]
    f1 = {
        "id": "F1", "title": (
            f"{int((~wards.ward.isin(island) & (wards.incident_class >= 6)).sum())} of {int((~wards.ward.isin(island)).sum())} "
            f"suburban wards but {int((wards.ward.isin(island) & (wards.incident_class >= 6)).sum())} of {len(island)} "
            f"island-city wards are in the two highest incident classes - and ward population alone ranks wards "
            f"with Spearman rho = {ev['ward_level']['spearman_population_vs_class']['rho']:.2f}"),
        "evidence_type": "historical",
        "numbers": {
            "wards_in_top_class_467_800": sorted(top.ward.tolist()),
            "n_wards_top_class": int(len(top)),
            "share_population_in_class_6_or_7_wards": round(float(hi.population_2011.sum() / wards.population_2011.sum()), 3),
            "suburban_wards_in_class_6_or_7": int((~wards.ward.isin(island) & (wards.incident_class >= 6)).sum()),
            "suburban_wards": int((~wards.ward.isin(island)).sum()),
            "loo_mae_population_only": ev["ward_level"]["models"]["B1_population"]["loo_mae_classes"],
            "loo_mae_median_baseline": ev["ward_level"]["models"]["B0_median"]["loo_mae_classes"],
            "island_city_wards_max_class": int(wards[wards.ward.isin(island)].incident_class.max()),
            "island_city_wards_in_class_6_or_7": sorted(wards[wards.ward.isin(island) & (wards.incident_class >= 6)].ward.tolist()),
            "spearman_population_vs_class": ev["ward_level"]["spearman_population_vs_class"],
        },
        "method": "Ordinal incident class per ward digitised from BMC FPG 2026 p.18 (colour-matched to legend, "
                  "3 sample points per ward, 24/24 unanimous); population from Census 2011 aggregated to wards.",
        "period": "2016-2023 per map legend (caption says 2016-2025)",
        "sample": "24 legacy BMC wards",
        "caveats": ["Counts are complaint/incident records (source: 'CCS'), so they reflect reporting as well as flooding.",
                    "Only the class bin is known, not the exact count.",
                    "Census population is from 2011."],
        "figure": "figures/f1_ward_incident_class.png",
    }
    findings.append(f1)
    w_sorted = wards.sort_values(["incident_class", "population_2011"], ascending=[True, True])
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh(w_sorted.ward, w_sorted.incident_class, color=[BLUE_RAMP[c - 1] for c in w_sorted.incident_class],
            height=0.7)
    ax.set_xlabel("Incident class (1 = 0-115 ... 7 = 467-800 recorded incidents)")
    ax.set_title("Ward-wise waterlogging incident class, BMC map (2016-2023/25)", loc="left", fontsize=11)
    ax.set_xticks(range(1, 8))
    fig.tight_layout()
    fig.savefig(FIG / "f1_ward_incident_class.png")
    plt.close(fig)

    # ---------- F2: official lists disagree ----------
    mtp = pd.read_csv(TR / "mtp_fpg2026_diversions.csv")
    locs = pd.read_csv(PROC / "locations.csv")
    combos = clean["outputs"]["by_source_combination"]
    multi = int((locs.n_sources >= 2).sum())
    nil_wards = ["A", "B", "G/N"]
    f2 = {
        "id": "F2",
        "title": (f"Three official lists name {len(locs)} distinct places, but only {multi} "
                  f"({multi / len(locs):.0%}) appear on more than one list"),
        "evidence_type": "historical (official listings)",
        "numbers": {
            "bmc_fpg2026_rows": int(len(fpg)), "best_annex_rows": int(len(best)),
            "mtp_location_rows": int((mtp.is_location == "yes").sum()),
            "unique_locations_after_merge": int(len(locs)),
            "locations_on_2_or_more_lists": multi,
            "locations_on_all_3_lists": int((locs.n_sources == 3).sum()),
            "by_source_combination": combos,
            "best_rows_per_ward_where_bmc_lists_nil": {w: int((best.ward == w).sum()) for w in nil_wards},
            "best_edition_text_similarity": best_edition_similarity(),
            "bmc_sections_where_header_count_differs_from_rows": len(verify["bmc_fpg2026"]["header_vs_rows"]),
            "within_source_duplicates": len(clean["within_source_duplicates"]),
        },
        "method": "Same-ward matching: fuzzy name tokens (Jaccard >= 0.5, >= 2 shared tokens) or geocodes within "
                  "250 m plus partial name match; never merging two records of one source. Edition similarity = "
                  "word-level SequenceMatcher ratio of BEST Annex IX text.",
        "period": "BMC FPG 2026 (incl. Mumbai Traffic Police table); BEST booklets 2023-24, 2024-25, 2026",
        "sample": f"{len(fpg)} BMC rows (24 wards), {len(best)} BEST rows (9 island-city wards), "
                  f"{int((mtp.is_location == 'yes').sum())} traffic-police rows ({mtp.ward_legacy.nunique()} ward headings)",
        "caveats": ["The lists serve different purposes (BMC: dewatering pumps; BEST: switching off electricity; "
                    "traffic police: diversions), so they need not match - but none can be treated as complete.",
                    "Name matching can miss the same place written very differently, so overlap may be understated."],
        "figure": "figures/f2_source_overlap.png",
    }
    findings.append(f2)
    order = ["BMC_FPG_2026", "BEST_ANNEX_IX_2026", "MTP_DIVERSIONS_2026"]
    labels = {"BMC_FPG_2026": "BMC", "BEST_ANNEX_IX_2026": "BEST", "MTP_DIVERSIONS_2026": "Traffic police"}
    items = sorted(combos.items(), key=lambda kv: (-kv[1]))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    names = [" + ".join(labels[s_] for s_ in k.split("|")) for k, _ in items]
    ax.barh(names[::-1], [v for _, v in items][::-1], color=[S1 if "|" not in k else S2 for k, _ in items][::-1],
            height=0.6)
    ax.set_xlabel("Distinct locations")
    ax.set_title("Which official lists name each location", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "f2_source_overlap.png")
    plt.close(fig)

    # ---------- F3: rainfall concentration + reanalysis misses extremes ----------
    e5, imd, cmp_ = rain["era5"], rain["imd"], rain["era5_vs_imd_monthly_1991_2021"]
    f3 = {
        "id": "F3", "title": "Monsoon rain is extremely concentrated, and global-model rainfall misses Mumbai's extremes",
        "evidence_type": "observed (IMD gridded) and estimated (ERA5 reanalysis)",
        "numbers": {
            "imd_jjas_share_of_annual": imd["jjas_share_of_annual"],
            "imd_mean_annual_mm": imd["mean_annual_mm"],
            "imd_annual_trend_mm_per_decade": imd["annual_total_trend_1901_2021"]["theil_sen_slope_per_decade"],
            "imd_annual_trend_p": imd["annual_total_trend_1901_2021"]["p_value"],
            "era5_median_share_of_monsoon_rain_on_10_wettest_days": e5["median_top10_day_share_jjas"],
            "era5_mean_heavy_days_per_year": e5["mean_heavy_days_per_year"],
            "era5_heavy_days_trend_p": e5["heavy_days_trend"]["p_value"],
            "era5_2005_07_26_mm": e5["2005_07_26_mm"], "observed_2005_07_26_mm": e5["2005_07_26_reference_mm"],
            "era5_to_imd_annual_ratio": cmp_["era5_to_imd_ratio"], "era5_imd_monthly_r": cmp_["pearson_r_all_months"],
        },
        "method": "IMD monthly grid 19.00N 72.75E (1901-2021); ERA5 daily via Open-Meteo (1991-2025); Theil-Sen "
                  "slope + Kendall tau for trends; heavy day = IMD category >= 64.5 mm/24 h.",
        "period": "1901-2021 (IMD), 1991-2025 (ERA5)",
        "sample": f"{imd['years'][1] - imd['years'][0] + 1} years IMD; {e5['days']} days ERA5",
        "caveats": ["ERA5 is a ~25 km model estimate; both Mumbai reference points fall in one cell, so it cannot show "
                    "rainfall differences between neighbourhoods.",
                    "The 944 mm figure is a station record quoted by BMC; ERA5 is an area average, so some gap is expected - "
                    "the size of the gap is the point."],
        "figure": "figures/f3_rainfall.png",
    }
    findings.append(f3)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    axes[0].bar(clim.month, clim["mean"], color=S1, width=0.7)
    axes[0].set_xticks(range(1, 13), list("JFMAMJJASOND"))
    axes[0].set_ylabel("Mean monthly rain (mm)")
    axes[0].set_title("IMD 1901-2021 monthly mean", loc="left", fontsize=10)
    axes[1].bar(ann.year, ann.heavy_days, color=S1, width=0.7)
    axes[1].set_ylabel("Days >= 64.5 mm (ERA5)")
    axes[1].set_title("Heavy-rain days per year, ERA5", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "f3_rainfall.png")
    plt.close(fig)

    # ---------- F4: terrain ----------
    cc = ev["location_terrain_case_control"]
    f4 = {
        "id": "F4", "title": (
            "Precisely located listed spots sit lower than the rest of their ward"
            if (cc["point_or_street"]["tpi_pct_in_ward"]["wilcoxon_p_vs_0.5"] or 1) < 0.05
            and cc["point_or_street"]["tpi_pct_in_ward"]["median"] < 0.5
            else "Terrain (90 m DEM) does not clearly separate listed spots from the rest of their ward"),
        "evidence_type": "estimated (DEM terrain) against historical listings",
        "numbers": cc,
        "method": "Copernicus GLO-90 DEM via Open-Meteo; TPI = elevation minus median of 500 m grid cells within 1 km; "
                  "each location's percentile among its own ward's grid cells; Wilcoxon signed-rank vs 0.5.",
        "period": "DEM 2021 release; listings 2026",
        "sample": f"{cc['point_or_street']['n']} point/street-precision locations; {cc['area_only']['n']} area-only shown separately",
        "caveats": ["GLO-90 is a 90 m surface model including buildings; vertical error is metres.",
                    "Geocoding error (tens to hundreds of metres) blurs the comparison.",
                    "Listed spots are not a random sample of flooded places."],
        "figure": "figures/f4_terrain_percentiles.png",
    }
    findings.append(f4)
    prec = loc[loc.geocode_precision.isin(["point", "street"]) & loc.tpi_pct_in_ward.notna()]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, col, name in [(axes[0], "tpi_pct_in_ward", "Relative elevation (TPI) percentile"),
                          (axes[1], "elev_pct_in_ward", "Elevation percentile")]:
        ax.hist(prec[col], bins=np.linspace(0, 1, 11), color=S1, rwidth=0.9)
        ax.axhline(len(prec) / 10, color=MUTED, ls="--", lw=1)
        ax.set_xlabel(f"{name} within own ward")
    axes[0].set_ylabel("Listed locations")
    fig.suptitle("If terrain carried no signal, bars would sit on the dashed line", x=0.02, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "f4_terrain_percentiles.png")
    plt.close(fig)

    # ---------- F5: pump coverage ----------
    pumps = pd.to_numeric(fpg.dewatering_pumps, errors="coerce")
    f5 = {
        "id": "F5", "title": (
            f"{int(pumps.isna().sum())} of {len(fpg)} BMC-listed spots have no dewatering pump recorded against them"),
        "evidence_type": "historical (official listing, 2026)",
        "numbers": {
            "bmc_rows": int(len(fpg)),
            "rows_with_pump_listed": int(pumps.gt(0).sum()),
            "rows_without_pump_listed": int(pumps.isna().sum()),
            "total_pumps_listed": int(pumps.sum()),
            "rows_marked_planning_stage": int(fpg.project_category.fillna("").str.contains("Planning", case=False).sum()),
            "rows_capacity_incomplete": int(((pumps > 0) & fpg.transcription_note.fillna("").str.contains("capacity")).sum()),
        },
        "method": "Direct counts from the transcribed BMC FPG 2026 ward directory.",
        "period": "Monsoon 2026 preparedness",
        "sample": f"{len(fpg)} rows",
        "caveats": ["A blank pump cell may mean no pump, a pump recorded elsewhere, or a mitigated spot - the source does not say.",
                    "Capacity figures are incomplete for several multi-pump spots."],
        "figure": None,
    }
    findings.append(f5)

    (PROC / "eda_findings.json").write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf8")
    for f in findings:
        print(f"{f['id']}: {f['title']}\n   {json.dumps(f['numbers'])}")


if __name__ == "__main__":
    main()
