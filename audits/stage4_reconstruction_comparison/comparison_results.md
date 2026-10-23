# Reconstruction comparison — results (revised spec)

Drugs: 298. R2-eligible (posting after archive start, entry bracketed): 184. Of these, exit AMBIGUOUS under the
common rule (some NDCs resolved, others not): 11 — retained as a separate category. **Common comparison set: 173 drugs,
51 resolved (events), 113 ongoing, 9 disappeared (censored at last sight).**

## Table 3a — entry-identifiable cohort and how the analytical subset is obtained
| Status under the shared exit rule | Drugs | Treatment |
|---|---|---|
| Resolved (every observed NDC carries a Resolved mark) | 51 | survival event |
| Ongoing at last snapshot | 113 | right-censored |
| Disappeared without a Resolved mark | 9 | censored at last verified observation |
| Ambiguous exit (some NDCs resolved, others not) | 11 | separate unresolved category, excluded from survival summaries |
| **Total entry-identifiable** | **184** | |
(The 31 ambiguous cases in Table 4 are counted among all 146 drugs with any resolved NDC — a different denominator from the 11 here.)

## Table 3b — same 173 drugs, same exit rule, three onset definitions
| Rule | Spells | Events | KM median | S(110) | S(180) | S(365) | >1 y observed |
|---|---|---|---|---|---|---|---|
| R1 posting-anchored (common set) | 173 | 51 | not reached | 0.97 | 0.925 | 0.823 | 0.607 |
| R2 archive-observed, earliest plausible onset | 173 | 51 | not reached | 0.988 | 0.97 | 0.84 | 0.578 |
| R2 archive-observed, latest plausible onset | 173 | 51 | 916 | 0.933 | 0.905 | 0.789 | 0.468 |

Paired difference R1 − R2(latest onset): median 37, IQR 16–118, range 0–1450 days. R1 − R2(earliest onset): median -27, IQR -66–-8, range -295–1436 days.
Latest-onset bound capped at the resolution date (spell posted and resolved inside one archive gap): 3 drugs.
Entry bracket width in the common set: median 71, IQR 37–184, range 4–308 days.
Drugs where R1 onset precedes R2 earliest-plausible onset by >365 days (entry-reuse suspects): 7.

## Table 4 — resolution status: original per-NDC coding vs the common drug-level rule (all 298 drugs)
- orig: any NDC resolved → common rule: AMBIGUOUS: 31
- orig: any NDC resolved → common rule: RESOLVED: 115
- orig: none resolved → common rule: DISAPPEARED: 15
- orig: none resolved → common rule: ONGOING: 137

## R0 pseudoreplication (same 173 drugs)
- NDC rows: 1037 vs drugs: 173; rows per drug median 3, max 60
- Multi-NDC drugs whose NDC rows all share one identical (duration, outcome): 88/129
- R0 NDC-level: 1037 'spells', 224 'events', KM median not reached, S(365) 0.883
- R1 drug-level: 173 spells, 51 events, KM median not reached, S(365) 0.823

## R3 linkage coverage (common set)
{'no ASHP link': 110, 'PROBABLE': 30, 'CONFIRMED': 23, 'AMBIGUOUS': 10}; CONFIRMED links with an FDA-resolved event: 8. R3 is reported as linkage coverage; no population KM is drawn from the confirmed subset.

## Rank stability — top-20 persistence
- DEFINITE (top-20 under R1, R2-earliest and R2-latest): 16
- POSSIBLE (top-20 under some onset definitions): 8
- UNRANKABLE (ambiguous exit): 11
- Spearman, R1 vs R2-latest: 0.825; R1 vs R2-earliest: 0.817
- Candidate universe: the 173 rankable drugs; union of the three top-20 lists = 24 drugs = DEFINITE + POSSIBLE. The 11 ambiguous-exit drugs are outside the universe (UNRANKABLE).
- Drugs leaving the top-20 under archive-observed onset (own duration falls by >365 d): ['Atropine Sulfate Injection', 'Dexmedetomidine Hydrochlorid', 'Sodium Chloride 23.4% Inject', 'Sulfasalazine Tablet']
- Drugs entering the top-20 under archive-observed onset: ['Azacitidine for Injection', 'Rifampin Injection', 'Trimethobenzamide Hydrochlor', 'Valproate Sodium Injection'] — relative rank changes only: their own R1 vs R2-latest differences are [30, 18, 30, 29] days.
- All drugs with R1 − R2 > 365 d are ONGOING: their values are elapsed observation times, not completed durations.
- Sole-source share (Orange Book point estimate ≤1 applicant) of the R1 top-20: 4/20; of the R2-latest top-20: 3/20

Files: drug_level_records.csv, paired_durations_common_set.csv, table3_reconstruction_summaries.csv, rank_stability.csv
