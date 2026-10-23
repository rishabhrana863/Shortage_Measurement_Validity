#!/usr/bin/env python3
"""
Stage 1 join-feasibility audit: FDA shortage episodes (NDC9) -> NDC Directory -> Orange Book.

Usage:
  python -I stage1_join_audit.py \
      --episodes FDA_Recovery_Time_Validation.xlsx \
      --ndc  2020-01=ndc_2020/product.txt 2021-01=ndc_2021/product.txt ... current=ndc_now/product.txt \
      --ob   2020-01=ob_2020/products.txt ... current=ob_now/products.txt \
      --out  stage1_audit

Each --ndc / --ob entry is <snapshot-label>=<path>. Labels of the form YYYY-MM are treated as the
snapshot date; "current" is treated as today. For each episode the matcher uses the earliest snapshot
dated on/after the posting date (falling back to the nearest earlier one), so predictors are measured
with information that existed around posting, not 2026 information.

Outputs (in --out/):
  match_by_episode.csv      one row per episode with match flags and derived predictors
  audit_summary.md          coverage overall and by posting year / outcome / therapeutic category /
                            reason; unmatched-product profile; distribution of applicant counts
"""
import argparse, csv, io, os, re, sys, zipfile, collections, datetime as dt
import openpyxl

# ----------------------------------------------------------------------------- helpers
def clean(s):
    return str(s).replace("​", "").strip()

def ndc_variants(hyphenated):
    """All 9-digit forms a hyphenated product NDC (4-4, 5-3 or 5-4) could have been collapsed to.

    Returns {variant: config}. 'canon' = labeler zfill(5) + product zfill(4) (the 11-digit-style
    convention); 'leftpad' = digits concatenated then left-padded to 9 (a naive collapse). For 5-4
    products the two coincide. Episode NDC9s carry no record of which convention built them, so a
    directory product is indexed under every variant and the audit reports which one matched.
    """
    lab, prod = clean(hyphenated).split("-")[:2]
    cfg = f"{len(lab)}-{len(prod)}"
    out = {lab.zfill(5) + prod.zfill(4): f"canon:{cfg}"}
    lp = (lab + prod).zfill(9)
    out.setdefault(lp, f"leftpad:{cfg}")
    return out

def episode_ndc9(s):
    digits = re.sub(r"\D", "", clean(s))
    return digits.zfill(9)

def parse_date(x):
    if x is None or x == "":
        return None
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    s = str(x).strip()
    if s.lower().startswith("approved prior to"):
        return dt.date(1982, 1, 1)
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def open_table(path, delim):
    """Yield dict rows from a txt file or the first .txt inside a zip."""
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith((".txt", ".tsv")) and "product" in n.lower())
            raw = z.read(name)
    else:
        raw = open(path, "rb").read()
    text = raw.decode("utf-8", errors="replace")
    rdr = csv.DictReader(io.StringIO(text), delimiter=delim)
    for r in rdr:
        yield {k.strip().upper(): (v or "").strip() for k, v in r.items() if k}

def label_to_date(label):
    if label == "current":
        return dt.date.today()
    y, m = label.split("-")[:2]
    return dt.date(int(y), int(m), 1)

def pick_snapshot(snapshots, posting):
    """Earliest snapshot on/after posting; else the latest before it."""
    after = [s for s in snapshots if s[0] >= posting]
    if after:
        return min(after)
    return max(snapshots)

# ----------------------------------------------------------------------------- loaders
def load_episodes(xlsx):
    wb = openpyxl.load_workbook(xlsx, read_only=True)
    rows = list(wb["FDA Product Episodes"].iter_rows(values_only=True))
    hdr_i = next(i for i, r in enumerate(rows) if r and r[0] == "NDC9")
    H = rows[hdr_i]
    eps = []
    for r in rows[hdr_i + 1:]:
        if not r or not r[0]:
            continue
        d = dict(zip(H, r))
        d["ndc9"] = episode_ndc9(d["NDC9"])
        d["posting"] = parse_date(d["Initial posting"])
        eps.append(d)
    return eps

def load_ndc(path):
    """NDC Directory product file -> {ndc9_variant: [(config, row), ...]}.

    A product is indexed under every 9-digit form it could collapse to (see ndc_variants). More than one
    distinct product under the same key = ambiguous normalisation, reported in uncertain_matches.csv.
    Also returns a market index used for the participation proxy.
    """
    idx = collections.defaultdict(list)
    market = collections.defaultdict(list)   # (substance, form, route, strength) -> rows
    for r in open_table(path, "\t"):
        pn = r.get("PRODUCTNDC", "")
        if not pn or "-" not in pn:
            continue
        for v, cfg in ndc_variants(pn).items():
            idx[v].append((cfg, r))
        market[ndc_market_key(r)].append(r)
    return {"idx": idx, "market": market}

