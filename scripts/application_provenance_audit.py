#!/usr/bin/env python3
"""
Application-provenance audit for episodes whose own product's earliest Orange Book approval is after the posting date.
Classifies each into one of:
  A  application_mismatch        the NDC listing's application was approved after posting, but the listing's own
                                 marketing start date is on/before posting -> the listing was marketed before this
                                 application existed (NDC reuse, re-listing under a successor application, or
                                 unapproved marketing); identity of the shortage product's application is not established
  B  historically_marketed_predecessor  the same applicant held a different application in the same ingredient market
                                 approved on/before posting -> successor application after transfer / re-approval
  C  approval_date_interpretation approval within 180 days after posting, or the Orange Book row is 'Approved Prior to
                                 Jan 1 1982'-type (parsed as 1982) with the listing marketed earlier
  D  unresolved_inconsistency     none of the above
Evidence levels recorded per the hierarchy: H1 historical application/product record (not available in current files),
H2 verified predecessor/successor linkage (B), H3 product-specific NDC listing evidence (A: marketing start date),
H4 retrospective inference from current records (everything else).
"""
import csv, re, collections, sys, datetime as dt
sys.path.insert(0, ".")
from stage1_join_audit import parse_date
D = sys.argv[1]
def digits(s): return re.sub(r"\D", "", s or "")

C = [c for c in csv.DictReader(open("stage2b_audit/market_definition_changes.csv")) if c["own_product_approved_after_posting"] == "1"]
S1 = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1_audit/match_by_episode.csv"))}
S1b = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1b_audit/recovered_matches.csv"))}
ob = list(csv.DictReader(open(f"{D}/ob/products.txt", encoding="utf-8", errors="replace"), delimiter="~"))
by_appl = collections.defaultdict(list)
for r in ob: by_appl[digits(r["Appl_No"])].append(r)
by_ing_applicant = collections.defaultdict(list)
for r in ob: by_ing_applicant[(r["Ingredient"].upper().strip(), r["Applicant"].upper().strip())].append(r)

out = []; seen = set()
for c in C:
    k = c["ndc9"] + "|" + c["posting"]
    if k in seen: continue
    seen.add(k)
    posting = dt.date.fromisoformat(c["posting"]); src = S1[k] if S1[k]["ndc_matched"] == "1" else S1b[k]
    ap = digits(src.get("ndc_appl_no") or src.get("appl_no")); start = parse_date(src.get("ndc_start_mkt") or src.get("start_mkt") or "")
    cat = src.get("ndc_marketing_cat") or src.get("marketing_cat") or ""
    rows = by_appl.get(ap, []); first = min((parse_date(r["Approval_Date"]) for r in rows if parse_date(r["Approval_Date"])), default=None)
    prior82 = any(r["Approval_Date"].lower().startswith("approved prior") for r in rows)
    applicant = rows[0]["Applicant"].upper().strip() if rows else ""; ing = c["harmonized_market"].split(" | ")[0]
    predecessors = sorted({(r["Appl_No"], parse_date(r["Approval_Date"])) for r in by_ing_applicant.get((ing, applicant), [])
                           if digits(r["Appl_No"]) != ap and parse_date(r["Approval_Date"]) and parse_date(r["Approval_Date"]) <= posting}, key=lambda x: x[1])
    lag = (first - posting).days if first else None
    if prior82 or (lag is not None and lag <= 180): cls, ev = "C approval_date_interpretation", "H4"
    elif predecessors: cls, ev = "B historically_marketed_predecessor", "H2"
    elif start and start <= posting: cls, ev = "A application_mismatch", "H3"
    else: cls, ev = "D unresolved_inconsistency", "H4"
    out.append({"ndc9": c["ndc9"], "generic": c["generic"], "posting": c["posting"], "market": c["harmonized_market"][:70], "source_file": "current" if S1[k]["ndc_matched"] == "1" else "excluded",
                "ndc_application": src.get("ndc_appl_no") or src.get("appl_no"), "marketing_category": cat, "listing_start_marketing": start.isoformat() if start else "",
                "application_first_approval": first.isoformat() if first else "", "days_approval_after_posting": lag, "applicant": applicant,
                "predecessor_applications_same_applicant": "; ".join(f"{a} ({d})" for a, d in predecessors)[:120],
                "classification": cls, "evidence_level": ev,
                "verification_needed": {"A": "Confirm which application the shortage NDC was marketed under at posting (historical Orange Book edition / NDC snapshot); check NDC reuse",
                                        "B": "Confirm transfer/successor linkage in historical Orange Book cumulative supplements",
                                        "C": "Confirm posting-to-approval timing; check tentative approval or 'approved prior to' convention",
                                        "D": "Manual review: no predecessor, no pre-posting listing date"}[cls[0]]})
with open("stage2b_audit/application_provenance_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
cnt = collections.Counter(o["classification"] for o in out); mk = collections.defaultdict(set)
for o in out: mk[o["classification"]].add(o["market"])
print(f"pre-approval episodes: {len(out)}")
for k, v in sorted(cnt.items()): print(f"  {k}: {v} episodes, {len(mk[k])} markets")
print("by marketing category:", dict(collections.Counter(o["marketing_category"] for o in out)))
print("by source file:", dict(collections.Counter(o["source_file"] for o in out)))
