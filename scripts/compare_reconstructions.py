#!/usr/bin/env python3
"""
Centrepiece comparison for the OSCM paper, revised spec (23 Oct):

MAIN  R1 vs R2 on the SAME eligible drugs with the SAME exit rule.
      Common exit rule (drug level): RESOLVED only if every NDC observed for the drug carries a Resolved mark (exit =
      latest Resolved decision date); AMBIGUOUS if some NDCs resolved and others not; ONGOING if none resolved and the drug
      is present at the last snapshot; DISAPPEARED if none resolved and last sight precedes the last snapshot (censor, not event).
      R1 onset = earliest recorded FDA posting across the drug's NDCs.
      R2 onset = archive-observed entry interval (previous snapshot, first sighting]; eligible only when posting is after
                 the archive start AND first sighting is not the first snapshot (entry bracketed).
      Eligible set = drugs with a bracketed R2 entry AND a decidable exit (RESOLVED / ONGOING / DISAPPEARED). AMBIGUOUS
      exits are retained as a separate count, never silently dropped.
      Sensitivity: R2 durations at earliest-plausible onset (previous snapshot) and latest-plausible (first sighting).
SECONDARY  R0 pseudoreplication: NDC-level rows vs drug-level rows for the same drugs — row counts, effective n, how the
      NDC rows of one drug share identical duration/outcome (inherited values), and the KM median at both levels.
      R3 coverage only: how many R1/R2-eligible drugs have a CONFIRMED / PROBABLE ASHP link; no population KM.
RANK  Persistence ranking (top 20 by observed duration) under R1 vs R2(earliest) vs R2(latest); each drug classified
      DEFINITE (top-20 under every scenario), POSSIBLE (top-20 in some), UNRANKABLE (ambiguous exit / not eligible);
      Spearman rank correlation R1 vs R2 on the common eligible set; sole-source share of each top-20 from Orange Book bounds.
No modelling. KM is Kaplan–Meier with right-censoring only; medians reported 'not reached' when S never falls below 0.5.
"""
import csv, re, sys, os, collections, statistics as st, datetime as dt
import openpyxl
sys.path.insert(0, ".")
from stage1_join_audit import parse_date

OUT = "stage4_compare"; os.makedirs(OUT, exist_ok=True)
wb = openpyxl.load_workbook("FDA_Recovery_Time_Validation.xlsx", read_only=True)
rows = list(wb["FDA Product Episodes"].iter_rows(values_only=True)); H = rows[3]
EP = [dict(zip(H, r)) for r in rows[4:] if r and r[0]]
for e in EP:
    for k in ("Initial posting", "Resolution / censor", "First seen", "Last seen"): e[k] = parse_date(e[k])
snap = sorted({parse_date(r[1]) for r in list(wb["Snapshot Audit"].iter_rows(values_only=True))[4:] if r and r[1] and parse_date(r[1])})
FIRST, LAST = snap[0], snap[-1]
def prev_snap(d):
    p = [s for s in snap if s < d]; return max(p) if p else None

# ---------------------------------------------------------------- drug-level records with the common exit rule
by = collections.defaultdict(list)
for e in EP: by[e["Generic name"]].append(e)
drugs = []
for g, v in by.items():
    posting = min(x["Initial posting"] for x in v); fs = min(x["First seen"] for x in v); ls = max(x["Last seen"] for x in v)
    resolved = [x for x in v if x["Event observed"]]
    if len(resolved) == len(v): exit_status, exit_date = "RESOLVED", max(x["Resolution / censor"] for x in v)
    elif resolved: exit_status, exit_date = "AMBIGUOUS", None
    elif ls >= LAST: exit_status, exit_date = "ONGOING", LAST
    else: exit_status, exit_date = "DISAPPEARED", ls
    r2_eligible = posting >= FIRST and fs > FIRST
    drugs.append(dict(generic=g, n_ndc=len(v), posting=posting, first_seen=fs, last_seen=ls, prev=prev_snap(fs) if fs > FIRST else None,
                      exit_status=exit_status, exit_date=exit_date, event=int(exit_status == "RESOLVED"), r2_eligible=r2_eligible,
                      n_resolved_ndc=len(resolved)))

def km(durs, events):
    pairs = sorted(zip(durs, events)); S = 1.0; curve = []; n = len(pairs)
    i = 0
    while i < n:
        t = pairs[i][0]; d = sum(1 for x in pairs[i:] if x[0] == t and x[1]); at = n - i
        if d: S *= 1 - d / at
        curve.append((t, S)); i += sum(1 for x in pairs[i:] if x[0] == t)
    return curve
def S_at(curve, t):
    s = 1.0
    for x, v in curve:
        if x <= t: s = v
        else: break
    return s
