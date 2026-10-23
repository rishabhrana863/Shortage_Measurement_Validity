# NDC-entry timing audit

Archive: 38 snapshots, 2019-12-29 to 2023-12-21.

## Dataset-wide check of the inherited-posting hypothesis (all 2,042 episodes)
- Drugs with >1 NDC: 235; of these, drugs where every NDC carries the *same* initial-posting date: 181 (77%)
- NDCs that first appear in a later snapshot than their drug's first appearance: 370 of 2,042 (18.1%); median lag 385.0 days, max 1416
- Among episodes posted after the archive begins (observable entry, n=1251): 306 NDCs entered later than their drug, and 173 of those (57%) still carry the drug's earliest posting date as their own start.

Reading: 'Initial posting' is a drug-entry date. NDCs added to an existing entry inherit it, so their recorded durations
include time before the product was listed in the shortage (and, for the 140, before it was approved).

## The 140 flagged episodes
- unresolved_entered_with_drug_but_approved_later: 71
- confirmed_late_entering_NDC: 64
- plausible_late_entrant_left_censored: 4
- unresolved_pre_archive: 1
Confidence: {'interval-bounded': 5, 'observed': 64, 'unavailable': 71}

## Implication for the unit of analysis
- Drug-level duration (entry posting → entry resolution) is unaffected by NDC entry timing; ~298 drugs.
- NDC-level duration needs the revised eligible start interval (previous snapshot, first seen] — interval-censored entry —
  and is unidentifiable for NDCs already present at the first snapshot (left-censored) when posting predates the archive.

## Two further findings from the dataset-wide check

### Drug entries that themselves appear in the archive long after their posting date
Of 184 drugs posted after the archive begins, the drug's *first* archive appearance lags its posting by ≤60 days for 117,
61–180 days for 35, 181–365 days for 20, and more than a year for 12 (32 episodes: atropine injection 1,450 d, sodium
chloride 23.4% 1,413 d, sulfasalazine 1,065 d, desmopressin spray 977 d …). Ketamine and bumetanide show the same pattern
with pre-archive postings (2018 posting, first seen 2022–2023). An entry cannot be in shortage for years without appearing in
any snapshot, so these are most plausibly **re-used FDA entries**: a drug that re-enters shortage is listed under its
original entry, which keeps the original initial-posting date. This affects the drug-level start date too, not only
NDC-level entry — 103 of the 1,251 post-archive episodes have a gap of more than a year between posting and first observation.

### Archive spacing is uneven
38 snapshots: 16 in 2020, 10 in 2021, 2 in 2022, 9 in 2023. Largest gaps: 2021-11-30 → 2022-10-04 (308 days) and
2023-05-14 → 2023-11-14 (184 days). 'First seen' therefore bounds entry only to the preceding gap; many 2023 first-seen
dates (2023-11-14) sit after the 184-day gap. Interval-censored entry is the honest representation; a point date is not.

## Classification of the 140 — corrected reading
- 64 confirmed late-entering NDCs (entry observed between two snapshots; marketing and approval precede first sight).
- 71 'entered with the drug but approved later': in nearly all of these the *drug entry* first appears in the archive long
  after its recorded posting — the re-used-entry mechanism above — so the recorded start is wrong at drug level as well.
- 4 left-censored plausible late entrants; 1 unresolved (first observed before its marketing start — identity check).
