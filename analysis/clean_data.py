"""Validate, de-duplicate and merge the two official location lists into one table.

Inputs  : data/transcribed/*.csv, data/processed/geocoded_locations.csv
Outputs : data/processed/locations.csv      one row per unique location
          data/processed/cleaning_log.json  every merge, match and flag, with reasons

Sources: BMC FPG 2026 ward directory, BEST Annexure IX 2026, and the Mumbai Traffic Police
diversion table printed in BMC FPG 2026 (rows that are not locations are excluded).

Rules (documented in docs/methodology.md):
1. Schema: required columns present, ward codes are legacy BMC wards, pump counts are
   non-negative integers, capacities parse as numbers.
2. Privacy guard: no 10-digit phone numbers may appear anywhere in the transcriptions.
3. Within-source duplicates: same source + same ward + identical normalised text -> merged.
4. Cross-source matches (any two different sources): same ward AND either
   (a) fuzzy token Jaccard >= 0.5 on distinctive name tokens with >= 2 shared tokens
       (or a complete match, Jaccard = 1, for single-token names), or
   (b) both geocoded at point/street precision within 250 m AND Jaccard >= 0.25
       (proximity alone is not enough in the dense island city), and in both cases
   (c) no conflicting explicit road numbers (e.g. "Road No. 24" vs "Road No. 6"), and
   (d) the merge never joins two different records of the SAME source (logged as ambiguous).
   A manual review file (data/transcribed/match_review.csv) can only reject matches.
   Matches are merged into one location that lists both sources (corroboration).
Nothing is imputed: missing pump data stays missing.
"""
from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "data" / "transcribed"
PROC = ROOT / "data" / "processed"
LEGACY_WARDS = {"A", "B", "C", "D", "E", "F/N", "F/S", "G/N", "G/S", "H/E", "H/W", "K/E", "K/W", "L",
                "M/E", "M/W", "N", "P/N", "P/S", "R/C", "R/N", "R/S", "S", "T"}
STOPWORDS = {"road", "rd", "marg", "near", "nr", "no", "opp", "junction", "jn", "mumbai", "east", "west",
             "station", "railway", "rly", "stn", "the", "of", "at", "to", "and", "lane", "full", "behind",
             "in", "front", "side", "low", "level", "area", "below", "bridge", "from", "towards",
             # traffic-direction qualifiers used by the traffic-police table, not place names
             "north", "south", "bond", "bound", "traffic"}
MATCH_JACCARD = 0.5
MATCH_DISTANCE_M = 250
MATCH_JACCARD_WITH_PROXIMITY = 0.25