def km_median(curve):
    for t, s in curve:
        if s < 0.5: return t
    return "not reached"
def summarize(name, durs, events, n_amb=0, extra=""):
    c = km(durs, events)
    return {"rule": name, "spells": len(durs), "events": sum(events), "ambiguous_exit_excluded": n_amb,
            "KM_median_days": km_median(c), "S_110": round(S_at(c, 110), 3), "S_180": round(S_at(c, 180), 3), "S_365": round(S_at(c, 365), 3),
            "share_obs_duration_gt_1y": round(sum(1 for d in durs if d > 365) / len(durs), 3) if durs else "", "note": extra}
# NB: for ongoing drugs these are elapsed observation / censoring times, not completed recovery durations

# ---------------------------------------------------------------- MAIN: R1 vs R2 on the common eligible set
elig = [d for d in drugs if d["r2_eligible"]]
amb = [d for d in elig if d["exit_status"] == "AMBIGUOUS"]
common = [d for d in elig if d["exit_status"] != "AMBIGUOUS"]
def dur(d, onset): return (d["exit_date"] - onset).days
R1 = [dur(d, d["posting"]) for d in common]; EV = [d["event"] for d in common]
R2_early = [dur(d, d["prev"]) for d in common]
# latest plausible onset = first sighting, but never later than the FDA resolution decision date or the recorded posting
# (a spell posted and resolved inside one archive gap is first seen already resolved)
def latest_onset(d):
    cands = [d["first_seen"]]
    if d["exit_status"] == "RESOLVED": cands.append(d["exit_date"])
    return min(cands)
R2_late = [dur(d, latest_onset(d)) for d in common]
n_late_capped = sum(1 for d in common if latest_onset(d) != d["first_seen"])
summ = [summarize("R1 posting-anchored (common set)", R1, EV, len(amb), "onset = earliest recorded FDA posting"),
        summarize("R2 archive-observed, earliest plausible onset", R2_early, EV, len(amb), "onset = snapshot before first sighting"),
        summarize("R2 archive-observed, latest plausible onset", R2_late, EV, len(amb), "onset = first sighting")]
# paired differences
diff_late = [a - b for a, b in zip(R1, R2_late)]; diff_early = [a - b for a, b in zip(R1, R2_early)]
# resolution-status agreement R1 vs R2 is identical by construction (same exit rule) — report status distribution instead,
# and the status change relative to the ORIGINAL per-NDC coding (any NDC resolved => 'resolved' in the original workbook)
orig_any = {d["generic"]: int(d["n_resolved_ndc"] > 0) for d in drugs}
status_tab = collections.Counter((("orig: any NDC resolved" if orig_any[d["generic"]] else "orig: none resolved"), "common rule: " + d["exit_status"]) for d in drugs)

# ---------------------------------------------------------------- SECONDARY: R0 pseudoreplication
ndc_rows = [e for e in EP if e["Generic name"] in {d["generic"] for d in common}]
r0_d = [e["Duration days"] for e in ndc_rows]; r0_e = [int(bool(e["Event observed"])) for e in ndc_rows]
ident_share = []
for d in common:
    v = by[d["generic"]]
    if len(v) > 1: ident_share.append(len({(x["Duration days"], x["Event observed"]) for x in v}) == 1)
pseudo = {"ndc_rows_for_common_drugs": len(ndc_rows), "drugs": len(common), "rows_per_drug_median": st.median(d["n_ndc"] for d in common), "rows_per_drug_max": max(d["n_ndc"] for d in common),
          "multi_ndc_drugs_with_identical_duration_and_outcome_across_all_ndcs": f"{sum(ident_share)}/{len(ident_share)}",
          "R0_ndc_level": summarize("R0 NDC-level (same drugs)", r0_d, r0_e, 0, "each NDC row counted as a spell"),
          "R1_drug_level": summ[0]}

# ---------------------------------------------------------------- SECONDARY: R3 coverage
hyb = list(csv.DictReader(open("stage3_ashp/hybrid_spells.csv")))
link = {h["fda_generic"]: h["spell_confidence"] for h in hyb if h.get("fda_generic")}
r3 = collections.Counter(link.get(d["generic"], "no ASHP link") for d in common)
r3_conf = [d for d in common if link.get(d["generic"]) == "CONFIRMED"]
r3_summary = {"eligible_drugs": len(common), "linkage": dict(r3), "confirmed_with_event": sum(d["event"] for d in r3_conf),
              "note": "R3 is reported as linkage coverage; no population KM is drawn from the confirmed subset"}

