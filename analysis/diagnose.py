"""Rule-based diagnosis labels for each listed place: what kind of problem, and what to check.

The priority score answers "where first?", and its top places depend on the weights (score.py).
These labels answer "what should the inspection team do there?" and depend on NO weights: each is a
plain fact read from the official lists or the geocoder. A missing input never triggers a label.

Labels (a place can carry several):
  pump_gap             on BMC's 2026 list with no dewatering pump recorded
  list_gap             on the BEST or Traffic Police list but not on BMC's own 2026 list
  corroborated         named by 2+ of the three official lists
  traffic_critical     Mumbai Traffic Police plan a diversion here
  needs_location       only placed at neighbourhood level, or not placed at all

The three-cause idea (adapted from JunkSnap's city / citizen / bin-access split):
  drainage capacity -> pump_gap, corroborated
  list coverage     -> list_gap, needs_location
  exposure          -> traffic_critical (and ward history in the score)

Output: data/processed/diagnosis.csv, data/processed/diagnosis_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

LABELS = {
    "pump_gap": {
        "cause": "drainage capacity",
        "title": "No pump recorded",
        "rule": "On BMC's 2026 list of waterlogging spots, with the dewatering-pump cell blank",
        "check": "Confirm whether a pump is assigned, moved or no longer needed; record it before the monsoon",
    },
    "list_gap": {
        "cause": "list coverage",
        "title": "Missing from BMC's list",
        "rule": "Named by BEST or the Traffic Police, but not by BMC's own 2026 list",
        "check": "Ask the ward office to confirm the spot and add it to the BMC list, or record why not",
    },
    "corroborated": {
        "cause": "drainage capacity",
        "title": "Named by 2+ lists",
        "rule": "Independent official lists agree on this place",
        "check": "Pre-monsoon drain, culvert and outfall check",
    },
    "traffic_critical": {
        "cause": "exposure",
        "title": "Traffic diversion planned",
        "rule": "Mumbai Traffic Police divert traffic here when it waterlogs",
        "check": "Agree the alert contact with the traffic division before heavy-rain days",
    },
    "needs_location": {
        "cause": "list coverage",
        "title": "Exact spot unknown",
        "rule": "The official name could only be placed at neighbourhood level, or not at all",
        "check": "Field-verify the exact spot and record its coordinates",
    },
}


def diagnose(loc: pd.DataFrame) -> pd.DataFrame:
    d = pd.DataFrame({"location_id": loc.location_id})
    d["pump_gap"] = loc.in_bmc_fpg_2026 & loc.pumps.isna()
    d["list_gap"] = ~loc.in_bmc_fpg_2026 & (loc.in_best_annex_2026 | loc.in_mtp_2026)
    d["corroborated"] = loc.n_sources >= 2
    d["traffic_critical"] = loc.in_mtp_2026.astype(bool)
    d["needs_location"] = loc.geocode_precision.isin(["area", "not_mappable"])
    d["diagnosis"] = d[list(LABELS)].apply(lambda r: "|".join(k for k in LABELS if r[k]), axis=1)
    return d


def main() -> None:
    loc = pd.read_csv(PROC / "location_features.csv")
    d = diagnose(loc)
    d[["location_id", "diagnosis"]].to_csv(PROC / "diagnosis.csv", index=False)
    summary = {
        "n_locations": len(d),
        "labels": {k: {**v, "n": int(d[k].sum())} for k, v in LABELS.items()},
        "with_no_label": int((d.diagnosis == "").sum()),
    }
    (PROC / "diagnosis_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v["n"] for k, v in summary["labels"].items()} | {"none": summary["with_no_label"]}))


if __name__ == "__main__":
    main()
