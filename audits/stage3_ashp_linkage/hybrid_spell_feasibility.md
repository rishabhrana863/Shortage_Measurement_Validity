# Hybrid ASHP–FDA spell feasibility

ASHP bulletins: 958; with ≥1 FDA candidate overlapping in time: 166; crosswalk rows (bulletin × FDA record): 418
Level-1 identity on crosswalk rows: {'MEDIUM': 298, 'LOW': 62, 'HIGH': 58}

## Spell classification (one row per ASHP bulletin with a candidate)
{'AMBIGUOUS': 69, 'PROBABLE': 70, 'CONFIRMED': 27}
AMBIGUOUS reasons: {'13 FDA candidates': 5, '10 FDA candidates': 3, '14 FDA candidates': 7, '5 FDA candidates': 8, '2 FDA candidates': 13, '6 FDA candidates': 2, 'FDA resolution precedes ASHP creation': 5, '1 FDA candidates': 11, 'FDA entry not inside ASHP spell window': 8, 'FDA record shows internal absence': 6, '3 FDA candidates': 1}

## The metrics requested
| Metric | Value |
|---|---|
| ASHP bulletin coverage (unique bulletins matched to an FDA record) | 166 of 958 |
| Confirmed spell pairs (distinct bulletins, HIGH identity, FDA entry observed inside spell) | 27 (26 distinct FDA drugs) |
| Probable spell pairs | 70 |
| Observed FDA resolutions — events (CONFIRMED / CONFIRMED+PROBABLE) | 11 / 55 |
| Right-censored spells (CONFIRMED / CONFIRMED+PROBABLE) | 16 / 42 |
| Ambiguous / recurrent spells excluded | 69 |
| Duration plausibility, events (CONFIRMED) | min 60, q1 273, median 336, q3 634, max 1070 |
| Duration plausibility, events (CONFIRMED+PROBABLE) | min 60, q1 328, median 580, q3 807, max 2071; negative 0; >4 years 4 |
| Market-structure linkage: confirmed spells with bounded applicant counts | 27 of 27 |

Resolution decision date (FDA Date of Update marked Resolved) and the archive snapshot where it was first observed
are recorded separately in hybrid_spells.csv; the exit observation interval is the snapshot gap containing the first sighting.

## Reading
- CONFIRMED pairs are the primary analytical sample; PROBABLE are a sensitivity set; AMBIGUOUS are excluded pending review.
- An FDA resolution is attached only when it follows ASHP creation and the FDA record shows no internal absence — never
  'first FDA resolution after ASHP creation' alone.
- Event counts and independent drug counts, not bulletin counts, determine what analysis is credible.
