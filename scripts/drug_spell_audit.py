#!/usr/bin/env python3
"""
Drug-level spell-identification audit from the deposited episode file (no raw snapshot CSVs available).

Per NDC the workbook gives: First seen, Last seen, Snapshots observed, Resolution/censor (first snapshot marked Resolved),
Event observed. Per drug (298 generic names) this script reconstructs:
  observation window      [earliest first-seen, latest last-seen] across its NDCs
  expected snapshots      number of archive snapshots falling in that window
  internal absences       expected minus max NDC-level 'snapshots observed' (a drug observed in fewer snapshots than its
                          window contains was absent from some captures)  -> candidate additional spells (INFERRED)
  entry                   OBSERVED if the drug's posting is after the archive start AND first seen is not the first
                          snapshot (so an absent->current transition is bracketed); otherwise LEFT-CENSORED
  resolution              OBSERVED if any NDC has an observed Resolved mark; DISAPPEARED if the drug's last sight precedes
                          the final snapshot without a Resolved mark (INFERRED exit: absence is not evidence of resolution);
                          ONGOING if last seen at the final snapshot
  interval uncertainty    width of the snapshot gap bracketing entry and bracketing resolution
Every original episode is preserved; nothing is re-dated. Observed and inferred transitions are reported separately.
"""
import re, sys, collections, datetime as dt, statistics as st, csv
import openpyxl
sys.path.insert(0, ".")
from stage1_join_audit import parse_date

wb = openpyxl.load_workbook("FDA_Recovery_Time_Validation.xlsx", read_only=True)
rows = list(wb["FDA Product Episodes"].iter_rows(values_only=True)); H = rows[3]
EP = [dict(zip(H, r)) for r in rows[4:] if r and r[0]]
for e in EP:
    for k in ("Initial posting", "Resolution / censor", "First seen", "Last seen"): e[k] = parse_date(e[k])
snap = sorted({parse_date(r[1]) for r in list(wb["Snapshot Audit"].iter_rows(values_only=True))[4:] if r and r[1] and parse_date(r[1])})
first_snap, last_snap = snap[0], snap[-1]
def idx(d): return snap.index(d) if d in snap else None
def gap_before(d):
    i = idx(d); return (d - snap[i-1]).days if i else None
def gap_after(d):
    i = idx(d); return (snap[i+1] - d).days if i is not None and i+1 < len(snap) else None

by = collections.defaultdict(list)
for e in EP: by[e["Generic name"]].append(e)

out = []
for g, v in by.items():
    posting = min(x["Initial posting"] for x in v); fs = min(x["First seen"] for x in v); ls = max(x["Last seen"] for x in v)
    i0, i1 = idx(fs), idx(ls); expected = (i1 - i0 + 1) if (i0 is not None and i1 is not None) else None
    max_obs = max(x["Snapshots observed"] for x in v)
    absences = (expected - max_obs) if expected is not None else None
    resolved = [x for x in v if x["Event observed"]]
    res_date = min(x["Resolution / censor"] for x in resolved) if resolved else None
    # entry
    if posting >= first_snap and fs > first_snap: entry, entry_int = "OBSERVED (absent→current bracketed)", f"({snap[i0-1]}, {fs}]"
    elif posting >= first_snap and fs == first_snap: entry, entry_int = "LEFT-CENSORED (present at first snapshot)", f"[{posting}, {fs}]"
    else: entry, entry_int = "LEFT-CENSORED (pre-archive posting)", f"[{posting}, {fs}]"
    # exit
    if res_date: exit_, exit_int = "OBSERVED (Resolved mark)", f"({snap[idx(res_date)-1] if idx(res_date) else 'n/a'}, {res_date}]"
    elif ls < last_snap: exit_, exit_int = "INFERRED (disappeared without Resolved mark)", f"({ls}, {snap[i1+1] if i1 is not None and i1+1 < len(snap) else 'n/a'}]"
    else: exit_, exit_int = "ONGOING at last snapshot", f"[{last_snap}, —)"
    multi = "INFERRED (absent from ≥1 snapshot inside window)" if absences and absences > 0 else "none detected"
    # identifiable spell: observed entry AND (observed resolution or ongoing); inferred exit excluded; multi-spell drugs flagged
    ident = entry.startswith("OBSERVED") and (exit_.startswith("OBSERVED") or exit_.startswith("ONGOING")) and not (absences and absences > 0)
    ident_relaxed = entry.startswith("OBSERVED") and not (absences and absences > 0)   # allows inferred exit as censoring at last sight
    out.append({"generic": g, "ndcs": len(v), "drug_posting": posting.isoformat(), "first_seen": fs.isoformat(), "last_seen": ls.isoformat(),
                "window_snapshots_expected": expected, "max_snapshots_observed": max_obs, "snapshots_absent_inside_window": absences,
                "entry_status": entry, "entry_interval": entry_int, "entry_gap_days": gap_before(fs) if fs > first_snap else None,
                "exit_status": exit_, "exit_interval": exit_int, "exit_gap_days": gap_before(res_date) if res_date else (gap_after(ls) if ls < last_snap else None),
                "multiple_spells": multi, "posting_to_first_seen_days": (fs - posting).days,
                "original_episodes_preserved": len(v), "original_resolved_episodes": len(resolved),
                "identifiable_spell_strict": int(ident), "identifiable_spell_relaxed": int(ident_relaxed)})
