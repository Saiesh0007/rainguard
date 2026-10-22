# Data folder

| Folder | Contents | In git? |
|---|---|---|
| `raw/` | Downloads from `analysis/fetch_data.py` (BMC/BEST PDFs, DataMeet wards, IMD, ERA5, census) plus `manifest.json` (URL, access time, size, SHA-256) | **Only `manifest.json`.** BMC/BEST PDFs are publisher copyright, so re-download them. |
| `transcribed/` | Hand transcriptions of the three official lists, curated geocoding queries, and the two review files (`geocode_review.csv` can only downgrade precision; `match_review.csv` can only reject matches) | Yes |
| `processed/` | All pipeline outputs, including the geocode and elevation caches that make re-runs offline and identical | Yes |

Key processed files:
* `locations.csv`: 251 unique places, sources, geocode precision, pumps, diversions
* `location_features.csv` / `priority_scores.csv`: terrain, neighbours, score components, rank, stability
* `ward_stats.csv`: incident class, population, area, listing counts, terrain summary per legacy ward
* `eda_findings.json`, `evaluation.json`, `score_sensitivity.json`, `rainfall_summary.json`
* `cleaning_log.json`: every merge, rejection, exclusion and re-assignment, with reasons
* `transcription_verification.json`: automatic check of every transcribed row against the PDFs

Re-create everything: `python analysis/fetch_data.py --full && python analysis/run_pipeline.py`.
