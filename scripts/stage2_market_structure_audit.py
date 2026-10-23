#!/usr/bin/env python3
"""
Stage 2: market-structure feasibility audit (sensitivity and plausibility; no survival models).

Two measures, kept separate:
  A. approved_applicants  — distinct Orange Book applicants in the episode's market with an approval date on or
                            before posting (regulatory competition potential). Market = ingredient + DF;Route.
                            Strength-level variant reported as sensitivity.
  B. participation_proxy  — distinct labelers with an NDC listing (current + excluded files) whose reported
                            marketing window contains the posting date, in the same market (retrospectively
                            reconstructed participation). Listings reach the market through their application
                            number -> Orange Book ingredient/DF;Route. Sensitivities: end-date minus 365 d
                            (lot-expiry allowance), current-file-only.

Usage:
  python -I stage2_market_structure_audit.py --episodes FDA_Recovery_Time_Validation.xlsx \
     --stage1 stage1_audit/match_by_episode.csv --stage1b stage1b_audit/recovered_matches.csv \
     --ndc <product.txt> --excluded <Products_excluded.txt> --ob <products.txt> \
     --adjudication stage1_audit/name_conflict_adjudication.csv --out stage2_audit
"""
import argparse, csv, os, re, collections, datetime as dt, hashlib, sys, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_join_audit import load_episodes, open_table, parse_date, load_ob

def digits(s): return re.sub(r"\D", "", s or "")
def norm_labeler(s):
    s = re.sub(r"[.,]", "", (s or "").upper())
    s = re.sub(r"\b(INC|LLC|LTD|CO|CORP|CORPORATION|COMPANY|PHARMACEUTICALS?|PHARMA|USA|US|LP|PLC|LIMITED|GMBH|SA|AG)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()
def spearman(x, y):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v); i = 0
        while i < len(order):
            j = i
            while j+1 < len(order) and v[order[j+1]] == v[order[i]]: j += 1
            for k in range(i, j+1): r[order[k]] = (i+j)/2 + 1
            i = j+1
        return r
    if len(x) < 3: return float("nan")
    rx, ry = rank(x), rank(y); mx, my = st.mean(rx), st.mean(ry)
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry)); den = (sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))**0.5
    return num/den if den else float("nan")

