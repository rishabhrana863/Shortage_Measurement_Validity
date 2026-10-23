# Stage 1b — excluded-products recovery audit

Excluded file rows indexed: 206936. Stage 1 matches preserved untouched.

## Recovery against baseline
| Measure | Baseline | After excluded file |
|---|---|---|
| Previously unmatched episodes | 508 | 16 still unmatched (492 recovered) |
| Discontinuation-reason episodes unmatched | 34 of 40 | 1 of 40 (33 recovered) |
| Drugs without any NDC match | 41 of 298 | 1 of 298 (40 recovered) |
| Historically verified matches | 0 | 0 (excluded records are retrospective listings, not dated observations) |
| Combined episode coverage | 1534/2042 | 2026/2042 (99.2%) |

## Recovered episodes by exclusion flag (D=discontinued by firm, U=expired certification, E=listing deficiency, I=FDA inactivation)
{'D': 437, 'I': 55}

## Identity confidence of recovered matches
{'high_brand_name': 402, 'high_ob_ingredient': 76, 'unverifiable_no_application': 11, 'low_conflict_ob_ingredient:DICLOFENAC SODIUM': 1, 'low_conflict_ob_ingredient:FLUCONAZOLE': 1, 'low_conflict_ob_ingredient:TRIFLURIDINE': 1}

Note: the excluded-products file carries PROPRIETARYNAME only (nonproprietary name, substance, dosage form and
route are blank in all rows), so identity is checked against the brand name and, via the application number,
the Orange Book ingredient. Recovered rows cannot feed the substance/form/route participation proxy.

## Recovery by shortage reason (recovered / previously unmatched)
| Reason | Recovered |
|---|---|
| API procurement delay | 2/2 |
| Availability of API | 1/1 |
| Available | 3/3 |
| Delay in shipping | 1/1 |
| Delay in shipping of drug | 1/1 |
| Delay in shipping of the drug | 9/10 |
| Demand Increase for the Drug | 1/1 |
| Demand increase | 0/2 |
| Demand increase for the drug | 76/80 |
| Demand increase in the drug | 1/1 |
| Demand increase of the drug | 1/1 |
| Discontinuation of manufacture of the drug (from existing site). | 1/1 |
| Discontinuation of manufacturing | 1/1 |
| Discontinuation of the manufacture of the drug | 30/31 |
| Discontinuation of the manufacture of the drug. | 1/1 |
| Manufacturing Delay | 1/1 |
| Manufacturing delay | 4/4 |
| Molybdenum 99 shortage | 1/1 |
| Other | 166/170 |
| Regulatory delay | 5/5 |
| Requirements related to complying with good manufacturing practices | 18/19 |
| Requirements related to complying with good manufacturing practices & demand increase for the drug | 3/3 |
| Shortage of active ingredient | 1/1 |
| Shortage of an active ingredient | 21/21 |
| Shortage of an active ingredient. | 1/1 |
| Unknown | 142/145 |

## Recovery by posting year
| Year | Recovered |
|---|---|
| 2018 | 132/133 |
| 2019 | 94/100 |
| 2020 | 106/110 |
| 2021 | 52/56 |
| 2022 | 54/55 |
| 2023 | 54/54 |

## Consistency between exclusion record and shortage episode (recovered rows)
| Check | Count |
|---|---|
| Marketing end date before posting | 44 |
| Marketing end date during the episode | 110 |
| Marketing end date after resolution/censor | 283 |
| No end date recorded | 55 |
| Orange Book application match | 451 |
| Marketing category | {'ANDA': 306, 'NDA': 137, 'NDA AUTHORIZED GENERIC': 17, 'UNAPPROVED DRUG FOR USE IN DRUG SHORTAGE': 15, 'UNAPPROVED DRUG OTHER': 9, 'BLA': 8} |

## Still unmatched after recovery
16 episodes; by reason: {'Demand increase for the drug': 4, 'Other': 4, 'Unknown': 3, 'Demand increase': 2, 'Discontinuation of the manufacture of the drug': 1, 'Requirements related to complying with good manufacturing practices': 1, 'Delay in shipping of the drug': 1}

## Reading the result
- A "D" flag with an end date during or after the episode is consistent with a product withdrawn in the shortage
  — retrospective evidence of disposition, not proof the firm was observed participating in 2020–2023.
- An end date *before* posting means the excluded listing cannot be the product that was in shortage as posted,
  or the episode's NDC was reused; treat as identity-uncertain.
- "U/E/I" flags are administrative, not market exits; they say nothing about discontinuation.
- The shortage-reason label "discontinuation" and the exclusion flag "D" are two independent signals; the
  competing-event disposition for Stage 4 should require both, or an archive observation.
