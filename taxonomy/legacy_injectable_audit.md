# Legacy-injectable error and coverage audit

Map finalised: reviewer decisions {'ACCEPT': 202, 'ACCEPT_CONDITIONAL': 11, 'REVISE->ACCEPT': 11, 'REVIEW': 80} across 304 labels; oral liquids split into distinct subtypes.

Legacy-label Orange Book product rows: 7964 (4978 applications). Tier assignment:
{'PROVISIONAL': 4273, 'REVIEW': 463, 'HIGH': 3228}

## Validation of the strength rule where NDC-form evidence exists (agreement / rows, by true class)
| True class (NDC form) | Strength rule agrees |
|---|---|
| emulsion | 0/22 (0.0%) |
| powder | 636/636 (100.0%) |
| solution | 1988/2034 (97.7%) |
| suspension | 0/45 (0.0%) |

False-powder (strength says per-container, NDC says liquid): 46/682 (6.7%)
False-solution (strength says concentration, NDC says powder): 0/2055 (0.0%)

## Exception list (113 rows) by error type — see legacy_injectable_exceptions.csv
- liquid in container expressed per vial/syringe (premixed bag, multi-dose vial, prefilled syringe): 46
- suspension expressed per mL (class granularity): 45
- emulsion expressed per mL (class granularity, not a powder/solution error): 22

## Coverage of the 806 legacy-label shortage episodes
| Outcome | HIGH only | HIGH + PROVISIONAL |
|---|---|---|
| resolved: emulsion | 16 | 16 |
| resolved: powder | 99 | 121 |
| resolved: solution | 589 | 648 |
| resolved: suspension | 16 | 16 |
| unresolved | 86 | 5 |

## Applicant-market assignment changes (legacy rows that would move from the undifferentiated legacy market into a formulation sub-market)
- HIGH only: 3228/7964 rows (40.5%)
- HIGH + PROVISIONAL: 7501/7964 rows (94.2%)
Rows not moved stay in the undifferentiated legacy market (REVIEW stratum), never merged into solution or powder.

## Reading
- HIGH-only is the proposed primary specification; HIGH+PROVISIONAL the sensitivity specification.
- Per-container strength is not conclusive evidence of a powder: the exception list shows the liquid-in-container cases.
- A shortage episode is 'resolved' only when every classified row of its own application agrees on one formulation.