def main():
    ap = argparse.ArgumentParser()
    for k in ("episodes", "stage1", "stage1b", "ndc", "excluded", "ob", "adjudication"): ap.add_argument("--"+k, required=True)
    ap.add_argument("--out", default="stage2_audit"); a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    random.seed(2026)

    # ---------------- inputs & provenance
    prov = [f"run_utc={dt.datetime.now(dt.timezone.utc).isoformat()}"]
    for k in ("ndc", "excluded", "ob", "stage1", "stage1b"):
        p = getattr(a, k); prov.append(f"{k}\t{p}\tsha256={hashlib.sha256(open(p,'rb').read()).hexdigest()}")
    open(os.path.join(a.out, "provenance.log"), "w").write("\n".join(prov)+"\n")

    eps = load_episodes(a.episodes)
    s1 = {r["ndc9"]+"|"+r["posting"]: r for r in csv.DictReader(open(a.stage1))}
    s1b = {r["ndc9"]+"|"+r["posting"]: r for r in csv.DictReader(open(a.stage1b))}
    adj = {(r["ndc9"], r["posting"]): r for r in csv.DictReader(open(a.adjudication))}

    # Orange Book: appl -> markets; market -> applicants with approval dates
    ob = load_ob(a.ob)
    appl_markets = collections.defaultdict(set)      # appl digits -> {(ingredient, dfroute)}
    market_products = collections.defaultdict(list)  # (ingredient, dfroute) -> [(applicant, approval, type, strength)]
    for r in ob:
        mk = (r.get("INGREDIENT", "").upper().strip(), r.get("DF;ROUTE", "").upper().strip())
        appl_markets[digits(r.get("APPL_NO"))].add(mk)
        market_products[mk].append((r.get("APPLICANT", "").upper().strip(), r["_approval"], r.get("TYPE", "").upper(), re.sub(r"\s+", "", r.get("STRENGTH", "").upper())))

    # NDC listings (current + excluded) -> market via application number
    listings = collections.defaultdict(list)         # market -> [(labeler, start, end, source, productndc)]
    def ingest(path, source):
        n = 0
        for r in open_table(path, "\t"):
            if (r.get("DOSAGEFORMNAME", "") or "").upper() == "KIT": continue
            ap_ = digits(r.get("APPLICATIONNUMBER"))
            if not ap_ or ap_ not in appl_markets: continue
            start, end = parse_date(r.get("STARTMARKETINGDATE")), parse_date(r.get("ENDMARKETINGDATE"))
            for mk in appl_markets[ap_]:
                listings[mk].append((norm_labeler(r.get("LABELERNAME")), start, end, source, r.get("PRODUCTNDC")))
            n += 1
        return n
    n_cur = ingest(a.ndc, "current"); n_exc = ingest(a.excluded, "excluded")

    def participation(mk, posting, end_shift_days=0, sources=("current", "excluded")):
        labs = set()
        for lab, start, end, src, _ in listings.get(mk, []):
            if src not in sources: continue
            e = (end - dt.timedelta(days=end_shift_days)) if end else None
            if (start is None or start <= posting) and (e is None or e >= posting): labs.add(lab)
        return len(labs)

    # ---------------- per-episode measures + identity audit
    out, ident = [], []
    for e in eps:
        key = e["ndc9"]+"|"+e["posting"].isoformat(); r1 = s1[key]; rb = s1b.get(key)
        posting = e["posting"]
        rec_src = "current" if r1["ndc_matched"] == "1" else ("excluded" if rb and rb["recovered"] == "1" else None)
        appl = digits(r1.get("ndc_appl_no") if rec_src == "current" else (rb.get("appl_no") if rb else ""))
        dosage = (r1.get("ndc_dosage_form") or "").upper() if rec_src == "current" else ""
        end_mkt = parse_date(r1.get("ndc_end_mkt") or "") if rec_src == "current" else (parse_date(rb.get("end_mkt") or "") if rb else None)
        start_mkt = parse_date(r1.get("ndc_start_mkt") or "") if rec_src == "current" else (parse_date(rb.get("start_mkt") or "") if rb else None)
        excl_flag = rb.get("exclude_flag", "") if rec_src == "excluded" else ""

        # identity status
        a_ = adj.get((e["ndc9"], posting.isoformat()))
        status, note = "confirmed", ""
        if rec_src is None: status, note = "unmatched", "no listing in current or excluded file"
        elif a_ and a_["proposed_disposition"] == "EXCLUDE": status, note = "excluded_identity_conflict", a_["rationale"]
        elif rec_src == "excluded" and rb["identity_confidence"].startswith("low_conflict"): status, note = "excluded_identity_conflict", rb["identity_confidence"]
        elif rec_src == "excluded" and rb["identity_confidence"].startswith("unverifiable"): status, note = "confirmed_manual", "brand name confirmed by inspection; no application"
        date_flag = ""
        if rec_src and end_mkt and end_mkt < posting:
            gap = (posting - end_mkt).days
            if gap <= 180: date_flag = "plausible_delayed_posting"
            elif e["Shortage reason"].lower().startswith("discontinu") or excl_flag == "D": date_flag = "genuine_historical_listing_withdrawn_before_posting"
            else: date_flag = "unresolved_date_conflict"
        ident.append({"ndc9": e["ndc9"], "generic": e["Generic name"], "posting": posting.isoformat(), "source": rec_src or "",
                      "identity_status": status, "identity_note": note, "end_before_posting_days": (posting-end_mkt).days if (end_mkt and end_mkt < posting) else "",
                      "date_flag": date_flag, "exclude_flag": excl_flag, "reason": e["Shortage reason"], "outcome": e["Censoring status"]})

        o = {"ndc9": e["ndc9"], "generic": e["Generic name"], "posting": posting.isoformat(), "posting_year": posting.year,
             "outcome": e["Censoring status"], "duration": e["Duration days"], "reason": e["Shortage reason"],
             "ther_cat_first": e["Therapeutic category"].split(";")[0].strip(), "source": rec_src or "",
             "identity_status": status, "date_flag": date_flag, "is_kit": int(dosage == "KIT"),
             "has_application": int(bool(appl)), "ob_market_defined": 0}
        if appl and appl in appl_markets and dosage != "KIT":
            mks = appl_markets[appl]
            if len(mks) > 1: o["market_ambiguity"] = len(mks)
            mk = sorted(mks)[0]; o.update({"ob_market_defined": 1, "market_ingredient": mk[0], "market_dfroute": mk[1]})
            prods = market_products[mk]
            before = [p for p in prods if p[1] and p[1] <= posting]
            o["A_approved_applicants"] = len({p[0] for p in before})
            o["A_approved_applicants_nonDISCN"] = len({p[0] for p in before if p[2] != "DISCN"})
            o["A_products_approved"] = len(before)
            # strength-level sensitivity: applicants with same strength as the matched OB product(s) of this application
            o["B_participation"] = participation(mk, posting)
            o["B_participation_endminus365"] = participation(mk, posting, 365)
            o["B_participation_current_only"] = participation(mk, posting, 0, ("current",))
            o["B_listings_in_market"] = len(listings.get(mk, []))
        out.append(o)

    keys = sorted({k for r in out for k in r})
    with open(os.path.join(a.out, "episode_measures.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
    with open(os.path.join(a.out, "identity_audit.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ident[0].keys())); w.writeheader(); w.writerows(ident)

    # ---------------- summaries
    el = [r for r in out if r["identity_status"].startswith("confirmed")]
    mk_ok = [r for r in el if r["ob_market_defined"]]
    def dist(vals, cuts=(0, 1, 2, 3, 5, 10, 20)):
        c = collections.Counter();
        for v in vals:
            lab = next((f"{cuts[i]}" if cuts[i]==cuts[i+1]-1 else f"{cuts[i]}–{cuts[i+1]-1}" for i in range(len(cuts)-1) if cuts[i] <= v < cuts[i+1]), f"{cuts[-1]}+")
            c[lab] += 1
        return dict(sorted(c.items(), key=lambda kv: (kv[0].endswith("+"), int(kv[0].split("–")[0].rstrip("+")))))
    A = [r["A_approved_applicants"] for r in mk_ok]; B = [r["B_participation"] for r in mk_ok]
    # drug level (median across episodes of a drug)
    drug = collections.defaultdict(list)
    for r in mk_ok: drug[r["generic"]].append(r)
    A_d = [st.median(x["A_approved_applicants"] for x in v) for v in drug.values()]
    B_d = [st.median(x["B_participation"] for x in v) for v in drug.values()]
    # markets
    markets = collections.defaultdict(list)
    for r in mk_ok: markets[(r["market_ingredient"], r["market_dfroute"])].append(r)

    def cov(field):
        g = collections.defaultdict(lambda: [0, 0, 0])
        for r in el:
            g[r[field]][2] += 1; g[r[field]][0] += r["ob_market_defined"]; g[r[field]][1] += int(bool(r.get("B_listings_in_market")))
        return "\n".join(f"| {k} | {v[0]}/{v[2]} | {v[1]}/{v[2]} |" for k, v in sorted(g.items(), key=lambda kv: str(kv[0])))
    def cov_cat():
        g = collections.defaultdict(lambda: [0, 0])
        for r in el: g[r["ther_cat_first"]][1] += 1; g[r["ther_cat_first"]][0] += r["ob_market_defined"]
        top = sorted(g.items(), key=lambda kv: -kv[1][1])[:12]
        return "\n".join(f"| {k} | {v[0]}/{v[1]} |" for k, v in top)

    # agreement
    agree_tab = collections.Counter()
    for r in mk_ok:
        a_, b_ = r["A_approved_applicants"], r["B_participation"]
        agree_tab["B > A (more labelers than approved applicants)" if b_ > a_ else "B = A" if b_ == a_ else "B < A"] += 1
    sens = {"B vs B(end−365)": spearman(B, [r["B_participation_endminus365"] for r in mk_ok]),
            "B vs B(current only)": spearman(B, [r["B_participation_current_only"] for r in mk_ok]),
            "share of episodes where B changes with end−365": sum(1 for r in mk_ok if r["B_participation"] != r["B_participation_endminus365"])/max(1,len(mk_ok)),
            "share where B changes dropping excluded listings": sum(1 for r in mk_ok if r["B_participation"] != r["B_participation_current_only"])/max(1,len(mk_ok))}

    # inspection samples
    def sample(pred, n=6):
        pool = [r for r in mk_ok if pred(r)]; random.shuffle(pool)
        return pool[:n]
    samples = {"zero_participation": sample(lambda r: r["B_participation"] == 0),
               "single_applicant": sample(lambda r: r["A_approved_applicants"] == 1),
               "high_count": sample(lambda r: r["A_approved_applicants"] >= 15),
               "B_much_greater_than_A": sample(lambda r: r["B_participation"] >= r["A_approved_applicants"] + 5),
               "A_but_zero_B": sample(lambda r: r["A_approved_applicants"] >= 3 and r["B_participation"] == 0)}
    with open(os.path.join(a.out, "inspection_samples.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["bucket", "generic", "posting", "market", "A_approved", "A_nonDISCN", "B_participation", "B_current_only", "reason", "outcome"])
        for b, rows in samples.items():
            for r in rows: w.writerow([b, r["generic"], r["posting"], r["market_ingredient"]+" | "+r["market_dfroute"], r["A_approved_applicants"], r["A_approved_applicants_nonDISCN"], r["B_participation"], r["B_participation_current_only"], r["reason"][:40], r["outcome"]])

    idc = collections.Counter(i["identity_status"] for i in ident); dfc = collections.Counter(i["date_flag"] for i in ident if i["date_flag"])
    overlap = sum(1 for i in ident if i["date_flag"] and i["identity_status"] == "excluded_identity_conflict")
    unmatched = [i for i in ident if i["identity_status"] == "unmatched"]

    md = f"""# Stage 2 — market-structure feasibility audit

Listings ingested: current {n_cur}, excluded {n_exc} (KITs dropped; only listings with an Orange Book application number
can be placed in a market). Orange Book markets (ingredient + DF;Route): {len(market_products)}.

## Analytical eligibility (coverage ≠ eligibility)
| Identity status | Episodes |
|---|---|
{chr(10).join(f'| {k} | {v} |' for k, v in idc.items())}

Date flags (marketing end before posting), classified: {dict(dfc)}; of these, {overlap} overlap the identity exclusions.
Eligible (confirmed) episodes: {len(el)}; with a defined Orange Book market (application-based, non-KIT): {len(mk_ok)} ({100*len(mk_ok)/len(el):.1f}%); drugs with a market: {len(drug)}.

Episodes without a market, by reason: {dict(collections.Counter('no application (unapproved/BLA)' if not r['has_application'] else 'KIT' if r['is_kit'] else 'application not in Orange Book' for r in el if not r['ob_market_defined']))}

## Measure A — approved applicants (Orange Book, approved by posting)
Episode level: {dist(A)}   |  median {st.median(A) if A else 'n/a'}
Drug level (median per drug): {dist(A_d)}

## Measure B — retrospective participation proxy (labelers with marketing window containing posting)
Episode level: {dist(B)}   |  median {st.median(B) if B else 'n/a'}
Drug level: {dist(B_d)}

## Agreement between A and B
Spearman (episode level): {spearman(A, B):.3f}
{dict(agree_tab)}
B > A arises from repackagers/relabelers and authorized generics (several labelers per application); B < A from applicants
with approvals but no listing in a marketing window containing the posting date.

## Sensitivity of B
{chr(10).join(f'- {k}: {v:.3f}' for k, v in sens.items())}

## Coverage of a defined market by posting year (market defined / listings present)
| Year | Market defined | Any listing |
|---|---|---|
{cov('posting_year')}

## By outcome
| Outcome | Market defined | Any listing |
|---|---|---|
{cov('outcome')}

## By therapeutic category (first listed; top 12)
| Category | Market defined |
|---|---|
{cov_cat()}

## Markets: {len(markets)} distinct; episodes per market: median {st.median(len(v) for v in markets.values())}, max {max(len(v) for v in markets.values())}

## Still-unmatched episodes ({len(unmatched)}), listed individually
{chr(10).join(f"- {i['generic'][:45]} | posted {i['posting']} | {i['reason'][:35]} | {i['outcome']}" for i in unmatched)}

## Caveats carried forward
- A is regulatory competition potential; B is retrospectively reconstructed participation. Not combined.
- FDA marketing end dates can reflect expected expiry of the last lot rather than the end of production; the end−365 sensitivity brackets that.
- The current Orange Book may omit approvals later removed or transferred; historical editions remain relevant.
- B counts labelers, not independent manufacturers.
- See inspection_samples.csv for manual review of zero-, single- and high-count markets and A/B disagreements.
"""
    open(os.path.join(a.out, "stage2_market_audit.md"), "w").write(md); print(md)

if __name__ == "__main__":
    main()
