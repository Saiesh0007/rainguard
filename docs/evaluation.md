# Evaluation

All numbers below come from `data/processed/evaluation.json` and `score_sensitivity.json`, produced by `python analysis/run_pipeline.py` on 22 October 2026. Nothing here is estimated by hand.

## What could not be evaluated, and why

There are **no dated, located waterlogging observations** in any free public source (see [`data_audit.md`](data_audit.md)). So:

* **No forecast is made**, and no forecast skill, precision or recall is reported.
* The **prioritisation score has no predictive accuracy figure**. There is no outcome to test it against. We evaluate its *behaviour* (sensitivity, ablation) and the *evidence for each input* instead.

## 1. Ward level: explaining recorded incident burden

Leave-one-ward-out cross-validation, n = 24 wards; target = incident class 1–7. Class counts: 2 → 1 ward, 3 → 4, 4 → 4, 5 → 3, 6 → 5, 7 → 7.

| Model | Features | LOO MAE (classes) | LOO Spearman ρ | Permutation p |
|---|---|---|---|---|
| B0 baseline | training median | **1.92** | — (constant) | — |
| B1 baseline | log population | **0.73** | 0.82 | 0.001 |
| B2 | + log area | 0.75 | 0.81 | 0.001 |
| M1 | + median elevation, low-lying share | 0.72 | 0.82 | 0.001 |
| M2 | + log(BMC-listed spots) | 0.75 | 0.81 | 0.001 |

Spearman correlation between ward population and incident class: **ρ = 0.835** (p < 0.001). Between BMC-listed spot count and class: ρ = 0.595 (p = 0.002).

**Interpretation**
* Population alone cuts the error by 62% compared with the median baseline. It is very unlikely to be chance (permutation p = 0.001, the smallest attainable with 1,000 shuffles).
* Adding terrain improves MAE by 0.008 classes, which is negligible with 24 wards. Adding listed-spot counts makes it slightly worse. **No model beats the population baseline in a meaningful way.**
* Recorded incidents therefore mostly follow *where people live and report*. The ward map is shown in the app as historical context, explicitly labelled "mostly follows population", and not as a hazard map.
* Caveats: n = 24; an ordinal target treated as numeric; population from 2011; and an ambiguous incident period.

## 2. Location level: is terrain a useful signal?

Within-ward case-control: percentile of each listed place's relative elevation (TPI) and elevation among all 500 m grid cells in its own ward. Under "no signal", the median is 0.5.

| Geocode precision | n | TPI percentile median | Wilcoxon p (TPI) | Elevation percentile median | Wilcoxon p (elev.) |
|---|---|---|---|---|---|
| point / street | 92 | 0.443 | 0.174 | 0.509 | 0.072 |
| area only | 144 | 0.536 | 0.406 | 0.490 | 0.164 |

**Interpretation:** precisely located places lean slightly lower than their surroundings (57% are below the ward median TPI), but **the difference is not statistically significant**. A 90 m surface model with building heights and metre-scale error is probably too coarse for street-level drainage problems. **Decision:** the terrain component's default weight in the priority score is 0. It is offered only as an optional, clearly labelled "unvalidated" factor.

## 3. Rainfall data reliability

| Check | Result |
|---|---|
| ERA5 vs IMD monthly totals, 1991–2021 (372 months) | Pearson r = 0.94 (all months), 0.805 (June–Sept months) |
| ERA5 annual total / IMD annual total | 0.80 (ERA5 is about 20% drier) |
| ERA5 on 26 July 2005 vs BMC-quoted Santacruz record | **69.6 mm vs 944 mm** |
| ERA5 cells covering Mumbai's two reference points | 1 (Santacruz and Colaba series are identical) |

ERA5 captures the *seasonal* pattern well, but it misses localised extremes by an order of magnitude and cannot resolve neighbourhoods. The live forecast in the app comes from the same family of global models, so it is shown only as third-party city-level context, with this caveat.

## 4. Prioritisation score: behaviour and robustness

Default weights: ward burden ⅓, corroboration ⅓, listing density ⅓, terrain 0. 251 places.

**Random weightings** (2,000 Dirichlet(1,1,1,1) draws over all four components):
* Spearman correlation of the full ordering with the default: median **0.778**, 5th percentile 0.527.
* Top-20 set overlap (Jaccard, tie-aware): median **0.55**, 5th percentile 0.14.
* Only **4 places** are in the top 20 in at least 80% of draws.

**Drop one component** (remaining weights equal):

| Dropped | Ordering correlation with default | Top-20 Jaccard |
|---|---|---|
| ward burden | 0.676 | 0.14 |
| corroboration | 0.877 | 0.50 |
| low-lying (already 0) | 1.000 | 1.00 |
| listing density | 0.484 | 0.14 |

**Interpretation:** the broad ordering is fairly stable, but *which* places make the very top depends strongly on how much weight goes to ward history versus local listing density. That is a value judgement, not a data fact. The civic view therefore shows live weight sliders, each place's top-20 frequency and its rank range, and labels tiers as "a starting point for judgement".

## 5. Software tests (executed 22 Oct 2026)

| Suite | Command | Result |
|---|---|---|
| Python pipeline (unit + output integrity) | `python -m pytest -q` | **21 passed** |
| Frontend (score parity with Python, forecast states, data integrity, UI states) | `cd app && npm test` | **35 passed** |
| Lint | `cd app && npm run lint` | no errors |
| Type-check + production build | `cd app && npm run build` | success |
| Full pipeline from cached inputs | `python analysis/run_pipeline.py` | completes, exit 0 |

Manual checks: phone (390 px), tablet (768 px) and desktop (1440 px) layouts with no horizontal scroll; light and dark themes; map loading, map error, forecast unavailable, cached/stale forecast, empty search and data-load error states. The UI states are also covered by the automated tests.
