#!/usr/bin/env python3
"""
NDC-entry timing audit. Tests whether 'Initial posting' in the 2,042-episode file is a drug-entry date inherited by
NDCs that joined the shortage record later. Uses the episode file's own archive fields (First seen / Last seen /
Snapshots observed) plus NDC marketing start and Orange Book approval dates. Produces:
  ndc_entry_timing_audit.csv   the 140 flagged episodes with original and reconstructed timing evidence
  ndc_entry_timing_summary.md  classification counts for the 140 and a dataset-wide check of the hypothesis
Nothing replaces the initial-posting date; marketing start is not shortage onset.
"""
import csv, re, sys, collections, datetime as dt, statistics as st
import openpyxl
sys.path.insert(0, ".")
from stage1_join_audit import parse_date
D = sys.argv[1]

wb = openpyxl.load_workbook("FDA_Recovery_Time_Validation.xlsx", read_only=True)
rows = list(wb["FDA Product Episodes"].iter_rows(values_only=True)); H = rows[3]
EP = [dict(zip(H, r)) for r in rows[4:] if r and r[0]]
for e in EP:
    e["ndc9"] = re.sub(r"\D", "", str(e["NDC9"]).replace("​", "")).zfill(9)
    for k in ("Initial posting", "Resolution / censor", "First seen", "Last seen", "Start month"): e[k] = parse_date(e[k])
snap = sorted({parse_date(r[1]) for r in list(wb["Snapshot Audit"].iter_rows(values_only=True))[4:] if r and r[1] and parse_date(r[1])})
first_snap = snap[0]
def prev_snapshot(d):
    p = [s for s in snap if s < d]; return max(p) if p else None

# drug-level earliest archive appearance and posting
by_drug = collections.defaultdict(list)
for e in EP: by_drug[e["Generic name"]].append(e)
drug_first_seen = {g: min(x["First seen"] for x in v) for g, v in by_drug.items()}
drug_posting_distinct = {g: len({x["Initial posting"] for x in v}) for g, v in by_drug.items()}

# NDC marketing start (current + excluded) and OB approval by application
S1 = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1_audit/match_by_episode.csv"))}
S1b = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1b_audit/recovered_matches.csv"))}
ob_first = collections.defaultdict(list)
for r in csv.DictReader(open(f"{D}/ob/products.txt", encoding="utf-8", errors="replace"), delimiter="~"):
    d = parse_date(r["Approval_Date"]);
    if d: ob_first[re.sub(r"\D", "", r["Appl_No"])].append(d)
ob_first = {k: min(v) for k, v in ob_first.items()}

flag = {c["ndc9"] + "|" + c["posting"] for c in csv.DictReader(open("stage2b_audit/market_definition_changes.csv")) if c["own_product_approved_after_posting"] == "1"}

