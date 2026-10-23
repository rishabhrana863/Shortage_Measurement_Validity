# Shortage Measurement Validity

Code, audits and intermediate data for **"When Supply Chain Recovery Data Disagree: Measurement Validity and Event Reconstruction in Pharmaceutical Shortages"** 
The study asks how administrative reporting, product aggregation and shortage-event reconstruction affect the reliability of drug-shortage duration and recovery measurements, using archived FDA Drug Shortage snapshots (2019–2023), the ASHP resolved-shortage list, and the FDA Orange Book / NDC Directory.

## Headline result

Aggregate persistence estimates are robust to reconstruction assumptions (paired posting-vs-observed-entry difference: median 37 days across 173 drugs), but posting-date artefacts change which shortages appear most persistent: 16 of the top-20 longest shortages are stable under every onset definition, 4 change, and 11 drugs cannot be ranked because their resolution status is ambiguous at drug level. Every drug whose recorded duration exceeds the archive-supported duration by more than a year is an ongoing shortage posted under a re-used FDA entry.

## Repository layout

| Folder | Contents |
|---|---|
| `scripts/` | Every analysis step, in run order (below). Pure Python 3.11+, standard library plus `openpyxl`. |
| `inputs/` | The 2,042-episode FDA reconstruction workbook (from the [Supply_Chain_CRL](https://github.com/rishabhrana863/Supply_Chain_CRL) deposit, `paper_experiment/validation/`) and the ASHP resolved-bulletin extract (pulled 12 Sep 2026). |
| `taxonomy/` | Orange Book dosage-form/route harmonization map with reviewer decisions; legacy-injectable classification audit and exception list. |
| `audits/stage1_*` | NDC Directory matching and excluded-products recovery (coverage 75.1% → 99.2%; identity adjudication). |
| `audits/stage2_*` | Market-structure measures, harmonized market rerun, bounded applicant counts, validation register, application-provenance and NDC-entry-timing audits, drug-level spell identifiability. |
| `audits/stage3_ashp_linkage/` | Two-level ASHP–FDA crosswalk (pharmaceutical identity × spell identity) and hybrid-spell feasibility. |
| `audits/stage4_reconstruction_comparison/` | The paper's results: R1 vs R2 on the common 173-drug cohort, R0 pseudoreplication, R3 linkage coverage, rank stability. |

Each audit folder carries a `provenance.log` with SHA-256 hashes of its inputs.

## Reproducing

External FDA files are not redistributed (size and licence); download the current **NDC Directory** (`ndctext.zip`), **NDC excluded products** (`ndc_excluded.zip`) and **Orange Book data files** (`EOBZIP_*.zip`) from fda.gov, unzip into `fda_inputs/{ndc,exc,ob}/`, then from the repository root:

```
python -I scripts/stage1_join_audit.py --episodes inputs/episode_file/FDA_Recovery_Time_Validation.xlsx --ndc current=fda_inputs/ndc/product.txt --ob current=fda_inputs/ob/products.txt --out stage1_audit
python -I scripts/stage1b_excluded_recovery.py --stage1 stage1_audit/match_by_episode.csv --episodes inputs/episode_file/FDA_Recovery_Time_Validation.xlsx --excluded fda_inputs/exc/Products_excluded.txt --ob fda_inputs/ob/products.txt --out stage1b_audit
python -I scripts/stage2_market_structure_audit.py --episodes inputs/episode_file/FDA_Recovery_Time_Validation.xlsx --stage1 stage1_audit/match_by_episode.csv --stage1b stage1b_audit/recovered_matches.csv --ndc fda_inputs/ndc/product.txt --excluded fda_inputs/exc/Products_excluded.txt --ob fda_inputs/ob/products.txt --adjudication stage1_audit/name_conflict_adjudication.csv --out stage2_audit
python -I scripts/build_form_route_harmonization.py taxonomy/ob_dfroute_labels.tsv stage2_audit/episode_measures.csv
python -I scripts/legacy_injectable_audit.py fda_inputs
python -I scripts/stage2b_market_rerun.py fda_inputs
python -I scripts/build_validation_register.py
python -I scripts/application_provenance_audit.py fda_inputs
python -I scripts/ndc_entry_timing_audit.py fda_inputs
python -I scripts/drug_spell_audit.py
python -I scripts/ashp_fda_crosswalk.py
python -I scripts/compare_reconstructions.py
```

Scripts expect to run from a directory containing `FDA_Recovery_Time_Validation.xlsx`, `ashp_resolved_bulletins.csv` and `form_route_harmonization.csv` (copy them from `inputs/` and `taxonomy/`), and write to the `stage*_audit/` folders named above; the committed `audits/` folders are those outputs as of the commit date.

## Reconstruction rules compared

| Rule | Unit | Onset | Exit |
|---|---|---|---|
| R0 | NDC | recorded FDA initial posting | first archived Resolved mark, else censor |
| R1 | drug | earliest recorded posting across NDCs | shared rule: resolved only if every observed NDC is resolved; some → ambiguous; none → ongoing / disappeared (censor) |
| R2 | drug | archive-observed entry interval (previous snapshot, first sighting], latest bound capped at resolution date | shared rule as R1 |
| R3 | drug | ASHP bulletin creation | FDA Resolved decision date, same-spell linkage required; reported as linkage coverage only |

## Relationship to other work

The episode workbook was built as an external benchmark for the author's simulation papers (Annals of Operations Research, ANOR-D-26-03489; Journal of Decision Systems, 262318073). Those papers use only its Kaplan–Meier median and day-110 resolution share; the analyses here are new. The HHS/ASPE archival reconstruction (NBK611681) is the published comparator; its documented duplicate listings and later-added NDCs are quantified here, not newly discovered.

## AI assistance

Parsing rules, deterministic matching code and audit scripts were developed interactively with an LLM assistant (Claude, Anthropic); every mapping rule carries a recorded human decision (`taxonomy/form_route_harmonization.csv`, column `reviewer_decision`). No model output enters the results at run time. The author is responsible for validating all outputs.

## Licence

Code: MIT. Derived data tables: CC BY 4.0. FDA and ASHP source data remain subject to their publishers' terms.
