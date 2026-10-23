#!/usr/bin/env python3
"""
Stage 1b: excluded-products recovery audit.

Preserves every match from Stage 1 (match_by_episode.csv) and tests whether the FDA NDC
"excluded products" file recovers previously unmatched episodes. Nothing from Stage 1 is overwritten.

Usage:
  python -I stage1b_excluded_recovery.py --stage1 stage1_audit/match_by_episode.csv \
      --episodes FDA_Recovery_Time_Validation.xlsx --excluded <products_excluded.txt or .zip> \
      --ob <orange book products.txt> --out stage1b_audit

Outputs:
  recovered_matches.csv   one row per previously unmatched episode: recovered? exclusion flag,
                          marketing start/end, application match, identity confidence, consistency checks
  recovery_audit.md       the recovery table against the Stage 1 baseline, by exclusion flag,
                          by shortage reason, by posting year; drug-level recovery; consistency flags
"""
import argparse, csv, os, re, collections, datetime as dt, hashlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_join_audit import (load_episodes, open_table, ndc_variants, name_overlap, parse_date,
                               load_ob, ob_index)

def load_excluded(path):
    idx = collections.defaultdict(list)
    n = 0
    for r in open_table(path, "\t"):
        pn = r.get("PRODUCTNDC", "")
        if not pn or "-" not in pn:
            continue
        n += 1
        for v, cfg in ndc_variants(pn).items():
            idx[v].append((cfg, r))
    return idx, n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1", required=True); ap.add_argument("--episodes", required=True)
    ap.add_argument("--excluded", required=True); ap.add_argument("--ob", required=True)
    ap.add_argument("--out", default="stage1b_audit")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)

    s1 = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open(a.stage1))}
    eps = load_episodes(a.episodes)
    exc, n_exc = load_excluded(a.excluded)
    obidx = ob_index(load_ob(a.ob))
    appl_map = {}
    for k, lst in obidx.items():
        for x in lst:
            appl_map.setdefault(re.sub(r"\D", "", x[3]), k)   # k[0] is the Orange Book ingredient

    def identity(ep_name, r):
        """Excluded listings carry only PROPRIETARYNAME; check it, then the Orange Book ingredient via appl no."""
        if name_overlap(ep_name, r.get("PROPRIETARYNAME", "")):
            return "high_brand_name"
        ap = re.sub(r"\D", "", r.get("APPLICATIONNUMBER", ""))
        if ap and ap in appl_map and name_overlap(ep_name, appl_map[ap][0]):
            return "high_ob_ingredient"
        if ap and ap in appl_map:
            return "low_conflict_ob_ingredient:" + appl_map[ap][0][:40]
        return "unverifiable_no_application"

    prov = [f"run_utc={dt.datetime.now(dt.timezone.utc).isoformat()}",
            f"excluded\t{a.excluded}\tsha256={hashlib.sha256(open(a.excluded,'rb').read()).hexdigest()}"
            f"\tmtime={dt.datetime.fromtimestamp(os.path.getmtime(a.excluded)).isoformat()}",
            f"excluded_rows={n_exc}"]
    open(os.path.join(a.out, "provenance.log"), "w").write("\n".join(prov) + "\n")

    base_unmatched = [e for e in eps if s1[e["ndc9"] + "|" + e["posting"].isoformat()]["ndc_matched"] == "0"]
    out = []
    for e in base_unmatched:
        hits = exc.get(e["ndc9"], [])
        seen, uniq = set(), []
        for cfg, r in hits:
            if r["PRODUCTNDC"] not in seen:
                seen.add(r["PRODUCTNDC"]); uniq.append((cfg, r))
        o = {"ndc9": e["ndc9"], "generic": e["Generic name"], "posting": e["posting"].isoformat(),
             "posting_year": e["posting"].year, "outcome": e["Censoring status"], "duration": e["Duration days"],
             "reason": e["Shortage reason"], "pre_archive": int(e["posting"] < dt.date(2019, 12, 29)),
             "recovered": 0, "candidates": len(uniq)}
        rec = None
        good = [(c, r) for c, r in uniq if identity(e["Generic name"], r).startswith("high")]
        if len(uniq) == 1:
            rec = uniq[0][1]; o["match_config"] = uniq[0][0]
            o["identity_confidence"] = identity(e["Generic name"], rec)
        elif len(good) == 1:
            rec = good[0][1]; o["match_config"] = good[0][0]; o["identity_confidence"] = "medium_resolved_by_name"
        elif uniq:
            o["identity_confidence"] = "unresolved_ambiguous"
            o["candidate_list"] = "; ".join(f"{r['PRODUCTNDC']}[{c}] {r.get('NONPROPRIETARYNAME','')[:30]}" for c, r in uniq)
        if rec:
            start, end = parse_date(rec.get("STARTMARKETINGDATE")), parse_date(rec.get("ENDMARKETINGDATE"))
            appl = re.sub(r"\D", "", rec.get("APPLICATIONNUMBER", ""))
            o.update({
                "recovered": 1, "productndc": rec["PRODUCTNDC"],
                "exclude_flag": rec.get("NDC_EXCLUDE_FLAG", ""), "proprietary": rec.get("PROPRIETARYNAME", "")[:60],
                "ob_ingredient": appl_map.get(re.sub(r"\D", "", rec.get("APPLICATIONNUMBER", "")), ("",))[0][:60],
                "dosage_form": rec.get("DOSAGEFORMNAME", ""), "route": rec.get("ROUTENAME", ""),
                "marketing_cat": rec.get("MARKETINGCATEGORYNAME", ""), "appl_no": rec.get("APPLICATIONNUMBER", ""),
                "labeler": rec.get("LABELERNAME", ""), "substance": rec.get("SUBSTANCENAME", "")[:60],
                "start_mkt": start.isoformat() if start else "", "end_mkt": end.isoformat() if end else "",
                "certified_through": rec.get("LISTING_RECORD_CERTIFIED_THROUGH", ""),
                "ob_application_match": int(bool(appl and appl in appl_map)),
                # consistency checks between exclusion record and the shortage episode
                "marketed_at_posting": int((start is None or start <= e["posting"]) and (end is None or end >= e["posting"])),
                "end_before_posting": int(bool(end and end < e["posting"])),
                "end_during_episode": int(bool(end and end >= e["posting"] and
                                               end <= e["posting"] + dt.timedelta(days=int(e["Duration days"])))),
                "end_after_resolution_or_censor": int(bool(end and end > e["posting"] + dt.timedelta(days=int(e["Duration days"])))),
            })
        out.append(o)

    keys = sorted({k for r in out for k in r})
    with open(os.path.join(a.out, "recovered_matches.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)

    rec = [r for r in out if r["recovered"]]
    disc = [r for r in out if r["reason"].startswith("Discontinuation")]
    # drug-level: which of the 41 zero-match drugs gain a match
    drugs_s1 = collections.defaultdict(int)
    for r in s1.values(): drugs_s1[r["generic"]] += int(r["ndc_matched"])
    zero_drugs = {g for g, n in drugs_s1.items() if n == 0}
    zero_recovered = {r["generic"] for r in rec if r["generic"] in zero_drugs}
    def cnt(rows, key): return dict(collections.Counter(r.get(key, "") for r in rows).most_common())
    def tbl(rows, key, denom_rows):
        g = collections.defaultdict(lambda: [0, 0])
        for r in denom_rows: g[r[key]][1] += 1
        for r in rows: g[r[key]][0] += 1
        return "\n".join(f"| {k} | {v[0]}/{v[1]} |" for k, v in sorted(g.items(), key=lambda kv: str(kv[0])))

    md = f"""# Stage 1b — excluded-products recovery audit

Excluded file rows indexed: {n_exc}. Stage 1 matches preserved untouched.

## Recovery against baseline
| Measure | Baseline | After excluded file |
|---|---|---|
| Previously unmatched episodes | {len(base_unmatched)} | {len(base_unmatched) - len(rec)} still unmatched ({len(rec)} recovered) |
| Discontinuation-reason episodes unmatched | {len(disc)} of 40 | {len(disc) - sum(r['recovered'] for r in disc)} of 40 ({sum(r['recovered'] for r in disc)} recovered) |
| Drugs without any NDC match | {len(zero_drugs)} of 298 | {len(zero_drugs) - len(zero_recovered)} of 298 ({len(zero_recovered)} recovered) |
| Historically verified matches | 0 | 0 (excluded records are retrospective listings, not dated observations) |
| Combined episode coverage | 1534/2042 | {1534 + len(rec)}/2042 ({100*(1534+len(rec))/2042:.1f}%) |

## Recovered episodes by exclusion flag (D=discontinued by firm, U=expired certification, E=listing deficiency, I=FDA inactivation)
{cnt(rec, 'exclude_flag')}

## Identity confidence of recovered matches
{cnt(rec, 'identity_confidence')}

Note: the excluded-products file carries PROPRIETARYNAME only (nonproprietary name, substance, dosage form and
route are blank in all rows), so identity is checked against the brand name and, via the application number,
the Orange Book ingredient. Recovered rows cannot feed the substance/form/route participation proxy.

## Recovery by shortage reason (recovered / previously unmatched)
| Reason | Recovered |
|---|---|
{tbl(rec, 'reason', out)}

## Recovery by posting year
| Year | Recovered |
|---|---|
{tbl(rec, 'posting_year', out)}

## Consistency between exclusion record and shortage episode (recovered rows)
| Check | Count |
|---|---|
| Marketing end date before posting | {sum(r['end_before_posting'] for r in rec)} |
| Marketing end date during the episode | {sum(r['end_during_episode'] for r in rec)} |
| Marketing end date after resolution/censor | {sum(r['end_after_resolution_or_censor'] for r in rec)} |
| No end date recorded | {sum(1 for r in rec if not r['end_mkt'])} |
| Orange Book application match | {sum(r['ob_application_match'] for r in rec)} |
| Marketing category | {cnt(rec, 'marketing_cat')} |

## Still unmatched after recovery
{len(base_unmatched) - len(rec)} episodes; by reason: {cnt([r for r in out if not r['recovered']], 'reason')}

## Reading the result
- A "D" flag with an end date during or after the episode is consistent with a product withdrawn in the shortage
  — retrospective evidence of disposition, not proof the firm was observed participating in 2020–2023.
- An end date *before* posting means the excluded listing cannot be the product that was in shortage as posted,
  or the episode's NDC was reused; treat as identity-uncertain.
- "U/E/I" flags are administrative, not market exits; they say nothing about discontinuation.
- The shortage-reason label "discontinuation" and the exclusion flag "D" are two independent signals; the
  competing-event disposition for Stage 4 should require both, or an archive observation.
"""
    open(os.path.join(a.out, "recovery_audit.md"), "w").write(md); print(md)

if __name__ == "__main__":
    main()
