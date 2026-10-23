# Stage 2 — market-structure feasibility audit

Listings ingested: current 57873, excluded 77503 (KITs dropped; only listings with an Orange Book application number
can be placed in a market). Orange Book markets (ingredient + DF;Route): 4530.

## Analytical eligibility (coverage ≠ eligibility)
| Identity status | Episodes |
|---|---|
| confirmed | 2009 |
| confirmed_manual | 11 |
| unmatched | 16 |
| excluded_identity_conflict | 6 |

Date flags (marketing end before posting), classified: {'genuine_historical_listing_withdrawn_before_posting': 33, 'plausible_delayed_posting': 11}; of these, 2 overlap the identity exclusions.
Eligible (confirmed) episodes: 2020; with a defined Orange Book market (application-based, non-KIT): 1901 (94.1%); drugs with a market: 277.

Episodes without a market, by reason: {'no application (unapproved/BLA)': 43, 'KIT': 44, 'application not in Orange Book': 32}

## Measure A — approved applicants (Orange Book, approved by posting)
Episode level: {'0': 3, '1': 218, '2': 70, '3–4': 119, '5–9': 392, '10–19': 762, '20+': 337}   |  median 11
Drug level (median per drug): {'0': 1, '1': 58, '2': 20, '3–4': 34, '5–9': 69, '10–19': 75, '20+': 20}

## Measure B — retrospective participation proxy (labelers with marketing window containing posting)
Episode level: {'0': 5, '1': 107, '2': 150, '3–4': 98, '5–9': 391, '10–19': 618, '20+': 532}   |  median 13
Drug level: {'0': 3, '1': 44, '2': 37, '3–4': 28, '5–9': 70, '10–19': 55, '20+': 40}

## Agreement between A and B
Spearman (episode level): 0.772
{'B = A': 178, 'B > A (more labelers than approved applicants)': 1145, 'B < A': 578}
B > A arises from repackagers/relabelers and authorized generics (several labelers per application); B < A from applicants
with approvals but no listing in a marketing window containing the posting date.

## Sensitivity of B
- B vs B(end−365): 0.996
- B vs B(current only): 0.923
- share of episodes where B changes with end−365: 0.467
- share where B changes dropping excluded listings: 0.894

## Coverage of a defined market by posting year (market defined / listings present)
| Year | Market defined | Any listing |
|---|---|---|
| 2018 | 450/463 | 450/463 |
| 2019 | 299/320 | 299/320 |
| 2020 | 379/398 | 379/398 |
| 2021 | 190/205 | 190/205 |
| 2022 | 254/273 | 254/273 |
| 2023 | 329/361 | 329/361 |

## By outcome
| Outcome | Market defined | Any listing |
|---|---|---|
| resolved | 783/841 | 783/841 |
| right-censored | 1118/1179 | 1118/1179 |

## By therapeutic category (first listed; top 12)
| Category | Market defined |
|---|---|
| Psychiatry | 354/354 |
| Anesthesia | 266/271 |
| Cardiovascular | 177/177 |
| Anti-Infective | 170/171 |
| Endocrinology/Metabolism | 115/169 |
| Gastroenterology | 161/168 |
| Analgesia/Addiction | 108/114 |
| Oncology | 97/102 |
| Ophthalmology | 84/92 |
| Neurology | 82/83 |
| Rheumatology | 47/51 |
| Other | 30/38 |

## Markets: 262 distinct; episodes per market: median 4.0, max 126

## Still-unmatched episodes (16), listed individually
- Lidocaine Hydrochloride (Xylocaine) Injection | posted 2018-06-13 | Demand increase for the drug | right-censored
- Olmesartan Medoxomil Tablets | posted 2019-03-12 | Unknown | resolved
- Metoprolol Tartrate Injection, USP | posted 2019-04-02 | Discontinuation of the manufacture  | resolved
- Tacrolimus Capsules | posted 2019-05-17 | Demand increase for the drug | resolved
- Triamcinolone Acetonide (Triesence) Injection | posted 2019-09-12 | Requirements related to complying w | right-censored
- Difluprednate (Durezol) Ophthalmic Emulsion | posted 2019-09-12 | Unknown | resolved
- Leuprolide Acetate (Lupron Depot; Lupron Depo | posted 2019-12-10 | Other | resolved
- Etomidate Injection | posted 2020-04-10 | Demand increase for the drug | right-censored
- Sertraline Hydrochloride Tablets | posted 2020-05-29 | Other | right-censored
- Sertraline Hydrochloride Tablets | posted 2020-05-29 | Other | resolved
- Sertraline Hydrochloride Tablets | posted 2020-05-29 | Other | right-censored
- Digoxin Injection | posted 2021-06-04 | Delay in shipping of the drug | right-censored
- Mannitol Injection | posted 2021-09-23 | Demand increase for the drug | right-censored
- IV Fat Emulsion | posted 2021-10-25 | Demand increase | right-censored
- IV Fat Emulsion | posted 2021-10-25 | Demand increase | right-censored
- Oxytocin Injection | posted 2022-09-23 | Unknown | resolved

## Caveats carried forward
- A is regulatory competition potential; B is retrospectively reconstructed participation. Not combined.
- FDA marketing end dates can reflect expected expiry of the last lot rather than the end of production; the end−365 sensitivity brackets that.
- The current Orange Book may omit approvals later removed or transferred; historical editions remain relevant.
- B counts labelers, not independent manufacturers.
- See inspection_samples.csv for manual review of zero-, single- and high-count markets and A/B disagreements.