out = []
for e in EP:
    k = e["ndc9"] + "|" + e["Initial posting"].isoformat()
    if k not in flag: continue
    src = S1[k] if S1[k]["ndc_matched"] == "1" else S1b.get(k, {})
    mstart = parse_date(src.get("ndc_start_mkt") or src.get("start_mkt") or ""); appl = re.sub(r"\D", "", src.get("ndc_appl_no") or src.get("appl_no") or "")
    approval = ob_first.get(appl)
    fs, ls = e["First seen"], e["Last seen"]; dfs = drug_first_seen[e["Generic name"]]
    prev = prev_snapshot(fs)
    # revised eligible start interval: (previous snapshot, first seen]; left-bounded by marketing start/approval if later
    lo = prev; hi = fs
    bounds = [x for x in (mstart, approval) if x]
    if bounds and max(bounds) > (lo or dt.date.min): lo = max(bounds)
    entry_after_drug = fs > dfs                       # NDC appeared in a later snapshot than the drug's first appearance
    timing_consistent = all(x <= fs for x in bounds)  # marketing/approval precede first observation
    if entry_after_drug and timing_consistent and fs > first_snap:
        cls, conf = "confirmed_late_entering_NDC", "observed"
    elif fs == first_snap and e["Initial posting"] < first_snap:
        cls, conf = "unresolved_pre_archive" if not timing_consistent else "plausible_late_entrant_left_censored", "interval-bounded"
    elif entry_after_drug:
        cls, conf = "plausible_late_entrant", "interval-bounded"
    elif not timing_consistent:
        cls, conf = "unresolved_inconsistent_timing", "unavailable"   # seen before marketing/approval: identity or date problem
    else:
        cls, conf = "unresolved_entered_with_drug_but_approved_later", "unavailable"
    out.append({"ndc9": e["ndc9"], "generic": e["Generic name"], "drug_level_first_posting": e["Initial posting"].isoformat(),
                "drug_distinct_posting_dates_across_its_NDCs": drug_posting_distinct[e["Generic name"]],
                "drug_earliest_archive_appearance": dfs.isoformat(), "ndc_first_archive_appearance": fs.isoformat(),
                "ndc_last_archive_appearance": ls.isoformat(), "snapshots_observed": e["Snapshots observed"],
                "ndc_marketing_start": mstart.isoformat() if mstart else "", "application_first_approval": approval.isoformat() if approval else "",
                "original_resolution_or_censor": e["Resolution / censor"].isoformat(), "original_duration_days": e["Duration days"], "original_status": e["Censoring status"],
                "revised_eligible_start_interval": f"({lo.isoformat() if lo else 'unbounded'}, {hi.isoformat()}]",
                "revised_max_duration_days_from_interval_end": (e["Resolution / censor"] - hi).days,
                "classification": cls, "confidence": conf})
with open("stage2b_audit/ndc_entry_timing_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

# dataset-wide hypothesis check
same_posting = sum(1 for g, n in drug_posting_distinct.items() if len(by_drug[g]) > 1 and n == 1)
multi = sum(1 for g in by_drug if len(by_drug[g]) > 1)
late_all = [e for e in EP if e["First seen"] > drug_first_seen[e["Generic name"]]]
late_gap = [ (e["First seen"] - drug_first_seen[e["Generic name"]]).days for e in late_all]
post_archive = [e for e in EP if e["Initial posting"] >= first_snap]
late_post = [e for e in post_archive if e["First seen"] > drug_first_seen[e["Generic name"]]]
inherit = sum(1 for e in late_post if e["Initial posting"] == min(x["Initial posting"] for x in by_drug[e["Generic name"]]))
cnt = collections.Counter(o["classification"] for o in out); conf = collections.Counter(o["confidence"] for o in out)
md = f"""# NDC-entry timing audit

Archive: {len(snap)} snapshots, {first_snap} to {snap[-1]}.

## Dataset-wide check of the inherited-posting hypothesis (all 2,042 episodes)
- Drugs with >1 NDC: {multi}; of these, drugs where every NDC carries the *same* initial-posting date: {same_posting} ({100*same_posting/multi:.0f}%)
- NDCs that first appear in a later snapshot than their drug's first appearance: {len(late_all)} of 2,042 ({100*len(late_all)/2042:.1f}%); median lag {st.median(late_gap) if late_gap else 'n/a'} days, max {max(late_gap) if late_gap else 'n/a'}
- Among episodes posted after the archive begins (observable entry, n={len(post_archive)}): {len(late_post)} NDCs entered later than their drug, and {inherit} of those ({100*inherit/max(1,len(late_post)):.0f}%) still carry the drug's earliest posting date as their own start.

Reading: 'Initial posting' is a drug-entry date. NDCs added to an existing entry inherit it, so their recorded durations
include time before the product was listed in the shortage (and, for the 140, before it was approved).

## The 140 flagged episodes
{chr(10).join(f'- {k}: {v}' for k, v in cnt.most_common())}
Confidence: {dict(conf)}

## Implication for the unit of analysis
- Drug-level duration (entry posting → entry resolution) is unaffected by NDC entry timing; ~{len(by_drug)} drugs.
- NDC-level duration needs the revised eligible start interval (previous snapshot, first seen] — interval-censored entry —
  and is unidentifiable for NDCs already present at the first snapshot (left-censored) when posting predates the archive.
"""
open("stage2b_audit/ndc_entry_timing_summary.md", "w").write(md); print(md)
