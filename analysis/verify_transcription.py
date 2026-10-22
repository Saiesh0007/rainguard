"""Independently check the manual transcriptions against the source PDFs.

* BEST Annexure IX (2026) has a text layer: every transcribed `area_or_road` must be found
  (fuzzy) in the annexure text.
* BMC FPG 2026 ward pages are scanned images: each page is OCR'd with Tesseract and every
  transcribed `location_published` must be found (fuzzy) in the OCR text. OCR misses some
  table cells, so a low score is a prompt for manual review, not proof of an error.
* Row counts are compared with the counts printed in each section header.

Writes data/processed/transcription_verification.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TR = ROOT / "data" / "transcribed"
OUT = ROOT / "data" / "processed" / "transcription_verification.json"
TESSERACT_CANDIDATES = [shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe"]
MATCH_THRESHOLD = 0.8


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def best_window_ratio(needle: str, hay: str) -> float:
    """Highest similarity between `needle` and any equal-length word window of `hay`."""
    n, h = norm(needle).split(), norm(hay).split()
    if not n or not h:
        return 0.0
    k = len(n)
    target = " ".join(n)
    best = 0.0
    for size in {k - 1, k, k + 1} - {0}:
        for i in range(0, max(1, len(h) - size + 1)):
            best = max(best, SequenceMatcher(None, target, " ".join(h[i:i + size])).ratio())
            if best == 1.0:
                return 1.0
    return best


def verify_best() -> dict:
    df = pd.read_csv(TR / "best_annex_ix_2026.csv")
    doc = pymupdf.open(RAW / "best" / "Disaster_Management_Protocol_Booklet_2026.pdf")
    text = " ".join(doc[int(i)].get_text() for i in sorted(df.pdf_page_index.unique()))
    scores = {r.record_id: best_window_ratio(r.area_or_road, text) for r in df.itertuples()}
    low = {k: round(v, 2) for k, v in scores.items() if v < MATCH_THRESHOLD}
    return {"rows": len(df), "matched": len(df) - len(low), "below_threshold": low,
            "max_sr_no": int(df.sr_no.max()), "sr_no_contiguous": sorted(df.sr_no) == list(range(1, len(df) + 1))}


def verify_mtp() -> dict:
    """Traffic-police diversion table (FPG 2026 printed pp.301-311) has a text layer."""
    df = pd.read_csv(TR / "mtp_fpg2026_diversions.csv")
    full = RAW / "bmc_fpg2026_full.pdf"
    if not full.exists():
        return {"rows": len(df), "check": "skipped: run fetch_data.py --full"}
    doc = pymupdf.open(full)
    text = " ".join(doc[int(i)].get_text() for i in sorted(df.pdf_page_index.unique()))
    scores = {r.record_id: best_window_ratio(r.location_published, text) for r in df.itertuples()}
    low = {k: round(v, 2) for k, v in scores.items() if v < MATCH_THRESHOLD}
    return {"rows": len(df), "location_rows": int((df.is_location == "yes").sum()),
            "matched": len(df) - len(low), "below_threshold": low}


def verify_fpg() -> dict:
    df = pd.read_csv(TR / "bmc_fpg2026_waterlogging_spots.csv")
    counts = pd.read_csv(TR / "fpg2026_ward_section_counts.csv")
    tess = next((t for t in TESSERACT_CANDIDATES if t and Path(t).exists()), None)
    result: dict = {"rows": len(df)}
    if tess is None:
        result["ocr"] = "skipped: tesseract not installed"
    else:
        ocr_cache: dict[tuple[str, int], str] = {}
        scores = {}
        for r in df.itertuples():
            key = (r.pdf_file, int(r.pdf_page_index))
            if key not in ocr_cache:
                page = pymupdf.open(RAW / "bmc_fpg2026_ward" / r.pdf_file)[key[1]]
                png = OUT.parent / "_ocr_tmp.png"
                page.get_pixmap(dpi=300).save(png)
                # several page-segmentation modes: table cells survive in different ones
                ocr_cache[key] = "\n".join(
                    subprocess.run([tess, str(png), "-", "--psm", psm], capture_output=True,
                                   text=True, encoding="utf8").stdout for psm in ("4", "6", "11"))
                png.unlink()
            scores[r.record_id] = best_window_ratio(r.location_published, ocr_cache[key])
        low = {k: round(v, 2) for k, v in scores.items() if v < MATCH_THRESHOLD}
        result.update({"matched": len(df) - len(low), "below_threshold_for_manual_review": low,
                       "mean_similarity": round(sum(scores.values()) / len(scores), 3)})
    listed = df.groupby(["pdf_file", "pdf_page_index"]).size()
    result["header_vs_rows"] = [
        {"ward_published": c.ward_published, "header": None if pd.isna(c.section_header_count) else int(c.section_header_count),
         "rows_listed": int(c.rows_listed)}
        for c in counts.itertuples()
        if pd.isna(c.section_header_count) or int(c.section_header_count) != int(c.rows_listed)
    ]
    result["rows_listed_total"] = int(counts.rows_listed.sum())
    result["header_total"] = int(counts.section_header_count.fillna(0).sum())
    assert int(counts.rows_listed.sum()) == len(df), "section counts table disagrees with transcription"
    assert listed.sum() == len(df)
    return result


def main() -> None:
    out = {"best_annex_ix_2026": verify_best(), "bmc_fpg2026": verify_fpg(), "mtp_diversions_2026": verify_mtp()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
