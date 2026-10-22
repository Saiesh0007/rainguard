"""Tests for the RainGuard analysis pipeline.

Unit tests cover the transformation rules; integrity tests check the committed processed
outputs (run `python analysis/run_pipeline.py` first if you changed inputs).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

import allocate  # noqa: E402
import clean_data  # noqa: E402
import diagnose  # noqa: E402
import evaluate  # noqa: E402
import predict  # noqa: E402
import score  # noqa: E402

PROC = ROOT / "data" / "processed"
TR = ROOT / "data" / "transcribed"
WARDS = {"A", "B", "C", "D", "E", "F/N", "F/S", "G/N", "G/S", "H/E", "H/W", "K/E", "K/W", "L",
         "M/E", "M/W", "N", "P/N", "P/S", "R/C", "R/N", "R/S", "S", "T"}


# ---------------- unit tests: matching rules ----------------
def test_norm_and_tokens_drop_noise():
    assert clean_data.norm("Dr. B.A.  Road!") == "dr b a road"
    assert clean_data.tokens("Hindmata Junction North Bond") == {"hindmata"}
    assert "road" not in clean_data.tokens("Hill Road")


def test_fuzzy_overlap_tolerates_spelling_variants():
    jac, shared = clean_data.fuzzy_overlap({"vacchraj"}, {"vachharaj"})
    assert jac == 1.0 and shared == 1
    jac, shared = clean_data.fuzzy_overlap({"bhandup"}, {"bhandup", "village"})
    assert shared == 1 and jac == 0.5


def test_road_numbers_detect_conflicts():
    assert clean_data.road_numbers("Mukhyadhyap Bhavan, Road no. 24") == {"24"}
    assert clean_data.road_numbers("Rd No.6, Sion") == {"6"}
    assert clean_data.road_numbers("Hill Road") == set()


def test_haversine_known_distance():
    # one degree of latitude is ~111.2 km
    assert clean_data.haversine_m(19.0, 72.8, 20.0, 72.8) == pytest.approx(111_195, rel=1e-3)


def test_union_find_merges_transitively():
    uf = clean_data.UnionFind(["a", "b", "c", "d"])
    uf.union("a", "b")
    uf.union("b", "c")
    assert uf.find("c") == uf.find("a") != uf.find("d")


# ---------------- unit tests: scoring ----------------
def _loc(**kw):
    base = {"incident_class": 7, "incident_excess": 0.5, "n_sources": 1, "geocode_precision": "area",
            "tpi_pct_in_ward": 0.1, "neighbours_1km": 4}
    base.update(kw)
    return pd.DataFrame([base])


def test_low_lying_only_for_precise_geocodes():
    assert np.isnan(score.components(_loc(geocode_precision="area")).low_lying.iloc[0])
    assert score.components(_loc(geocode_precision="point")).low_lying.iloc[0] == pytest.approx(0.9)


def test_score_skips_missing_components_and_renormalises():
    c = score.components(_loc(geocode_precision="area", neighbours_1km=10, n_sources=3))
    # ward_burden 1, corroboration 1, listing_density 1; low_lying missing (area geocode) and ward_excess
    # missing (min-max of a single ward is undefined) -> 100 regardless of their weights
    w = {"ward_burden": 1, "ward_excess": 1, "corroboration": 1, "low_lying": 1, "listing_density": 1}
    assert score.score(c, w).iloc[0] == 100


def test_ward_excess_scales_population_residual_to_unit_range():
    c = score.components(pd.concat([_loc(incident_excess=x) for x in (-1.0, 0.0, 1.0)]))
    assert list(c.ward_excess) == [0, 0.5, 1]


# ---------------- unit tests: diagnosis and plan ----------------
def _dloc(**kw):
    base = {"location_id": "RG-1", "in_bmc_fpg_2026": True, "in_best_annex_2026": False, "in_mtp_2026": False,
            "pumps": np.nan, "n_sources": 1, "geocode_precision": "point"}
    base.update(kw)
    return pd.DataFrame([base])


def test_pump_gap_needs_bmc_listing_and_blank_pump():
    assert diagnose.diagnose(_dloc()).pump_gap.iloc[0]
    assert not diagnose.diagnose(_dloc(pumps=2)).pump_gap.iloc[0]
    # not on BMC's list -> pump information is unknown, never a gap
    assert not diagnose.diagnose(_dloc(in_bmc_fpg_2026=False, in_mtp_2026=True)).pump_gap.iloc[0]


def test_list_gap_and_location_labels():
    d = diagnose.diagnose(_dloc(in_bmc_fpg_2026=False, in_best_annex_2026=True, geocode_precision="area")).iloc[0]
    assert d.list_gap and d.needs_location and d.diagnosis == "list_gap|needs_location"


def test_plan_respects_ward_cap_and_k():
    rank = pd.Series([1, 2, 3, 4, 5])
    ward = pd.Series(["A", "A", "A", "B", "B"])
    ids = pd.Series(["p1", "p2", "p3", "p4", "p5"])
    assert allocate.plan(rank, ward, ids, k=3, cap=2) == [0, 1, 3]
    assert allocate.plan(rank, ward, ids, k=10, cap=1) == [0, 3]


# ---------------- unit tests: heavy-rain outlook ----------------
def test_logistic_fit_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    x = rng.normal(size=20000)
    X = np.column_stack([np.ones_like(x), x])
    y = (rng.random(20000) < 1 / (1 + np.exp(-(-1 + 2 * x)))).astype(float)
    assert np.allclose(predict.fit_logistic(X, y), [-1, 2], atol=0.1)


def test_auc_perfect_and_random():
    y = np.array([0, 0, 1, 1])
    assert predict.auc(np.array([0.1, 0.2, 0.8, 0.9]), y) == 1
    assert predict.auc(np.array([0.5, 0.5, 0.5, 0.5]), y) == 0.5


def test_outlook_split_is_chronological_and_features_use_only_past():
    s = predict.SPLIT
    assert s["train"][1] < s["validate"][0] and s["validate"][1] < s["test"][0]
    t = predict.daily_table()
    d = pd.read_csv(PROC / "rain_daily_imd.csv", parse_dates=["date"]).set_index("date").city_max_mm
    day = t.index[100]
    # today's features equal observed rain up to today; the target is tomorrow's rain
    assert t.loc[day, "rain_today"] == d[day]
    assert t.loc[day, "rain_3d"] == pytest.approx(d[day - pd.Timedelta(days=2):day].sum())
    assert t.loc[day, "y"] == float(d[day + pd.Timedelta(days=1)] >= predict.HEAVY_MM)


def test_score_zero_weights_returns_zero_not_nan():
    c = score.components(_loc())
    assert score.score(c, {k: 0 for k in score.COMPONENTS}).iloc[0] == 0


def test_corroboration_scale():
    assert list(score.components(pd.concat([_loc(n_sources=n) for n in (1, 2, 3)])).corroboration) == [0, 0.5, 1]


def test_ranks_treat_float_noise_as_ties():
    s = pd.Series([100 / 3, 33.333333333333336, 10.0])
    assert list(score.ranks(s)) == [1, 1, 3]


# ---------------- unit tests: evaluation ----------------
def test_loo_predict_recovers_linear_signal():
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 1, (30, 1))
    y = 1 + 5 * x[:, 0]
    pred = evaluate.loo_predict(x, y)
    assert np.abs(pred - y).max() < 1e-6


def test_loo_median_baseline_has_no_features():
    y = np.array([1, 2, 3, 4, 5.0])
    pred = evaluate.loo_predict(np.empty((5, 0)), y)
    assert pred[0] == np.median(y[1:])


# ---------------- integrity tests on processed outputs ----------------
@pytest.fixture(scope="module")
def locations():
    return pd.read_csv(PROC / "locations.csv")


def test_every_transcribed_location_row_is_accounted_for(locations):
    ids = [r for cell in locations.record_ids for r in cell.split("|")]
    assert len(ids) == len(set(ids)), "a record appears in two locations"
    fpg = set(pd.read_csv(TR / "bmc_fpg2026_waterlogging_spots.csv").record_id)
    best = set(pd.read_csv(TR / "best_annex_ix_2026.csv").record_id)
    mtp = pd.read_csv(TR / "mtp_fpg2026_diversions.csv")
    expected = fpg | best | set(mtp[mtp.is_location == "yes"].record_id)
    assert set(ids) == expected
    assert not set(mtp[mtp.is_location == "no"].record_id) & set(ids)


def test_location_fields_are_valid(locations):
    assert locations.location_id.is_unique
    assert set(locations.ward) <= WARDS
    assert set(locations.geocode_precision) <= {"point", "street", "area", "not_mappable"}
    mapped = locations[locations.geocode_precision != "not_mappable"]
    assert mapped.lat.between(18.85, 19.3).all() and mapped.lon.between(72.75, 73.05).all()
    assert locations[locations.geocode_precision == "not_mappable"].lat.isna().all()
    assert (locations.n_sources == locations[["in_bmc_fpg_2026", "in_best_annex_2026", "in_mtp_2026"]].sum(axis=1)).all()


def test_no_personal_phone_numbers_anywhere():
    for f in list(TR.glob("*.csv")) + [PROC / "locations.csv", ROOT / "app" / "public" / "data" / "rainguard.json"]:
        assert not re.search(r"\b\d{10}\b", f.read_text(encoding="utf8")), f


def test_geocode_review_never_upgrades_precision():
    g = pd.read_csv(PROC / "geocoded_locations.csv")
    rev = pd.read_csv(TR / "geocode_review.csv")
    merged = rev.merge(g, on="record_id")
    assert (merged.reviewed_precision == merged.geocode_precision).all()


def test_ward_incident_classes_complete_and_unanimous():
    w = pd.read_csv(PROC / "ward_incident_class.csv")
    assert set(w.ward) == WARDS
    assert w.incident_class.between(1, 7).all()
    assert (w.points_agreeing == w.points_total).all()


def test_census_population_matches_official_total():
    w = pd.read_csv(PROC / "ward_stats.csv")
    assert w.population_2011.sum() == 12_442_373  # Census 2011, Greater Mumbai


def test_transcriptions_verified_against_sources():
    v = json.loads((PROC / "transcription_verification.json").read_text())
    assert v["mtp_diversions_2026"]["matched"] == v["mtp_diversions_2026"]["rows"]
    assert v["best_annex_ix_2026"]["matched"] >= v["best_annex_ix_2026"]["rows"] - 1
    assert v["bmc_fpg2026"]["matched"] >= 0.9 * v["bmc_fpg2026"]["rows"]


def test_findings_are_computed_and_complete():
    f = json.loads((PROC / "eda_findings.json").read_text(encoding="utf8"))
    assert len(f) >= 6
    for x in f:
        assert x["method"] and x["period"] and x["sample"] and x["caveats"]


def test_priority_scores_match_default_weights():
    loc = pd.read_csv(PROC / "location_features.csv")
    s = pd.read_csv(PROC / "priority_scores.csv")
    recomputed = score.score(score.components(loc), score.DEFAULT_WEIGHTS)
    assert np.allclose(recomputed.round(1).values, s.priority_score.values)


def test_imd_daily_matches_opencity_monthly_series():
    c = json.loads((PROC / "rain_daily_checks.json").read_text())["monthly_vs_opencity_same_point"]
    assert c["n_months"] > 500 and c["pearson_r"] > 0.99 and c["median_abs_diff_mm"] == 0


def test_outlook_test_years_were_not_used_for_model_choice():
    o = json.loads((PROC / "outlook.json").read_text())["observed_model"]
    assert o["chosen_on_validation"] in o["validation"]
    assert o["split_years"]["test"][0] > o["split_years"]["validate"][1]


def test_imd_date_convention_matches_26_july_2005():
    # the record storm of 26 July 2005 must sit on 27 July (IMD day = 24 h ending 08:30 IST)
    j = json.loads((PROC / "rain_daily_checks.json").read_text())["jul_2005"]
    assert j["2005-07-27"]["north_mm"] > 300 > j["2005-07-26"]["north_mm"]
