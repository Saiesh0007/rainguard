# Methodology

RainGuard is a **historical hotspot and evidence-based prioritisation system**. It is not a forecasting model. [`data_audit.md`](data_audit.md) explains why no defensible forecast is possible with free public data. This document describes exactly what the code does. Every step is a script in `analysis/` run by `python analysis/run_pipeline.py`.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. Fetch sources, record URL / time / SHA-256 | `fetch_data.py` | `data/raw/`, `data/raw/manifest.json` |
| 2. Verify manual transcriptions against the PDFs | `verify_transcription.py` | `transcription_verification.json` |
| 3. Digitise the ward incident map | `digitize_ward_incidents.py` | `ward_incident_class.csv`, QC image |
| 4. Geocode and quality-check locations | `geocode.py` | `geocoded_locations.csv` |
| 5. Validate, de-duplicate, match across sources | `clean_data.py` | `locations.csv`, `cleaning_log.json` |
| 6. Terrain from the DEM | `terrain.py` | `grid_terrain.csv`, `location_terrain.csv` |
| 7. Rainfall summaries and reliability check | `rainfall.py` | `rainfall_*.csv/json` |
| 8. Ward and location features | `features.py` | `ward_stats.csv`, `location_features.csv` |
| 9. Baselines vs models; terrain test | `evaluate.py` | `evaluation.json` |
| 10. Prioritisation score and sensitivity | `score.py` | `priority_scores.csv`, `score_sensitivity.json` |
| 11. EDA findings and figures | `eda.py` | `eda_findings.json`, `docs/figures/*.png` |
| 12. Package for the web app | `export_app_data.py` | `app/public/data/*.json` |

## 1. Transcription (manual, then verified automatically)

The three official lists are tables inside PDFs (the BMC tables are scanned images), so they were transcribed by hand into `data/transcribed/`:

