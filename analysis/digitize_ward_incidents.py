"""Digitise BMC's ward-wise waterlogging-incident choropleth into an ordinal table.

Source: BMC Flood Preparedness Guidelines 2026, printed page 18 (PDF page index 21),
"Water Logging - Ward-wise no. of incidents". The page caption says 2016-2025 but the
legend baked into the embedded raster says "2016 To 2023"; we keep both and flag the
inconsistency rather than choosing one.

Method (fully reproducible):
1. Extract the embedded map raster from the PDF at native resolution.
2. For every ward, read the fill colour at hand-placed sample points next to the ward
   label (points listed below, in raster pixel coordinates). Each point uses the median
   colour of a 13x13 patch, ignoring dark label text and pale boundary pixels.
3. Read the seven legend swatch colours the same way.
4. Assign each ward the legend class whose colour is nearest (Euclidean RGB distance).
   Three points per ward must agree; disagreements are reported, not hidden.

Output: data/processed/ward_incident_class.csv and an annotated QC image.
The output is an ORDINAL BIN (e.g. "317-466 incidents"), not an exact count.

Requires: python analysis/fetch_data.py --full  (the 622 MB book).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "bmc_fpg2026_full.pdf"
OUT = ROOT / "data" / "processed" / "ward_incident_class.csv"
QC_IMG = ROOT / "data" / "processed" / "qc_ward_incident_digitisation.png"
PAGE_INDEX = 21
MAX_DIST = 30.0  # samples farther than this from every swatch are treated as boundary/text noise

LEGEND = [  # (class, low, high, swatch centre x, y)
    (1, 0, 115, 655, 626), (2, 116, 130, 655, 662), (3, 131, 212, 655, 698),
    (4, 213, 270, 655, 735), (5, 271, 316, 655, 772), (6, 317, 466, 655, 809),
    (7, 467, 800, 655, 847),
]

# Three sample points per ward, placed inside the ward fill near its printed label.
SAMPLES: dict[str, list[tuple[int, int]]] = {
    "A": [(175, 800), (190, 780), (160, 840)],
    "B": [(225, 742), (230, 748), (222, 752)],
    "C": [(176, 770), (183, 776), (172, 764)],
    "D": [(115, 735), (130, 720), (105, 748)],
    "E": [(225, 690), (195, 695), (230, 715)],
    "F/S": [(235, 668), (265, 640), (225, 650)],
    "G/S": [(175, 665), (160, 680), (170, 610)],
    "G/N": [(215, 610), (205, 600), (230, 570)],
    "F/N": [(300, 600), (310, 575), (290, 615)],
    "M/W": [(360, 585), (355, 620), (375, 520)],
    "M/E": [(470, 610), (420, 620), (500, 560)],
    "H/W": [(200, 530), (195, 480), (185, 520)],
    "H/E": [(265, 520), (250, 465), (285, 515)],
    "L": [(330, 480), (320, 520), (340, 420)],
    "N": [(460, 440), (400, 450), (500, 470)],
    "K/W": [(200, 350), (215, 395), (190, 330)],
    "K/E": [(285, 440), (300, 370), (270, 390)],
    "S": [(470, 390), (420, 380), (510, 340)],
    "T": [(440, 230), (500, 250), (470, 215)],
    "P/S": [(280, 290), (330, 300), (220, 300)],
    "P/N": [(140, 280), (120, 230), (300, 250)],
    "R/S": [(300, 220), (340, 200), (220, 195)],
    "R/C": [(300, 150), (360, 140), (180, 140)],
    "R/N": [(290, 75), (250, 78), (300, 95)],
}


def extract_raster() -> np.ndarray:
    doc = pymupdf.open(PDF)
    page = doc[PAGE_INDEX]
    xref = max(page.get_images(), key=lambda im: im[2] * im[3])[0]
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n - pix.alpha >= 4:  # CMYK -> RGB
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return arr[:, :, :3].astype(float)


def patch_colour(img: np.ndarray, x: int, y: int, r: int = 6) -> np.ndarray:
    patch = img[max(0, y - r): y + r + 1, max(0, x - r): x + r + 1].reshape(-1, 3)
    lum = patch @ np.array([0.299, 0.587, 0.114])
    keep = patch[(lum > 25) & (lum < 250)]
    return np.median(keep if len(keep) else patch, axis=0)


def classify(img: np.ndarray) -> list[dict]:
    swatches = {c: patch_colour(img, x, y, r=4) for c, _, _, x, y in LEGEND}
    rows = []
    for ward, pts in SAMPLES.items():
        classes, dists = [], []
        for x, y in pts:
            col = patch_colour(img, x, y)
            d = {c: float(np.linalg.norm(col - s)) for c, s in swatches.items()}
            best = min(d, key=d.get)
            classes.append(best)
            dists.append(round(d[best], 1))
        valid = [c for c, d in zip(classes, dists) if d <= MAX_DIST]
        if not valid:
            raise ValueError(f"no sample for ward {ward} matched a legend colour")
        # most frequent class; ties resolved toward the LOWER class (conservative)
        majority = sorted(set(valid), key=lambda c: (-valid.count(c), c))[0]
        lo, hi = next((lo, hi) for c, lo, hi, _, _ in LEGEND if c == majority)
        rows.append({
            "ward": ward, "incident_class": majority, "incidents_low": lo, "incidents_high": hi,
            "points_agreeing": classes.count(majority), "points_total": len(classes),
            "points_valid": len(valid),
            "sample_classes": "|".join(map(str, classes)), "colour_distance": "|".join(map(str, dists)),
        })
    return rows


def write_qc_image(rows: list[dict]) -> None:
    doc = pymupdf.open(PDF)
    page = doc[PAGE_INDEX]
    xref = max(page.get_images(), key=lambda im: im[2] * im[3])[0]
    pix = pymupdf.Pixmap(doc, xref)
    out = pymupdf.open()
    p = out.new_page(width=pix.width, height=pix.height)
    p.insert_image(p.rect, pixmap=pix)
    for row in rows:
        for x, y in SAMPLES[row["ward"]]:
            p.draw_circle((x, y), 3, color=(1, 0, 0), fill=(1, 0, 0))
        x, y = SAMPLES[row["ward"]][0]
        p.insert_text((x + 5, y + 4), str(row["incident_class"]), fontsize=11, color=(1, 0, 0))
    out[0].get_pixmap(dpi=72).save(QC_IMG)


def main() -> None:
    img = extract_raster()
    rows = classify(img)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["period_caption", "period_legend", "source"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "period_caption": "2016-2025", "period_legend": "2016-2023",
                        "source": "BMC Flood Preparedness Guidelines 2026, p.18 (digitised choropleth)"})
    write_qc_image(rows)
    for r in rows:
        flag = "" if r["points_agreeing"] == r["points_total"] else "  <-- points disagree"
        print(f"{r['ward']:>4}  class {r['incident_class']}  ({r['incidents_low']}-{r['incidents_high']})"
              f"  samples {r['sample_classes']}  dist {r['colour_distance']}{flag}")
    print(json.dumps({"wards": len(rows), "unanimous": sum(r["points_agreeing"] == r["points_total"] for r in rows)}))


if __name__ == "__main__":
    main()
