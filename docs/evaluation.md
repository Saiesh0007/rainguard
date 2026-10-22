# Evaluation

All numbers below come from `data/processed/evaluation.json`, `score_sensitivity.json`, `allocation.json`, `diagnosis_summary.json` and `outlook.json`, produced by `python analysis/run_pipeline.py` (last run 23 October 2026). Nothing here is estimated by hand.

## What could not be evaluated, and why

There are **no dated, located waterlogging observations** in any free public source (see [`data_audit.md`](data_audit.md)). So:

* **No waterlogging forecast is made**, at any location, and no waterlogging precision or recall is reported.
* What *is* forecast and tested chronologically is a **city-wide heavy-rain outlook** (§5): the trigger, not the outcome.
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

Default weights: ward burden ⅓, corroboration ⅓, listing density ⅓, terrain 0, population-adjusted ward history 0. 251 places.

**Random weightings** (2,000 Dirichlet(1,1,1,1,1) draws over all five components):
* Spearman correlation of the full ordering with the default: median **0.726**, 5th percentile 0.472.
* Top-20 set overlap (Jaccard, tie-aware): median **0.46**, 5th percentile 0.17.
* **11 places** are in the top 20 in at least 80% of draws.

These differ from the 22 October figures (0.778, 0.55 and 4 places) only because the draws now span five components instead of four.

**Drop one component** (remaining three of the original four equal; population-adjusted factor off):

| Dropped | Ordering correlation with default | Top-20 Jaccard |
|---|---|---|
| ward burden | 0.676 | 0.14 |
| corroboration | 0.877 | 0.50 |
| low-lying (already 0) | 1.000 | 1.00 |
| listing density | 0.484 | 0.14 |

**Interpretation:** the broad ordering is fairly stable, but *which* places make the very top depends strongly on how much weight goes to ward history versus local listing density. That is a value judgement, not a data fact. The civic view therefore shows live weight sliders, each place's top-20 frequency and its rank range, and labels tiers as "a starting point for judgement".

**Population-adjusted alternative** (swap ward burden for incidents beyond what population explains): ordering correlation with the default **0.832**, top-20 Jaccard **0.65**. Both views agree on most of the top, but not all of it; the Plan tab shows either one in a click.

## 5. Heavy-rain outlook: chronological test

Target: tomorrow is a heavy-rain day (IMD gridded ≥ 64.5 mm in either Mumbai cell), June–September. Made at 08:30 IST from the 24 h just measured. **This is a rain outlook, not a waterlogging forecast.**

| Block | Years | Days | Heavy share |
|---|---|---|---|
| Train | 1971–2008 | 4,636 | 9.7% |
| Validate | 2009–2016 | 976 | 10.6% |
| Test (used once) | 2017–2025 | 1,098 | 13.2% |

**Validation** (model choice): Brier skill vs climatology B1 persistence 0.081, M1 0.150, **M2 0.160** (chosen).

**Test, 2017–2025** (models refitted on 1971–2016):

| Model | Brier | Skill vs climatology (95% CI, resampled years) | ROC AUC |
|---|---|---|---|
| B0 climatology (month) | 0.1122 | 0 | 0.65 |
| B1 persistence | 0.0992 | 0.116 (0.078 to 0.160) | 0.69 |
| M1 logistic: today's rain | 0.0882 | 0.214 (0.190 to 0.239) | 0.85 |
| **M2 logistic: + 3-day rain + month** (chosen) | **0.0875** | **0.220 (0.201 to 0.243)** | **0.85** |

**Interpretation**
* Both logistic models beat both baselines on years they never saw, and the interval excludes zero. The outlook adds real, if modest, skill.
* M2's 3-day-rain coefficient is about 0.04, so it adds almost nothing over M1: the signal is today's rain plus the month. Persistence is the finding: after a heavy-rain day the next is heavy **43%** of the time, against **6%** otherwise (1971–2016, 557 heavy days; Insights F6).
* Reliability on test years is reasonable at the top: outlooks of 50–100% came true 57% of the time (42 days). It is less good in the middle: outlooks of 30–50% averaged 39% but came true 46% of the time, and outlooks of 5–10% averaged 7% but came true 3% of the time.
* Test years were wetter (13.2% heavy days, against 9.7% in training), which the month baseline does not adapt to.

**Live forecast track record** (Open-Meteo day-ahead forecasts vs IMD, June–September 2024 and 2025, 244 days, 33 heavy):

| Day-ahead forecast | Days | Heavy-rain days that followed |
|---|---|---|
| under 15.6 mm | 128 | 1 (1%) |
| 15.6–35 mm | 80 | 15 (19%) |
| 35–64.5 mm | 28 | 12 (43%) |
| 64.5 mm or more | 8 | 5 (63%) |

A forecast of ≥ 64.5 mm caught only **5 of 33** heavy days (15%), and 3 of its 8 heavy calls were false alarms. The forecast amount is informative, but its "heavy" call is far too rare; the app therefore quotes the band frequencies rather than the forecast's own category. Two seasons only.

## 6. Diagnosis labels and weekly plan

Labels (251 places; a place can carry several): no pump recorded 42 · missing from BMC's list 155 · named by 2+ lists 16 · traffic diversion 89 · exact spot unknown 159 · no label 7. They are counts of rule matches, not validated findings.

Weekly plan (K = 20, at most 3 per ward): the plan covers **12 wards**, against 5 for an uncapped top 20. Across the 2,000 random weightings, the plan's median Jaccard overlap with the default plan is **0.33** (5th percentile 0.21), and only **3 places** stay in at least 80% of the time. The cap makes the plan fairer across wards but more weight-sensitive. Each planned place therefore shows its plan frequency, and the labels, which are weight-free, carry the "what to do".

## 7. Software tests (executed 23 Oct 2026)

| Suite | Command | Result |
|---|---|---|
| Python pipeline (unit + output integrity, outlook leakage and date checks) | `python -m pytest -q` | **31 passed** |
| Frontend (score and plan parity with Python, labels, forecast states, data integrity, UI states) | `cd app && npm test` | **41 passed** |
| Lint | `cd app && npm run lint` | no errors |
| Type-check + production build | `cd app && npm run build` | success |
| Full pipeline from cached inputs | `python analysis/run_pipeline.py` | completes, exit 0 |

Manual checks (22 Oct 2026, before the Plan and outlook additions; not repeated on 23 Oct): phone (390 px), tablet (768 px) and desktop (1440 px) layouts with no horizontal scroll; light and dark themes; map loading, map error, forecast unavailable, cached/stale forecast, empty search and data-load error states. The UI states are also covered by the automated tests.
