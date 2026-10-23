# Stage 2b — harmonized market-definition rerun (bounded counts)

Legacy-injectable rows after corrections (bare 'INJECTION' no longer counts as evidence; premixed/dual-chamber containers
are their own class; prefilled devices are liquids): {'PROVISIONAL': 4226, 'UNRESOLVED': 614, 'CONFIRMED': 3124}; basis: {'strength': 4184, 'REVIEW': 379, 'trade-name premix marker': 1075, 'specific NDC dosage form': 2049, 'no evidence; strength unclassifiable': 231, 'mixed NDC forms under application': 4, 'verified override (injectable suspension, ingredient-level, reviewed)': 23, 'verified override (liquid in vial)': 19}

Episodes with a market: 1901; own product unambiguous: 1829 ({'CONFIRMED': 1616, 'PROVISIONAL': 213}); ambiguous (alternatives reported, none selected): 72

## Bounds (unambiguous episodes)
| | lower (confirmed) | point (conf.+prov.) | upper (+compatible unresolved) | original unharmonized |
|---|---|---|---|---|
| median | 6 | 10 | 10 | 11 |

Bound width (upper − lower): {'0': 1147, '3–5': 144, '6+': 410, '1–2': 128}
Episodes whose single-applicant status differs between lower and upper bound: 116 of 1829
Single-applicant at point estimate: 197; at lower: 304; at upper: 188

## Named test drugs (one representative episode each; full detail in tail_validation.csv)
| Drug | old market | harmonized market | orig | lower | point | upper | own tier |
|---|---|---|---|---|---|---|---|
| MIDAZOLAM | MIDAZOLAM HYDROCHLORIDE | INJECTABLE;INJECTIO | MIDAZOLAM HYDROCHLORIDE | parenteral | injectable, ready-to- | 17 | 5 | 17 | 17 | CONFIRMED |
| CEFEPIME | CEFEPIME HYDROCHLORIDE | INJECTABLE;INJECTION | CEFEPIME HYDROCHLORIDE | parenteral | injectable, powder/for | 7 | 2 | 5 | 5 | CONFIRMED |
| DEXMEDETOMIDINE | DEXMEDETOMIDINE HYDROCHLORIDE | INJECTABLE;IN | DEXMEDETOMIDINE HYDROCHLORIDE | parenteral | injectable, rea | 18 | 11 | 19 | 19 | PROVISIONAL |
| TACROLIMUS | TACROLIMUS | CAPSULE;ORAL | TACROLIMUS | oral | capsule, immediate release | IR/NA | 9 | 9 | 9 | 9 | CONFIRMED |
| LISDEXAMFETAMINE | LISDEXAMFETAMINE DIMESYLATE | CAPSULE;ORAL | LISDEXAMFETAMINE DIMESYLATE | oral | capsule, immediate rele | 1 | 1 | 1 | 1 | CONFIRMED |

## Historical credibility check: bounds for episodes whose product came from the excluded (discontinued) file vs current file
- current: n=1399, median lower 5, point 10, upper 10
- excluded: n=430, median lower 6, point 10, upper 10

Files: market_definition_changes.csv, market_bounds.csv, tail_validation.csv, legacy_exception_audit.csv, provenance.log