def ndc_market_key(r):
    return (r.get("SUBSTANCENAME", "").upper(), r.get("DOSAGEFORMNAME", "").upper(),
            r.get("ROUTENAME", "").upper(),
            re.sub(r"\s+", "", (r.get("ACTIVE_NUMERATOR_STRENGTH", "") + r.get("ACTIVE_INGRED_UNIT", "")).upper()))

def name_overlap(a, b):
    """Crude check that the episode generic name and directory nonproprietary name share a token."""
    ta = {t for t in re.findall(r"[a-z]{4,}", a.lower())}
    tb = {t for t in re.findall(r"[a-z]{4,}", b.lower())}
    return bool(ta & tb)

def load_ob(path):
    """Orange Book products.txt (delimiter '~') -> list of rows with parsed approval dates."""
    rows = []
    for r in open_table(path, "~"):
        r["_approval"] = parse_date(r.get("APPROVAL_DATE", ""))
        rows.append(r)
    return rows

def market_key(ingredient, df_route, strength):
    return (ingredient.upper().strip(), df_route.upper().strip(), re.sub(r"\s+", "", strength.upper()))

def ob_index(ob_rows):
    """market_key -> list of (applicant, approval_date, type, appl_no)."""
    idx = collections.defaultdict(list)
    for r in ob_rows:
        k = market_key(r.get("INGREDIENT", ""), r.get("DF;ROUTE", ""), r.get("STRENGTH", ""))
        idx[k].append((r.get("APPLICANT", ""), r["_approval"], r.get("TYPE", ""), r.get("APPL_NO", "")))
    return idx

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--ndc", nargs="+", required=True, help="label=path pairs")
    ap.add_argument("--ob", nargs="+", required=True, help="label=path pairs")
    ap.add_argument("--out", default="stage1_audit")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    eps = load_episodes(a.episodes)
    ndc_snaps = sorted((label_to_date(l), load_ndc(p)) for l, p in (x.split("=", 1) for x in a.ndc))
    ob_snaps = sorted((label_to_date(l), ob_index(load_ob(p))) for l, p in (x.split("=", 1) for x in a.ob))
    print(f"episodes={len(eps)}  ndc snapshots={[d.isoformat() for d,_ in ndc_snaps]}  ob snapshots={[d.isoformat() for d,_ in ob_snaps]}")

    # provenance log: inputs, hashes, mtimes, run time
    import hashlib
    prov = [f"run_utc={dt.datetime.now(dt.timezone.utc).isoformat()}", f"episodes={a.episodes}"]
    for lbl_path in a.ndc + a.ob:
        lbl, p = lbl_path.split("=", 1)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        prov.append(f"{lbl}\t{p}\tsha256={h}\tmtime={dt.datetime.fromtimestamp(os.path.getmtime(p)).isoformat()}")
    open(os.path.join(a.out, "provenance.log"), "w").write("\n".join(prov) + "\n")

    # Orange Book appl_no -> market key, per snapshot (built once)
    ob_appl_index = []
    for d, obidx in ob_snaps:
        m = {}
        for k, lst in obidx.items():
            for x in lst:
                m.setdefault(re.sub(r"\D", "", x[3]), k)
        ob_appl_index.append((d, m))

    rows_out, uncertain = [], []
    def flag(e, kind, detail):
        uncertain.append({"ndc9": e["ndc9"], "generic": e["Generic name"], "posting": e["posting"].isoformat(),
                          "issue": kind, "detail": detail})

    for e in eps:
        snap_date, ndc = pick_snapshot(ndc_snaps, e["posting"])
        hits = ndc["idx"].get(e["ndc9"], [])
        # de-duplicate by PRODUCTNDC (a 5-4 product appears under one key twice with the same row)
        seen, uniq = set(), []
        for cfg, r in hits:
            if r["PRODUCTNDC"] not in seen:
                seen.add(r["PRODUCTNDC"]); uniq.append((cfg, r))
        o = {
            "ndc9": e["ndc9"], "generic": e["Generic name"], "posting": e["posting"].isoformat(),
            "posting_year": e["posting"].year, "outcome": e["Censoring status"], "duration": e["Duration days"],
            "reason": e["Shortage reason"], "ther_cat": e["Therapeutic category"],
            "posted_before_first_archive": int(e["posting"] < dt.date(2019, 12, 29)),
            "ndc_snapshot": snap_date.isoformat(), "ndc_matched": int(bool(uniq)),
            "ndc_candidates": len(uniq),
        }
        rec = None
        if len(uniq) > 1:
            # ambiguous normalisation: prefer the candidate whose nonproprietary name overlaps the episode generic
            good = [(c, r) for c, r in uniq if name_overlap(e["Generic name"], r.get("NONPROPRIETARYNAME", ""))]
            flag(e, "ambiguous_ndc_normalisation",
                 "; ".join(f"{r['PRODUCTNDC']} [{c}] {r.get('NONPROPRIETARYNAME','')[:40]}" for c, r in uniq))
            if len(good) == 1:
                rec = good[0][1]; o["ndc_match_config"] = good[0][0]; o["ndc_match_resolved_by"] = "name"
            else:
                o["ndc_matched"] = 0; o["ndc_match_resolved_by"] = "unresolved"
        elif uniq:
            rec = uniq[0][1]; o["ndc_match_config"] = uniq[0][0]; o["ndc_match_resolved_by"] = "unique"
            if not name_overlap(e["Generic name"], rec.get("NONPROPRIETARYNAME", "")):
                flag(e, "name_conflict", f"episode='{e['Generic name'][:50]}' directory='{rec.get('NONPROPRIETARYNAME','')[:50]}' ({rec['PRODUCTNDC']})")
                o["ndc_name_conflict"] = 1
        else:
            flag(e, "unmatched_ndc", "no directory product under any 9-digit variant in the chosen snapshot")

        if rec:
            start, end = parse_date(rec.get("STARTMARKETINGDATE")), parse_date(rec.get("ENDMARKETINGDATE"))
            hist_status_known = snap_date <= e["posting"] + dt.timedelta(days=90)   # snapshot near posting?
            o.update({
                "ndc_productndc": rec.get("PRODUCTNDC"),
                "ndc_dosage_form": rec.get("DOSAGEFORMNAME"), "ndc_route": rec.get("ROUTENAME"),
                "ndc_marketing_cat": rec.get("MARKETINGCATEGORYNAME"), "ndc_appl_no": rec.get("APPLICATIONNUMBER"),
                "ndc_labeler": rec.get("LABELERNAME"), "ndc_dea": rec.get("DEASCHEDULE"),
                "ndc_substance": rec.get("SUBSTANCENAME"),
                "ndc_start_mkt": start.isoformat() if start else "", "ndc_end_mkt": end.isoformat() if end else "",
                "ndc_marketed_at_posting": int((start is None or start <= e["posting"]) and (end is None or end >= e["posting"])),
                "ndc_historical_status_known": int(hist_status_known),
            })
            if not hist_status_known:
                flag(e, "missing_historical_marketing_status",
                     f"nearest directory snapshot {snap_date} is >90 days after posting; marketed-at-posting is a current-file inference")

            # --- participation proxy from the NDC Directory market (labelers with a product marketed at posting)
            mk = ndc_market_key(rec)
            peers = ndc["market"].get(mk, [])
            active = [p for p in peers
                      if (parse_date(p.get("STARTMARKETINGDATE")) or dt.date.min) <= e["posting"]
                      and (parse_date(p.get("ENDMARKETINGDATE")) or dt.date.max) >= e["posting"]]
            o.update({
                "ndc_market": " | ".join(mk),
                "part_labelers_marketed_at_posting": len({p.get("LABELERNAME") for p in active}),
                "part_products_marketed_at_posting": len(active),
                "part_proxy_basis": "historical" if hist_status_known else "current_file",
            })

            # --- approval-based count from the Orange Book (approved on/before posting; NOT participation)
            ob_date, appl_map = pick_snapshot(ob_appl_index, e["posting"])
            obidx = dict(ob_snaps)[ob_date]
            appl = re.sub(r"\D", "", rec.get("APPLICATIONNUMBER", ""))
            key = appl_map.get(appl) if appl else None
            if key:
                lst = obidx[key]
                before = [x for x in lst if x[1] and x[1] <= e["posting"]]
                o.update({
                    "ob_matched": 1, "ob_snapshot": ob_date.isoformat(), "ob_market": " | ".join(key),
                    "ob_applicants_approved_by_posting": len({x[0] for x in before}),
                    "ob_applicants_approved_not_discn": len({x[0] for x in before if x[2].upper() != "DISCN"}),
                    "ob_products_approved_by_posting": len(before),
                    "ob_first_approval": min((x[1] for x in before), default=None),
                })
            else:
                o["ob_matched"] = 0
                flag(e, "unmatched_application",
                     f"appl '{rec.get('APPLICATIONNUMBER','')}' ({rec.get('MARKETINGCATEGORYNAME','')}) not in Orange Book snapshot {ob_date}"
                     + (" — expected: OB covers NDA/ANDA only" if not re.match(r"^(NDA|ANDA)", rec.get("APPLICATIONNUMBER", "")) else ""))
        rows_out.append(o)

    with open(os.path.join(a.out, "uncertain_matches.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ndc9", "generic", "posting", "issue", "detail"]); w.writeheader(); w.writerows(uncertain)

    # ------------------------------------------------------------------ write episode-level file
    keys = sorted({k for r in rows_out for k in r})
    with open(os.path.join(a.out, "match_by_episode.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows_out)

    # ------------------------------------------------------------------ summary
    def rate(rows, flag):
        n = len(rows); m = sum(int(r.get(flag, 0) or 0) for r in rows)
        return f"{m}/{n} ({100*m/n:.1f}%)" if n else "0/0"
    def by(field, flag):
        g = collections.defaultdict(list)
        for r in rows_out: g[r[field]].append(r)
        return "\n".join(f"| {k} | {rate(v, flag)} |" for k, v in sorted(g.items(), key=lambda kv: str(kv[0])))

    drugs = collections.defaultdict(list)
    for r in rows_out: drugs[r["generic"]].append(r)
    drug_any = sum(1 for v in drugs.values() if any(x["ndc_matched"] for x in v))
    drug_ob = sum(1 for v in drugs.values() if any(x.get("ob_matched") for x in v))

    um = [r for r in rows_out if not r["ndc_matched"]]
    um_reason = collections.Counter(r["reason"] for r in um).most_common(8)
    um_year = collections.Counter(r["posting_year"] for r in um)
    um_outcome = collections.Counter(r["outcome"] for r in um)
    um_cat = collections.Counter(t.strip() for r in um for t in r["ther_cat"].split(";")).most_common(8)
    um_prearchive = sum(r["posted_before_first_archive"] for r in um)

    issues = collections.Counter(u["issue"] for u in uncertain)
    matched = [r for r in rows_out if r["ndc_matched"]]
    cfg_dist = collections.Counter(r.get("ndc_match_config") for r in matched)
    part_dist = collections.Counter(r.get("part_labelers_marketed_at_posting") for r in matched)
    basis = collections.Counter(r.get("part_proxy_basis") for r in matched)
    appl_dist = collections.Counter(r.get("ob_applicants_approved_by_posting") for r in rows_out if r.get("ob_matched"))

    md = f"""# Stage 1 join audit — technical feasibility

Episodes: {len(rows_out)} | drugs (generic names): {len(drugs)} | posted before first archive snapshot: {sum(r['posted_before_first_archive'] for r in rows_out)}

Scope: this run tests whether the join *works*. Predictor values derived from current-dated files are not
historically validated (see "basis" below) and must not be reported as predictors until dated snapshots are used.

## Coverage
| Level | NDC Directory match | Orange Book application match |
|---|---|---|
| Episode | {rate(rows_out, 'ndc_matched')} | {rate(rows_out, 'ob_matched')} |
| Drug (any NDC matched) | {drug_any}/{len(drugs)} | {drug_ob}/{len(drugs)} |
| Matched & marketed on posting date | {rate(matched, 'ndc_marketed_at_posting')} | — |
| Matched with historical status known (snapshot within 90 d of posting) | {rate(matched, 'ndc_historical_status_known')} | — |

## How matches were made (segment configuration)
{dict(cfg_dist)}

## Matching diagnostics (uncertain_matches.csv)
{dict(issues)}

## NDC match by posting year
| Year | Matched |
|---|---|
{by('posting_year', 'ndc_matched')}

## NDC match by outcome
| Outcome | Matched |
|---|---|
{by('outcome', 'ndc_matched')}

## NDC match by pre-archive posting
| Posted before 2019-12-29 | Matched |
|---|---|
{by('posted_before_first_archive', 'ndc_matched')}

## Unmatched-episode profile (n={len(um)})
- by year: {dict(sorted(um_year.items()))}
- by outcome: {dict(um_outcome)}
- posted before first archive: {um_prearchive}
- top reasons: {um_reason}
- top therapeutic categories: {um_cat}

## Supplier-concentration proxies, matched episodes
Labelers with a product marketed on the posting date (NDC Directory market: substance/form/route/strength):
{dict(sorted(part_dist.items(), key=lambda kv: (kv[0] is None, kv[0])))}
Basis of that count: {dict(basis)}  ("current_file" = inferred from current marketing dates, not historical evidence)

Applicants approved on/before posting (Orange Book) — an *approval* count, not participation:
{dict(sorted(appl_dist.items(), key=lambda kv: (kv[0] is None, kv[0])))}

## Caveats
- Labeler/applicant counts are market-participation / supplier-concentration proxies, not independent
  manufacturers: contract manufacturing and repackaging inflate them.
- Approval date says when a product was approved, not whether its applicant was supplying the market at posting.
- The current NDC Directory omits products past their marketing end date, so current-file participation
  counts are biased toward survivors; dated snapshots are required before any count is called a predictor.
- Episodes posted before the first archive snapshot were observed retrospectively and need separate treatment
  (selection into the archive and timing of first observation), not ordinary delayed entry.
"""
    open(os.path.join(a.out, "audit_summary.md"), "w").write(md)
    print(md)

if __name__ == "__main__":
    main()