with open("stage2b_audit/drug_spell_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

c = collections.Counter; n = len(out)
entry = c(o["entry_status"] for o in out); exit_ = c(o["exit_status"] for o in out); multi = c(o["multiple_spells"] for o in out)
obs_entry = [o for o in out if o["entry_status"].startswith("OBSERVED")]
obs_both = [o for o in obs_entry if o["exit_status"].startswith("OBSERVED")]
strict = sum(o["identifiable_spell_strict"] for o in out); relaxed = sum(o["identifiable_spell_relaxed"] for o in out)
eg = [o["entry_gap_days"] for o in obs_entry if o["entry_gap_days"]]; xg = [o["exit_gap_days"] for o in out if o["exit_gap_days"]]
big_gap = sum(1 for o in out if o["posting_to_first_seen_days"] > 365 and o["drug_posting"] >= first_snap.isoformat())
md = f"""# Spell identifiability summary (drug level, from deposited episode fields)

Drugs: {n} | episodes preserved: {sum(o['original_episodes_preserved'] for o in out)} | archive: {len(snap)} snapshots {first_snap}–{last_snap}

**Limit of this audit:** the raw snapshot CSVs are not in the deposit, so status is reconstructed from each NDC's first/last
sight and count of sightings. A full absent/current/resolved sequence per snapshot — and any current→resolved→current
recurrence — needs the 38 archived files (listed with Wayback URLs and hashes in the workbook's Snapshot Audit sheet).

## Entry (not-in-shortage → current)
{chr(10).join(f'- {k}: {v}' for k, v in entry.most_common())}

## Exit (current → resolved / disappearance)
{chr(10).join(f'- {k}: {v}' for k, v in exit_.most_common())}

## Multiple plausible spells
{chr(10).join(f'- {k}: {v}' for k, v in multi.most_common())}
(absence inside the window is INFERRED from sighting counts; FDA removes resolved listings after a retention period and a missed
capture can also produce an absence, so this is a flag for the raw-snapshot check, not a confirmed recurrence)

## Interval uncertainty from snapshot spacing
- Entry bracket (observed entries, n={len(eg)}): median {st.median(eg) if eg else 'n/a'} days, max {max(eg) if eg else 'n/a'}
- Exit bracket (n={len(xg)}): median {st.median(xg) if xg else 'n/a'} days, max {max(xg) if xg else 'n/a'}
- Drugs posted after archive start whose first sight lags posting by >365 days: {big_gap} (entry re-use / re-listing suspects)

## Identifiable independent spells — the sample size for the original question
| Definition | Drugs |
|---|---|
| Observed entry only | {len(obs_entry)} |
| Observed entry AND observed resolution | {len(obs_both)} |
| **Strict:** observed entry, observed resolution or ongoing, no internal absence | **{strict}** |
| Relaxed: observed entry, no internal absence (inferred disappearance treated as censoring at last sight) | {relaxed} |

Left-censored entries ({n - len(obs_entry)}) can contribute to prevalence/persistence descriptions but not to onset-anchored duration.
"""
open("stage2b_audit/spell_identifiability_summary.md", "w").write(md); print(md)
