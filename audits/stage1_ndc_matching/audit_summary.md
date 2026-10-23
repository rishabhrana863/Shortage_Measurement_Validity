# Stage 1 join audit — technical feasibility

Episodes: 2042 | drugs (generic names): 298 | posted before first archive snapshot: 791

Scope: this run tests whether the join *works*. Predictor values derived from current-dated files are not
historically validated (see "basis" below) and must not be reported as predictors until dated snapshots are used.

## Coverage
| Level | NDC Directory match | Orange Book application match |
|---|---|---|
| Episode | 1534/2042 (75.1%) | 1486/2042 (72.8%) |
| Drug (any NDC matched) | 257/298 | 246/298 |
| Matched & marketed on posting date | 1318/1534 (85.9%) | — |
| Matched with historical status known (snapshot within 90 d of posting) | 0/1534 (0.0%) | — |

## How matches were made (segment configuration)
{'canon:4-4': 621, 'canon:5-4': 66, 'canon:5-3': 842, 'leftpad:5-3': 5}

## Matching diagnostics (uncertain_matches.csv)
{'missing_historical_marketing_status': 1534, 'unmatched_ndc': 508, 'unmatched_application': 48, 'name_conflict': 17}

## NDC match by posting year
| Year | Matched |
|---|---|
| 2018 | 332/465 (71.4%) |
| 2019 | 226/326 (69.3%) |
| 2020 | 294/404 (72.8%) |
| 2021 | 154/210 (73.3%) |
| 2022 | 220/275 (80.0%) |
| 2023 | 308/362 (85.1%) |

## NDC match by outcome
| Outcome | Matched |
|---|---|
| resolved | 638/850 (75.1%) |
| right-censored | 896/1192 (75.2%) |

## NDC match by pre-archive posting
| Posted before 2019-12-29 | Matched |
|---|---|
| 0 | 976/1251 (78.0%) |
| 1 | 558/791 (70.5%) |

## Unmatched-episode profile (n=508)
- by year: {2018: 133, 2019: 100, 2020: 110, 2021: 56, 2022: 55, 2023: 54}
- by outcome: {'right-censored': 296, 'resolved': 212}
- posted before first archive: 233
- top reasons: [('Other', 170), ('Unknown', 145), ('Demand increase for the drug', 80), ('Discontinuation of the manufacture of the drug', 31), ('Shortage of an active ingredient', 21), ('Requirements related to complying with good manufacturing practices', 19), ('Delay in shipping of the drug', 10), ('Regulatory delay', 5)]
- top therapeutic categories: [('Psychiatry', 80), ('Pediatric', 74), ('Gastroenterology', 68), ('Anesthesia', 60), ('Cardiovascular', 54), ('Other', 45), ('Ophthalmology', 43), ('Anti-Infective', 41)]

## Supplier-concentration proxies, matched episodes
Labelers with a product marketed on the posting date (NDC Directory market: substance/form/route/strength):
{0: 52, 1: 395, 2: 244, 3: 134, 4: 97, 5: 108, 6: 73, 7: 60, 8: 36, 9: 77, 10: 42, 11: 48, 12: 29, 13: 6, 14: 19, 15: 11, 16: 16, 17: 9, 18: 15, 19: 10, 20: 14, 36: 2, 176: 1, 216: 6, 230: 11, 261: 2, 268: 1, 292: 12, 320: 4}
Basis of that count: {'current_file': 1534}  ("current_file" = inferred from current marketing dates, not historical evidence)

Applicants approved on/before posting (Orange Book) — an *approval* count, not participation:
{0: 16, 1: 255, 2: 76, 3: 53, 4: 86, 5: 132, 6: 56, 7: 74, 8: 57, 9: 42, 10: 38, 11: 62, 12: 78, 13: 67, 14: 37, 15: 25, 16: 96, 17: 11, 18: 40, 19: 1, 20: 83, 21: 8, 22: 4, 23: 36, 24: 17, 25: 20, 26: 6, 33: 10}

## Caveats
- Labeler/applicant counts are market-participation / supplier-concentration proxies, not independent
  manufacturers: contract manufacturing and repackaging inflate them.
- Approval date says when a product was approved, not whether its applicant was supplying the market at posting.
- The current NDC Directory omits products past their marketing end date, so current-file participation
  counts are biased toward survivors; dated snapshots are required before any count is called a predictor.
- Episodes posted before the first archive snapshot were observed retrospectively and need separate treatment
  (selection into the archive and timing of first observation), not ordinary delayed entry.