# ---------------------------------------------------------------- RANK stability
M = list(csv.DictReader(open("stage2b_audit/market_definition_changes.csv")))
mk = collections.defaultdict(list)
for m in M: mk[m["generic"]].append(m)
def sole(g):
    v = mk.get(g, [])
    if not v: return ""
    return int(st.median(int(x["point_confirmed_plus_provisional"]) for x in v) <= 1)
def top20(durs):
    order = sorted(range(len(common)), key=lambda i: -durs[i]); return {common[i]["generic"] for i in order[:20]}
T1, T2e, T2l = top20(R1), top20(R2_early), top20(R2_late)
rank_rows = []
for i, d in enumerate(common):
    ins = [d["generic"] in T for T in (T1, T2e, T2l)]
    tier = "DEFINITE" if all(ins) else "POSSIBLE" if any(ins) else "not top-20"
    if tier != "not top-20":
        rank_rows.append({"generic": d["generic"], "tier": tier, "in_R1_top20": int(ins[0]), "in_R2_earliest_top20": int(ins[1]), "in_R2_latest_top20": int(ins[2]),
                          "R1_days": R1[i], "R2_earliest_days": R2_early[i], "R2_latest_days": R2_late[i], "exit_status": d["exit_status"], "sole_source_point": sole(d["generic"])})
for d in amb:
    rank_rows.append({"generic": d["generic"], "tier": "UNRANKABLE (ambiguous exit)", "exit_status": "AMBIGUOUS", "sole_source_point": sole(d["generic"])})
