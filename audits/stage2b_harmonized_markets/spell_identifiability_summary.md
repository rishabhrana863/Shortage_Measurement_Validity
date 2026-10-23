# Spell identifiability summary (drug level, from deposited episode fields)

Drugs: 298 | episodes preserved: 2042 | archive: 38 snapshots 2019-12-29–2023-12-21

**Limit of this audit:** the raw snapshot CSVs are not in the deposit, so status is reconstructed from each NDC's first/last
sight and count of sightings. A full absent/current/resolved sequence per snapshot — and any current→resolved→current
recurrence — needs the 38 archived files (listed with Wayback URLs and hashes in the workbook's Snapshot Audit sheet).

## Entry (not-in-shortage → current)
- OBSERVED (absent→current bracketed): 184
- LEFT-CENSORED (pre-archive posting): 114

## Exit (current → resolved / disappearance)
- OBSERVED (Resolved mark): 146
- ONGOING at last snapshot: 137
- INFERRED (disappeared without Resolved mark): 15

## Multiple plausible spells
- none detected: 276
- INFERRED (absent from ≥1 snapshot inside window): 22
(absence inside the window is INFERRED from sighting counts; FDA removes resolved listings after a retention period and a missed
capture can also produce an absence, so this is a flag for the raw-snapshot check, not a confirmed recurrence)

## Interval uncertainty from snapshot spacing
- Entry bracket (observed entries, n=184): median 71.0 days, max 308
- Exit bracket (n=18): median 184.0 days, max 308
- Drugs posted after archive start whose first sight lags posting by >365 days: 12 (entry re-use / re-listing suspects)

## Identifiable independent spells — the sample size for the original question
| Definition | Drugs |
|---|---|
| Observed entry only | 184 |
| Observed entry AND observed resolution | 62 |
| **Strict:** observed entry, observed resolution or ongoing, no internal absence | **169** |
| Relaxed: observed entry, no internal absence (inferred disappearance treated as censoring at last sight) | 178 |

Left-censored entries (114) can contribute to prevalence/persistence descriptions but not to onset-anchored duration.

## Notes on the resolution date and the strict set
- The workbook's resolution date is FDA's own 'Date of Update' marked Resolved (as first seen in an archived snapshot), so exit is
  FDA-dated; only the observation lag (which snapshot first showed it) is unknown. Entry has no FDA date other than the
  (unreliable) initial posting, so entry is purely interval-bracketed by snapshots.
- Strict set composition: see the run output appended by the analyst — observed resolutions are the survival 'events'; ongoing
  drugs are right-censored at the last snapshot. Drugs in the strict set whose first sight lags posting by more than a year
  are entry re-use suspects: their onset should be taken as the bracketed first sighting, never the posting date.
