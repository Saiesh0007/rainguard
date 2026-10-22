# Limitations and responsible use

RainGuard is a student prototype for HackAMatch 1.0. It is **not** an official BMC service, an emergency-warning system, or a route-safety tool.

## Data
* **Listings, not events.** All three lists name places where authorities *expect* waterlogging. None records when, how deep or how often it happened.
* **The lists disagree.** Only 16 of 251 places appear on more than one list. BMC's 2026 list says wards A, B and G/N have no waterlogging spots, while BEST lists 16 there. None of the lists is complete.
* **Absence ≠ safety.** A road missing from every list may still flood.
* **The BEST list is static.** It is virtually identical across the 2023-24, 2024-25 and 2026 editions, so it may include fixed spots and miss new ones.
* **The ward incident map** is binned (7 classes), its period is ambiguous (2016–2023 in the legend vs 2016–2025 in the caption), it counts complaints, and it largely follows population (ρ = 0.835).
* **Ward boundaries** are the 24 legacy wards. BMC has since split P/North and K/East.
* **Census population** is from 2011.

## Location accuracy
* 144 of 251 places could only be placed at neighbourhood level, and 15 could not be placed at all. Even "exact" points are geocoding estimates, typically accurate to tens of metres.
* Name matching across lists may miss the same place written very differently, so corroboration may be understated.

## Rainfall
* There is no open neighbourhood-scale rainfall. BMC's 120-gauge network is behind authentication.
* ERA5 is one 25 km cell for the whole city and under-estimated 26 July 2005 by about 93%.
* The live forecast is a third-party global model for one point and can miss Mumbai's most intense storms.
* No tide data is integrated, although BMC notes flooding is worst when heavy rain meets high tide. No dated tide series is openly available (data audit §2), and BMC's own counts show rain > 100 mm and tide > 4.5 m on the same day at most 5 times a year in 2016–2025, too few to validate.
* IMD's daily grid is also a 25 km cell average. The heavy-rain outlook is built on it, so it shares that limit.

## Method
* The priority score is a transparent rule, not a validated model. Its top places change noticeably with the weights (Evaluation §4).
* Terrain (90 m DSM) showed no significant signal and is off by default.
* Ward-level evaluation has only 24 observations.
* The **heavy-rain outlook predicts rain, not waterlogging**, and only city-wide. It is tested on years the model never saw, but a heavy-rain day is the trigger, not the outcome. It cannot change the inspection plan between places.
* The **forecast track record** covers only the 2024 and 2025 monsoons (the archive starts in 2024), so its shares rest on small counts.
* **Diagnosis labels** are read from the lists, not verified on the ground. `list_gap` says a place is missing from BMC's list; it does not prove BMC is wrong, since the lists serve different purposes. A blank pump cell may mean a pump recorded elsewhere.
* The **weekly plan** inherits the score's sensitivity to weights; each place shows how often it stays in the plan. The ward cap (default 3) is a planning choice, not a data fact.
* The **population-adjusted** ward factor rests on a 24-ward fit with a binned target.

## Possible harms and mitigations
| Risk | Mitigation |
|---|---|
| A citizen reads "not listed" as "safe" | Stated in the panel, search empty state and legend |
| Over-trust in a polished map | Evidence labels on every block; precision shown; approximate places drawn as hollow rings |
| Ranking used as an automated order | "Decision support, not an official directive"; adjustable weights; stability shown; labels say what to *check*, never what to conclude |
| Heavy-rain outlook read as a flood warning | Labelled "rain outlook, not a waterlogging forecast"; official IMD/BMC alerts linked; track record shows misses and false alarms |
| Stigmatising neighbourhoods | Ward history labelled as following population; no per-capita "danger" ranking |
| Exposure of personal data | Phone numbers excluded; residents' names redacted; tested automatically |

## What would improve confidence
1. BMC's dated, geolocated waterlogging complaints (CCS) for 3+ monsoons, or an official dated record of city disruption days (none found, data audit §2). This would enable chronological validation (precision/recall of a rain + tide model against a rain-threshold baseline).
2. Open access to BMC's 15-minute automatic rain-gauge and tide data.
3. A higher-resolution terrain model (LiDAR DTM) and storm-drain network data.
4. A single, versioned, machine-readable official hotspot list with coordinates and a "resolved" status.