* `bmc_fpg2026_waterlogging_spots.csv`: 97 rows. Each row records its PDF file and page, the published ward, the legacy ward, and notes on anomalies.
* `fpg2026_ward_section_counts.csv`: the count each ward section *claims*, compared with rows listed.
* `best_annex_ix_2026.csv`: 84 rows (residents' names used as landmarks are redacted).
* `mtp_fpg2026_diversions.csv`: 92 rows, with `is_location = no` for 2 rows that are not places.

**Privacy:** pump-operator and caretaker phone numbers are never transcribed, and a test fails if any 10-digit number appears.

**Verification** (`verify_transcription.py`) fuzzy-matches every transcribed name against the source text: the PDF text layer for BEST and the traffic-police table, and Tesseract OCR in three page-segmentation modes for the scanned BMC pages. Results: BMC 93/97, BEST 83/84, traffic police 92/92 at similarity ≥ 0.8. The 5 remaining rows were checked against the page images by eye (OCR line breaks and wrapped cells).

## 2. Ward incident classes (digitised map)

The BMC map has 7 colour bins. For each ward, three sample points were placed inside the fill (coordinates are in the script). The median colour of a 13×13 pixel patch (ignoring dark label text and pale borders) is matched to the nearest legend swatch by RGB distance. Samples more than 30 units from every swatch are discarded, and ties go to the lower class. **All 24 wards were unanimous.** The output is an *ordinal bin*, not a count.

## 3. Geocoding and quality control

Each record has a curated Nominatim query plus a neighbourhood-level fallback (`data/transcribed/geocode_queries.csv`). Searches are bounded to Greater Mumbai.

* **Ward check:** a result must fall inside the legacy ward that the source names (300 m tolerance for boundary roads), otherwise it is rejected. For traffic-police rows only, a specific-feature hit outside the heading ward is re-assigned to the ward containing it, because those headings are police groupings (2 rows).
* **Precision:** `point` (a specific feature), `street` (somewhere along a road), `area` (neighbourhood only; this always applies to fallback queries, so a station sharing a neighbourhood's name is never mistaken for the spot), or `not_mappable`.
* **Manual review** (`geocode_review.csv`, 49 rows, each with a reason) can only **downgrade** precision, never move a point. A test enforces this.

Result for the 251 merged places: **47 point, 45 street, 144 area-only, 15 not mappable.** Area-only places are drawn as hollow rings. Unmappable places appear only in the list.

## 4. Cleaning and cross-source matching

* Schema checks: required columns, legacy ward codes, non-negative integer pump counts, numeric capacities.
* **Within-source duplicates** (same source, ward and normalised text) are merged: 3 cases.
* **Cross-source matches** (same ward only) are accepted when either:
  * names match (fuzzy token Jaccard ≥ 0.5 with ≥ 2 shared distinctive tokens, or a complete single-token match), or
  * both are geocoded precisely within 250 m and share some name (Jaccard ≥ 0.25).

  A match is refused if explicit road numbers conflict, or if it would merge two different records of the same source (1 such ambiguous case is logged). Generic words (road, marg, junction, north, bound…) are ignored.
* **Match review** (`match_review.csv`) can only reject matches: 2 were rejected, with reasons.
* Nothing is imputed. Missing pump data stays missing.

Result: **251 distinct places**; 235 on one list, 15 on two, and 1 (Worli Naka) on all three.

## 5. Terrain

A 500 m grid (1,841 cells inside BMC wards) gets Copernicus GLO-90 elevations. **TPI** = elevation minus the median of grid cells within 1 km. Each precisely geocoded place gets its TPI percentile *within its own ward*. Area-level places are not assessed.

## 6. Rainfall

* IMD monthly (1901–2021): climatology, June–September share, and an annual trend (Theil–Sen slope with Kendall's τ).
* ERA5 daily (1991–2025): heavy-rain days per year using IMD categories (heavy ≥ 64.5 mm, very heavy ≥ 115.6 mm, extremely heavy ≥ 204.5 mm), and the share of monsoon rain falling on the 10 wettest days.
* **Reliability check:** ERA5 vs IMD monthly totals over the 1991–2021 overlap, and ERA5's value for 26 July 2005 compared with the 944 mm Santacruz record quoted by BMC.

## 7. Analytical method and baselines

### 7a. Ward level: what explains recorded incident burden? (`evaluate.py`)
Target: incident class (1–7) for 24 wards. Models are ordinary least squares on standardised features, with predictions clipped to [1, 7]:

| ID | Features | Role |
|---|---|---|
| B0 | none (training median) | naive baseline |
| B1 | log population (Census 2011) | exposure/reporting baseline |
| B2 | + log ward area | |
| M1 | + median elevation, low-lying share (TPI ≤ −2 m) | terrain model |
| M2 | + log(BMC-listed spots) | adds the official listing |

Protocol: leave-one-ward-out cross-validation; MAE in classes and Spearman ρ; permutation test (1,000 target shuffles). This is cross-sectional and **explanatory**. The ward data has no time dimension, so it cannot be a forecast.

### 7b. Location level: does terrain distinguish listed places? (`evaluate.py`)
Within-ward case-control: if terrain carried no signal, the percentile of listed places among their own ward's grid cells would be uniform (median 0.5). One-sample Wilcoxon test vs 0.5, reported separately for precise and area-only geocodes.

### 7c. Inspection-prioritisation score (`score.py`)
A **rule-based relative ordering**, explicitly *not* a probability:

| Component (0–1) | Definition | Evidence type |
|---|---|---|
| `ward_burden` | (incident class − 1) / 6 | historical, ward-level |
| `corroboration` | (number of official lists naming the place − 1) / 2 | historical |
| `listing_density` | min(other listed records within 1 km, 10) / 10 | historical |
| `low_lying` | 1 − TPI percentile within ward (precise geocodes only) | estimated, **unvalidated** |

Score = 100 × weighted mean of the *available* components. Missing components are skipped, not zero-filled. **Default weights are ⅓, ⅓, ⅓ and 0 for `low_lying`**, because 7b found no significant terrain signal. Civic users can turn it on with a slider labelled "unvalidated".

Tiers by rank: A = top 20%, B = next 30%, C = rest. Places tied at a cut-off go to the higher tier, so A currently holds 73 places.

**Sensitivity:** 2,000 Dirichlet(1,1,1,1) random weightings (seed 20261022) give, per place, the share of draws in which it is in the top 20 and its 10th–90th percentile rank. Each component is also dropped in turn. The app's TypeScript re-implementation is tested to reproduce every Python score, rank and tier.

## 8. How the app presents evidence

Every block in a location panel carries one of five labels: **Observed, Historical, Estimated, Forecast, Unknown** (icon + text + colour, never colour alone). Guidance is cautious. It never says a road is safe, and it cites BMC's own advice (1916 helpline; see a doctor within 24–72 h after wading through floodwater; flooding is worst when heavy rain coincides with high tide).