def spearman(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for pos, i in enumerate(o): r[i] = pos
        return r
    rx, ry = rk(x), rk(y); mx, my = st.mean(rx), st.mean(ry)
    return sum((a-mx)*(b-my) for a, b in zip(rx, ry)) / ((sum((a-mx)**2 for a in rx) * sum((b-my)**2 for b in ry)) ** 0.5)
rank_stats = {"definite_top20": sum(1 for r in rank_rows if r["tier"] == "DEFINITE"), "possible_top20": sum(1 for r in rank_rows if r["tier"] == "POSSIBLE"),
              "unrankable_ambiguous_exit": len(amb), "spearman_R1_vs_R2_latest": round(spearman(R1, R2_late), 3), "spearman_R1_vs_R2_earliest": round(spearman(R1, R2_early), 3),
              "sole_source_share_R1_top20": f"{sum(1 for r in rank_rows if r.get('in_R1_top20') == 1 and r['sole_source_point'] == 1)}/{sum(1 for r in rank_rows if r.get('in_R1_top20') == 1 and r['sole_source_point'] != '')}",
              "sole_source_share_R2_latest_top20": f"{sum(1 for r in rank_rows if r.get('in_R2_latest_top20') == 1 and r['sole_source_point'] == 1)}/{sum(1 for r in rank_rows if r.get('in_R2_latest_top20') == 1 and r['sole_source_point'] != '')}"}

# ---------------------------------------------------------------- write
with open(f"{OUT}/drug_level_records.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(drugs[0].keys())); w.writeheader(); w.writerows(drugs)
with open(f"{OUT}/table3_reconstruction_summaries.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ + [pseudo["R0_ndc_level"]])
with open(f"{OUT}/rank_stability.csv", "w", newline="") as f:
    keys = sorted({k for r in rank_rows for k in r}); w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rank_rows)
with open(f"{OUT}/paired_durations_common_set.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["generic", "exit_status", "event", "R1_days", "R2_earliest_days", "R2_latest_days", "entry_bracket_days"])
    for i, d in enumerate(common): w.writerow([d["generic"], d["exit_status"], d["event"], R1[i], R2_early[i], R2_late[i], (d["first_seen"] - d["prev"]).days])

def q(x): return f"median {round(st.median(x))}, IQR {round(st.quantiles(x, n=4)[0])}–{round(st.quantiles(x, n=4)[2])}, range {min(x)}–{max(x)}"
md = f"""# Reconstruction comparison — results (revised spec)

Drugs: {len(drugs)}. R2-eligible (posting after archive start, entry bracketed): {len(elig)}. Of these, exit AMBIGUOUS under the
common rule (some NDCs resolved, others not): {len(amb)} — retained as a separate category. **Common comparison set: {len(common)} drugs,
{sum(EV)} resolved (events), {sum(1 for d in common if d['exit_status']=='ONGOING')} ongoing, {sum(1 for d in common if d['exit_status']=='DISAPPEARED')} disappeared (censored at last sight).**

## Table 3a — entry-identifiable cohort and how the analytical subset is obtained
| Status under the shared exit rule | Drugs | Treatment |
|---|---|---|
| Resolved (every observed NDC carries a Resolved mark) | {sum(EV)} | survival event |
| Ongoing at last snapshot | {sum(1 for d in common if d['exit_status']=='ONGOING')} | right-censored |
| Disappeared without a Resolved mark | {sum(1 for d in common if d['exit_status']=='DISAPPEARED')} | censored at last verified observation |
| Ambiguous exit (some NDCs resolved, others not) | {len(amb)} | separate unresolved category, excluded from survival summaries |
| **Total entry-identifiable** | **{len(elig)}** | |
(The 31 ambiguous cases in Table 4 are counted among all 146 drugs with any resolved NDC — a different denominator from the 11 here.)

## Table 3b — same {len(common)} drugs, same exit rule, three onset definitions
| Rule | Spells | Events | KM median | S(110) | S(180) | S(365) | >1 y observed |
|---|---|---|---|---|---|---|---|
{chr(10).join(f"| {s['rule']} | {s['spells']} | {s['events']} | {s['KM_median_days']} | {s['S_110']} | {s['S_180']} | {s['S_365']} | {s['share_obs_duration_gt_1y']} |" for s in summ)}

Paired difference R1 − R2(latest onset): {q(diff_late)} days. R1 − R2(earliest onset): {q(diff_early)} days.
Latest-onset bound capped at the resolution date (spell posted and resolved inside one archive gap): {n_late_capped} drugs.
Entry bracket width in the common set: {q([(d['first_seen']-d['prev']).days for d in common])} days.
Drugs where R1 onset precedes R2 earliest-plausible onset by >365 days (entry-reuse suspects): {sum(1 for d in common if (d['prev']-d['posting']).days > 365)}.

## Table 4 — resolution status: original per-NDC coding vs the common drug-level rule (all {len(drugs)} drugs)
{chr(10).join(f'- {a} → {b}: {n}' for (a, b), n in sorted(status_tab.items()))}

## R0 pseudoreplication (same {len(common)} drugs)
- NDC rows: {pseudo['ndc_rows_for_common_drugs']} vs drugs: {pseudo['drugs']}; rows per drug median {pseudo['rows_per_drug_median']}, max {pseudo['rows_per_drug_max']}
- Multi-NDC drugs whose NDC rows all share one identical (duration, outcome): {pseudo['multi_ndc_drugs_with_identical_duration_and_outcome_across_all_ndcs']}
- R0 NDC-level: {pseudo['R0_ndc_level']['spells']} 'spells', {pseudo['R0_ndc_level']['events']} 'events', KM median {pseudo['R0_ndc_level']['KM_median_days']}, S(365) {pseudo['R0_ndc_level']['S_365']}
- R1 drug-level: {summ[0]['spells']} spells, {summ[0]['events']} events, KM median {summ[0]['KM_median_days']}, S(365) {summ[0]['S_365']}

## R3 linkage coverage (common set)
{r3_summary['linkage']}; CONFIRMED links with an FDA-resolved event: {r3_summary['confirmed_with_event']}. {r3_summary['note']}.

## Rank stability — top-20 persistence
- DEFINITE (top-20 under R1, R2-earliest and R2-latest): {rank_stats['definite_top20']}
- POSSIBLE (top-20 under some onset definitions): {rank_stats['possible_top20']}
- UNRANKABLE (ambiguous exit): {rank_stats['unrankable_ambiguous_exit']}
- Spearman, R1 vs R2-latest: {rank_stats['spearman_R1_vs_R2_latest']}; R1 vs R2-earliest: {rank_stats['spearman_R1_vs_R2_earliest']}
- Candidate universe: the {len(common)} rankable drugs; union of the three top-20 lists = {len(T1|T2e|T2l)} drugs = DEFINITE + POSSIBLE. The {len(amb)} ambiguous-exit drugs are outside the universe (UNRANKABLE).
- Drugs leaving the top-20 under archive-observed onset (own duration falls by >365 d): {sorted(d['generic'][:28] for i,d in enumerate(common) if d['generic'] in T1-T2e-T2l)}
- Drugs entering the top-20 under archive-observed onset: {sorted(d['generic'][:28] for i,d in enumerate(common) if d['generic'] in (T2e&T2l)-T1)} — relative rank changes only: their own R1 vs R2-latest differences are {[abs(R1[i]-R2_late[i]) for i,d in enumerate(common) if d['generic'] in (T2e&T2l)-T1]} days.
- All drugs with R1 − R2 > 365 d are ONGOING: their values are elapsed observation times, not completed durations.
- Sole-source share (Orange Book point estimate ≤1 applicant) of the R1 top-20: {rank_stats['sole_source_share_R1_top20']}; of the R2-latest top-20: {rank_stats['sole_source_share_R2_latest_top20']}

Files: drug_level_records.csv, paired_durations_common_set.csv, table3_reconstruction_summaries.csv, rank_stability.csv
"""
open(f"{OUT}/comparison_results.md", "w").write(md); print(md)