def norm(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip() if pd.notna(s) else ""


def tokens(s: str) -> set[str]:
    return {t for t in norm(s).split() if len(t) > 1 and t not in STOPWORDS and not t.isdigit()}


def fuzzy_overlap(a: set[str], b: set[str]) -> tuple[float, int]:
    """(fuzzy Jaccard, number of shared tokens); tokens match when similarity >= 0.8."""
    if not a or not b:
        return 0.0, 0
    matched = sum(any(SequenceMatcher(None, x, y).ratio() >= 0.8 for y in b) for x in a)
    return matched / (len(a) + len(b) - matched), matched


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


def road_numbers(s: str) -> set[str]:
    return set(re.findall(r"\b(?:road|rd)\s*(?:no\.?)?\s*(\d+)", str(s).lower()))


def parse_capacity(v) -> list[float]:
    return [] if pd.isna(v) or str(v).strip() == "" else [float(x) for x in str(v).split(";")]


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fpg = pd.read_csv(TR / "bmc_fpg2026_waterlogging_spots.csv", dtype=str)
    best = pd.read_csv(TR / "best_annex_ix_2026.csv", dtype=str)
    mtp = pd.read_csv(TR / "mtp_fpg2026_diversions.csv", dtype=str)
    for df, cols in [(fpg, ["record_id", "ward_legacy", "location_published"]),
                     (best, ["record_id", "ward", "area_or_road"]),
                     (mtp, ["record_id", "ward_legacy", "location_published", "diversion_published", "is_location"])]:
        missing = set(cols) - set(df.columns)
        assert not missing, f"missing columns {missing}"
        assert df.record_id.is_unique, "duplicate record ids"
    assert set(fpg.ward_legacy) <= LEGACY_WARDS and set(best.ward) <= LEGACY_WARDS \
        and set(mtp.ward_legacy) <= LEGACY_WARDS, "unknown ward code"
    assert set(mtp.is_location) <= {"yes", "no"}
    pumps = pd.to_numeric(fpg.dewatering_pumps, errors="coerce")
    assert (pumps.dropna() >= 0).all() and (pumps.dropna() % 1 == 0).all()
    fpg.pump_capacity_m3hr_listed.apply(parse_capacity)  # raises on unparsable values
    phone = re.compile(r"\b\d{10}\b")
    for df in (fpg, best, mtp):
        assert not df.apply(lambda c: c.fillna("").str.contains(phone)).any().any(), "phone number found"
    return fpg, best, mtp


SOURCES = ["BMC_FPG_2026", "BEST_ANNEX_IX_2026", "MTP_DIVERSIONS_2026"]


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def main() -> None:
    fpg, best, mtp = load()
    geo = pd.read_csv(PROC / "geocoded_locations.csv").set_index("record_id")
    log: dict = {"inputs": {"bmc_fpg2026_rows": len(fpg), "best_annex_rows": len(best), "mtp_rows": len(mtp)},
                 "excluded": [], "ward_reassigned": [], "within_source_duplicates": [],
                 "cross_source_matches": [], "ambiguous_matches_skipped": [], "unmapped": []}

    recs = []
    for r in fpg.itertuples():
        caps = parse_capacity(r.pump_capacity_m3hr_listed)
        pumps = None if pd.isna(r.dewatering_pumps) else int(r.dewatering_pumps)
        recs.append({"record_id": r.record_id, "source": "BMC_FPG_2026", "ward": r.ward_legacy,
                     "name": r.location_published, "detail": "", "diversion": "",
                     "project_category": r.project_category,
                     "pumps": pumps, "capacity_listed_m3hr": sum(caps) if caps else None,
                     "capacity_complete": bool(pumps) and len(caps) == pumps})
    for r in best.itertuples():
        recs.append({"record_id": r.record_id, "source": "BEST_ANNEX_IX_2026", "ward": r.ward,
                     "name": r.area_or_road, "detail": "" if pd.isna(r.location_detail) else r.location_detail,
                     "diversion": "", "project_category": None, "pumps": None,
                     "capacity_listed_m3hr": None, "capacity_complete": False})
    for r in mtp.itertuples():
        if r.is_location != "yes":
            log["excluded"].append({"record": r.record_id, "text": r.location_published,
                                    "reason": r.transcription_note if pd.notna(r.transcription_note) else "not a location"})
            continue
        recs.append({"record_id": r.record_id, "source": "MTP_DIVERSIONS_2026", "ward": r.ward_legacy,
                     "name": r.location_published, "detail": "", "diversion": r.diversion_published,
                     "project_category": None, "pumps": None, "capacity_listed_m3hr": None,
                     "capacity_complete": False})
    df = pd.DataFrame(recs)
    df["text_norm"] = [norm(f"{n} {d}") for n, d in zip(df.name, df.detail)]
    df = df.join(geo[["lat", "lon", "geocode_precision", "ward_check", "osm_name", "review_note"]], on="record_id")
    # Traffic-police rows whose specific geocode lies in another ward were re-assigned by geocode.py
    for rid, w in geo[geo.ward_check == "reassigned"].ward_legacy.items():
        old = df.loc[df.record_id == rid, "ward"].iloc[0]
        df.loc[df.record_id == rid, "ward"] = w
        log["ward_reassigned"].append({"record": rid, "heading_ward": old, "geocoded_ward": w})

    uf = UnionFind(df.record_id)
    # --- 3. within-source duplicates ---
    for (src, ward, txt), g in df.groupby(["source", "ward", "text_norm"]):
        if len(g) > 1:
            for rid in g.record_id.iloc[1:]:
                uf.union(g.record_id.iloc[0], rid)
            log["within_source_duplicates"].append({"records": list(g.record_id),
                                                    "reason": "identical normalised text in same source and ward"})

    # --- 4. cross-source matches (every pair of different sources, same ward) ---
    # data/transcribed/match_review.csv may only REJECT automatic matches (never create them)
    review = pd.read_csv(TR / "match_review.csv")
    rejected = {frozenset((r.a, r.b)): r.reason for r in review.itertuples() if r.decision == "reject"}
    log["matches_rejected_by_review"] = [{"a": sorted(k)[0], "b": sorted(k)[1], "reason": v} for k, v in rejected.items()]
    precise = {"point", "street"}
    for i, a in df.iterrows():
        for _, b in df[(df.ward == a.ward) & (df.index > i) & (df.source != a.source)].iterrows():
            ta, tb = f"{a['name']} {a.detail}".strip(), f"{b['name']} {b.detail}".strip()
            jac, shared = fuzzy_overlap(tokens(ta), tokens(tb))
            dist = (haversine_m(a.lat, a.lon, b.lat, b.lon)
                    if a.geocode_precision in precise and b.geocode_precision in precise else None)
            nums_a, nums_b = road_numbers(ta), road_numbers(tb)
            conflict = bool(nums_a and nums_b and not nums_a & nums_b)
            near = dist is not None and dist <= MATCH_DISTANCE_M and jac >= MATCH_JACCARD_WITH_PROXIMITY
            if frozenset((a.record_id, b.record_id)) in rejected:
                continue
            if not conflict and ((jac >= MATCH_JACCARD and (shared >= 2 or jac == 1.0)) or near):
                ga, gb = uf.find(a.record_id), uf.find(b.record_id)
                src_a = {s_ for r_, s_ in zip(df.record_id, df.source) if uf.find(r_) == ga}
                src_b = {s_ for r_, s_ in zip(df.record_id, df.source) if uf.find(r_) == gb}
                if ga != gb and src_a & src_b:
                    log["ambiguous_matches_skipped"].append({
                        "a": a.record_id, "b": b.record_id, "a_name": ta, "b_name": tb,
                        "reason": "would merge two different records of the same source"})
                    continue
                uf.union(a.record_id, b.record_id)
                log["cross_source_matches"].append({
                    "a": a.record_id, "b": b.record_id, "a_name": ta, "b_name": tb,
                    "token_jaccard": round(jac, 2), "distance_m": None if dist is None else round(dist)})
    df["group"] = [uf.find(r) for r in df.record_id]

    # --- 5. build one row per location ---
    rank = {"point": 0, "street": 1, "area": 2, "not_found": 3}
    rows = []
    for gid, g in df.groupby("group", sort=False):
        ok = g[g.ward_check.isin(["inside", "reassigned"])].copy()
        ok["r"] = ok.geocode_precision.map(rank)
        geo_src = ok.sort_values("r").iloc[0] if len(ok) else None
        fpg_part = g[g.source == "BMC_FPG_2026"]
        lead = next(g[g.source == s].iloc[0] for s in SOURCES if (g.source == s).any())
        srcs = sorted(set(g.source))
        rows.append({
            "group_id": gid,
            "name": lead["name"],
            "detail": "; ".join(sorted({d for d in g.detail if d})),
            "ward": lead.ward,
            "sources": "|".join(srcs),
            "n_sources": len(srcs),
            "record_ids": "|".join(g.record_id),
            "n_records": len(g),
            "in_bmc_fpg_2026": "BMC_FPG_2026" in srcs,
            "in_best_annex_2026": "BEST_ANNEX_IX_2026" in srcs,
            "in_mtp_2026": "MTP_DIVERSIONS_2026" in srcs,
            "traffic_diversion": " || ".join(d for d in g.diversion if d),
            "lat": None if geo_src is None else geo_src.lat,
            "lon": None if geo_src is None else geo_src.lon,
            "geocode_precision": "not_mappable" if geo_src is None else geo_src.geocode_precision,
            "geocode_osm_name": None if geo_src is None else geo_src.osm_name,
            "geocode_note": None if geo_src is None else geo_src.review_note,
            "project_category": next((p for p in fpg_part.project_category if pd.notna(p)), None),
            "pumps": None if fpg_part.pumps.dropna().empty else int(fpg_part.pumps.dropna().max()),
            "capacity_listed_m3hr": None if fpg_part.capacity_listed_m3hr.dropna().empty
            else float(fpg_part.capacity_listed_m3hr.dropna().max()),
            "capacity_complete": bool(fpg_part.capacity_complete.any()),
        })
        if geo_src is None:
            log["unmapped"].append({"records": list(g.record_id), "reason":
                                    "geocode not found or contradicted the ward named in the source"})
    out = pd.DataFrame(rows).sort_values(["ward", "group_id"]).reset_index(drop=True)
    out.insert(0, "location_id", [f"RG-{i + 1:03d}" for i in range(len(out))])
    out.to_csv(PROC / "locations.csv", index=False, encoding="utf8")
    log["outputs"] = {
        "unique_locations": len(out),
        "by_n_sources": {str(k): int(v) for k, v in out.n_sources.value_counts().sort_index().items()},
        "by_source_combination": {k: int(v) for k, v in out.sources.value_counts().items()},
        "by_precision": {k: int(v) for k, v in out.geocode_precision.value_counts().items()},
    }
    (PROC / "cleaning_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False, default=str),
                                            encoding="utf8")
    print(json.dumps(log, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
