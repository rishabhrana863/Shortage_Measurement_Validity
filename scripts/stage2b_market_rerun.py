#!/usr/bin/env python3
"""
Stage 2b: harmonized market-definition rerun with bounded applicant counts. No survival models, no NADAC.

Per Orange Book product row -> harmonized market (ingredient, family | formulation, release) with a tier:
  CONFIRMED    non-legacy label accepted in the map; or legacy row with specific NDC-form evidence
               (SOLUTION / POWDER / EMULSION / SUSPENSION / LIPOSOMAL — the bare SPL form 'INJECTION' is NOT evidence);
               or legacy row whose trade name carries premixed / dual-chamber container markers
  PROVISIONAL  legacy row classified from strength pattern (per-container -> powder; concentration -> solution;
               /SYRINGE,/PEN,/CARTRIDGE -> solution), with verified overrides applied
  UNRESOLVED   legacy row with no evidence and unclassifiable strength; REVIEW-held labels kept as their own stratum

Per shortage episode (own product's harmonized class -> competitor set, applicants de-duplicated by normalized name,
approved on/before posting):
  lower   = CONFIRMED same-market applicants                              (also the HIGH-only sensitivity)
  point   = CONFIRMED + PROVISIONAL same-market applicants
  upper   = point + UNRESOLVED applicants in the same ingredient & family, IR release, strength-compatible
  orig    = Stage 2 unharmonized count (diagnostic only)
If the own product is ambiguous, every plausible assignment is reported; none is selected.
"""
import csv, re, os, sys, collections, datetime as dt, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_join_audit import parse_date, load_episodes

D = sys.argv[1]; OUT = "stage2b_audit"; os.makedirs(OUT, exist_ok=True)
NAMED = ["MIDAZOLAM", "CEFEPIME", "DEXMEDETOMIDINE", "TACROLIMUS", "LISDEXAMFETAMINE"]

def digits(s): return re.sub(r"\D", "", s or "")
def norm_app(s):
    s = re.sub(r"[.,]", "", (s or "").upper())
    s = re.sub(r"\b(INC|LLC|LTD|CO|CORP|CORPORATION|COMPANY|PHARMACEUTICALS?|PHARMA|PHARMS|USA|US|LP|PLC|LIMITED|GMBH|SA|AG|LABS|LABORATORIES|HLDGS|HOLDINGS)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()
UNIT_MG = {"MG": 1, "GM": 1000, "G": 1000, "MCG": 0.001, "UG": 0.001}
def amounts(strength):
    out = set()
    for v, u in re.findall(r"(\d+(?:\.\d+)?)\s*(MG|GM|MCG|UG|G|UNITS|IU|MEQ|MMOL|%)", (strength or "").upper()):
        out.add((round(float(v) * UNIT_MG[u], 4), "MG") if u in UNIT_MG else (float(v), u))
    return out

# ---------------------------------------------------------------- map
MAP = {r["original_df_route"]: r for r in csv.DictReader(open("form_route_harmonization.csv"))}
def accepted(r): return r["reviewer_decision"].startswith("ACCEPT") or r["reviewer_decision"].startswith("REVISE->ACCEPT")

# ---------------------------------------------------------------- NDC-form evidence (specific forms only)
ndc_forms = collections.defaultdict(set)
for r in csv.DictReader(open(f"{D}/ndc/product.txt", encoding="utf-8", errors="replace"), delimiter="\t"):
    ap = digits(r.get("APPLICATIONNUMBER")); f = (r.get("DOSAGEFORMNAME") or "").upper()
    if ap and f and f not in ("KIT", "INJECTION"): ndc_forms[ap].add(f)
def specific_class(forms):
    c = set()
    for f in forms:
        if re.search(r"POWDER|LYOPHIL|FOR SOLUTION|FOR SUSPENSION", f): c.add("powder/for reconstitution")
        elif re.search(r"LIPOSOM", f): c.add("liposomal")
        elif re.search(r"EMULSION", f): c.add("emulsion")
        elif re.search(r"SUSPENSION", f): c.add("suspension")
        elif re.search(r"SOLUTION|CONCENTRATE", f): c.add("ready-to-use solution")
    return c
PREMIX = re.compile(r"DUPLEX|GALAXY|PREMIX|AND DEXTROSE|IN DEXTROSE|IN SODIUM CHLORIDE|AND SODIUM CHLORIDE|IN PLASTIC CONTAINER|IN WATER|VIAFLEX|EXCEL CONTAINER|FLEXIBLE CONTAINER|ADD-VANTAGE|MINI-BAG")
def strength_class(s):
    s = (s or "").upper()
    if re.search(r"/SYRINGE|/PEN|/CARTRIDGE|/INJECTOR", s): return "ready-to-use solution", "prefilled device = liquid"
    if re.search(r"/VIAL|/AMP|/BOTTLE|/CONTAINER|/PKG", s): return "powder/for reconstitution", "per-container"
    if re.search(r"/ML|/L\b|%|/HR|/24HR|/DOSE", s): return "ready-to-use solution", "concentration"
    return None, "unclassifiable"

# verified overrides for the liquid-in-container cases reviewed above (appl_no -> formulation)
SUSPENSION_INGREDIENTS = {"METHYLPREDNISOLONE ACETATE"}   # verified injectable suspensions (Depo-Medrol and generics)
OVERRIDES = {  # true liquids in vials, verified against NDC 'INJECTION, SOLUTION' / 'SOLUTION' evidence
    "ANECTINE": "ready-to-use solution", "DILAUDID-HP": "ready-to-use solution", "METHOTREXATE SODIUM": "ready-to-use solution",
    "METHOTREXATE SODIUM PRESERVATIVE FREE": "ready-to-use solution", "INFUVITE PEDIATRIC": "ready-to-use solution",
    "INFUVITE PEDIATRIC (PHARMACY BULK PACKAGE)": "ready-to-use solution", "THAM-E": "ready-to-use solution",
}

# ---------------------------------------------------------------- classify every Orange Book row
ob_rows = []
for r in csv.DictReader(open(f"{D}/ob/products.txt", encoding="utf-8", errors="replace"), delimiter="~"):
    lab = r["DF;Route"]; m = MAP.get(lab); ap = digits(r["Appl_No"])
    ing = r["Ingredient"].upper().strip(); fam = m["family"] if m else "other/unclassified"
    rel = m["release"] if m else "IR/NA"
    tier, formulation, basis = "UNRESOLVED", None, ""
    if lab.startswith("INJECTABLE;"):
        fam = "parenteral"
        if PREMIX.search(r["Trade_Name"].upper()):
            tier, formulation, basis = "CONFIRMED", "premixed/dual-chamber container", "trade-name premix marker"
        else:
            sc = specific_class(ndc_forms.get(ap, set()))
            if len(sc) == 1: tier, formulation, basis = "CONFIRMED", next(iter(sc)), "specific NDC dosage form"
            elif len(sc) > 1: tier, formulation, basis = "UNRESOLVED", None, "mixed NDC forms under application"
            else:
                if ing in SUSPENSION_INGREDIENTS and fam == "parenteral":
                    tier, formulation, basis = "PROVISIONAL", "suspension", "verified override (injectable suspension, ingredient-level, reviewed)"
                elif r["Trade_Name"].upper() in OVERRIDES:
                    tier, formulation, basis = "PROVISIONAL", OVERRIDES[r["Trade_Name"].upper()], "verified override (liquid in vial)"
                else:
                    f_, why = strength_class(r["Strength"])
                    if f_: tier, formulation, basis = "PROVISIONAL", f_, "strength: " + why
                    else: basis = "no evidence; strength unclassifiable"
        group = f"parenteral | injectable, {formulation}" if formulation else "parenteral | injectable, UNRESOLVED"
    elif m and accepted(m) and fam == "parenteral" and PREMIX.search(r["Trade_Name"].upper()) and "injectable," in m["proposed_equivalence_group"]:
        tier, basis, group = "CONFIRMED", "trade-name premix marker (non-legacy label)", "parenteral | injectable, premixed/dual-chamber container"
    elif m and accepted(m):
        tier, basis, group = "CONFIRMED", "accepted label mapping", m["proposed_equivalence_group"]
    else:
        tier, basis, group = "UNRESOLVED", "label held for REVIEW", f"REVIEW-held | {lab}"
    ob_rows.append({"ingredient": ing, "label": lab, "family": fam, "group": group, "release": rel, "tier": tier, "basis": basis,
                    "applicant": norm_app(r["Applicant"]), "applicant_raw": r["Applicant"], "appl": ap, "product_no": r["Product_No"],
                    "trade": r["Trade_Name"], "strength": r["Strength"], "amounts": amounts(r["Strength"]),
                    "approval": parse_date(r["Approval_Date"]), "type": r["Type"]})

# ---- contradiction safeguard: a confirmed formulation for the same ingredient, family and strength that differs from a
#      strength-derived provisional class flags the provisional row for REVIEW (no automatic override)
conf_idx = collections.defaultdict(set)
for o in ob_rows:
    if o["tier"] == "CONFIRMED" and o["family"] == "parenteral" and "injectable," in o["group"]:
        for amt in o["amounts"]: conf_idx[(o["ingredient"], amt)].add(o["group"])
n_contra = 0
for o in ob_rows:
    if o["tier"] == "PROVISIONAL" and o["basis"].startswith("strength"):
        conflicting = set()
        for amt in o["amounts"]:
            conflicting |= {g for g in conf_idx.get((o["ingredient"], amt), set()) if g != o["group"] and g != "parenteral | injectable, premixed/dual-chamber container"}
        if conflicting:
            o["tier"], o["basis"], o["group"] = "UNRESOLVED", "REVIEW: strength-derived class contradicts confirmed " + "/".join(sorted(g.split(", ")[-1] for g in conflicting)) + " at same ingredient+strength", "parenteral | injectable, UNRESOLVED"
            n_contra += 1
print("contradiction-flagged provisional rows:", n_contra)
by_appl = collections.defaultdict(list); by_market = collections.defaultdict(list); by_ing_fam = collections.defaultdict(list)
for o in ob_rows:
    by_appl[o["appl"]].append(o); by_market[(o["ingredient"], o["group"], o["release"])].append(o); by_ing_fam[(o["ingredient"], o["family"])].append(o)

# ---------------------------------------------------------------- episodes
E = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage2_audit/episode_measures.csv"))}
S1 = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1_audit/match_by_episode.csv"))}
S1b = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1b_audit/recovered_matches.csv"))}
eps = load_episodes("FDA_Recovery_Time_Validation.xlsx")

def applicants(rows, posting, tiers):
    return {o["applicant"] for o in rows if o["tier"] in tiers and o["approval"] and o["approval"] <= posting}

changes, bounds, exc_audit = [], [], []
for e in eps:
    k = e["ndc9"] + "|" + e["posting"].isoformat(); em = E[k]; posting = e["posting"]
    if not em["identity_status"].startswith("confirmed") or em["ob_market_defined"] != "1": continue
    src = em["source"]; ap = digits(S1[k]["ndc_appl_no"] if src == "current" else S1b[k]["appl_no"])
    own = [o for o in by_appl.get(ap, []) if o["ingredient"] == em["market_ingredient"]] or by_appl.get(ap, [])
    if not own: continue
    # own product's harmonized classes among resolved rows
    own_groups = {(o["ingredient"], o["group"], o["release"]) for o in own if o["tier"] in ("CONFIRMED", "PROVISIONAL")}
    own_amounts = set().union(*[o["amounts"] for o in own]) if own else set()
    ambiguous = False
    if not own_groups:   # unresolved own product: enumerate plausible assignments
        ambiguous = True
        base = own[0]
        cands = ["ready-to-use solution", "powder/for reconstitution"] if base["family"] == "parenteral" else [None]
        own_groups = {(base["ingredient"], f"parenteral | injectable, {c}" if c else base["group"], base["release"]) for c in cands}
    elif len(own_groups) > 1: ambiguous = True
    for (ing, grp, rel) in sorted(own_groups):
        mk = by_market.get((ing, grp, rel), [])
        lower = applicants(mk, posting, ("CONFIRMED",))
        point = applicants(mk, posting, ("CONFIRMED", "PROVISIONAL"))
        fam = mk[0]["family"] if mk else grp.split(" | ")[0]
        unresolved = {o["applicant"] for o in by_ing_fam.get((ing, fam), [])
                      if o["tier"] == "UNRESOLVED" and o["release"] == rel and o["approval"] and o["approval"] <= posting
                      and (not own_amounts or not o["amounts"] or (o["amounts"] & own_amounts))}
        upper = point | unresolved
        prov_only = point - lower
        own_approvals = [o["approval"] for o in own if o["approval"]]
        preapproval = int(bool(own_approvals) and min(own_approvals) > posting)
        rec = {"provisional_applicants": "; ".join(sorted(prov_only)), "unresolved_applicants": "; ".join(sorted(unresolved)),
               "own_product_approved_after_posting": preapproval,
               "own_first_approval": min(own_approvals).isoformat() if own_approvals else "","ndc9": e["ndc9"], "generic": e["Generic name"], "posting": posting.isoformat(), "outcome": e["Censoring status"],
               "reason": e["Shortage reason"][:40], "appl": ap, "own_product_ambiguous": int(ambiguous), "n_alternative_assignments": len(own_groups),
               "old_market": f"{em['market_ingredient']} | {em['market_dfroute']}", "harmonized_market": f"{ing} | {grp} | {rel}",
               "own_tier": ";".join(sorted({o["tier"] for o in own})), "own_basis": ";".join(sorted({o["basis"] for o in own}))[:120],
               "orig_unharmonized_count": em.get("A_approved_applicants", ""),
               "lower_confirmed": len(lower), "point_confirmed_plus_provisional": len(point), "upper_plus_compatible_unresolved": len(upper),
               "high_only_sensitivity": len(lower), "bound_width": len(upper) - len(lower), "provisional_applicants_added": len(prov_only),
               "unresolved_applicants_added": len(unresolved),
               "single_applicant_lower": int(len(lower) <= 1), "single_applicant_point": int(len(point) <= 1), "single_applicant_upper": int(len(upper) <= 1),
               "named_test_drug": next((n for n in NAMED if n in ing), ""),
               "classification_confidence": "CONFIRMED" if not ambiguous and all(o["tier"] == "CONFIRMED" for o in own) else ("PROVISIONAL" if not ambiguous else "AMBIGUOUS")}
        changes.append(rec); bounds.append(rec)
        for o in own:
            if o["basis"].startswith("verified override") or o["basis"].startswith("trade-name premix") or o["tier"] == "UNRESOLVED":
                exc_audit.append({"generic": e["Generic name"], "posting": posting.isoformat(), "appl": ap, "trade": o["trade"], "strength": o["strength"],
                                  "tier": o["tier"], "basis": o["basis"], "formulation": o["group"]})

def write(name, rows, fields=None):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0].keys())); w.writeheader(); w.writerows(rows)
write("market_definition_changes.csv", changes)
write("market_bounds.csv", [{k: r[k] for k in ("ndc9", "generic", "posting", "harmonized_market", "own_product_ambiguous", "lower_confirmed",
      "point_confirmed_plus_provisional", "upper_plus_compatible_unresolved", "bound_width", "classification_confidence")} for r in bounds])
tail = [r for r in changes if r["single_applicant_point"] or r["single_applicant_lower"] or r["named_test_drug"]]
write("tail_validation.csv", tail)
# legacy exception audit: all overrides / premix / unresolved legacy rows, with affected episodes
leg_rows = [{"ingredient": o["ingredient"], "trade": o["trade"], "applicant": o["applicant_raw"], "appl": o["appl"], "strength": o["strength"],
             "tier": o["tier"], "basis": o["basis"], "formulation": o["group"],
             "affected_shortage_episodes": sum(1 for c in changes if c["appl"] == o["appl"])}
            for o in ob_rows if o["label"].startswith("INJECTABLE;") and (o["tier"] == "UNRESOLVED" or "override" in o["basis"] or "premix" in o["basis"])]
write("legacy_exception_audit.csv", leg_rows)
with open(os.path.join(OUT, "provenance.log"), "w") as f:
    f.write(f"run_utc={dt.datetime.now(dt.timezone.utc).isoformat()}\n")
    for p in ("form_route_harmonization.csv", f"{D}/ob/products.txt", f"{D}/ndc/product.txt"):
        f.write(f"{p}\tsha256={hashlib.sha256(open(p,'rb').read()).hexdigest()}\n")

# ---------------------------------------------------------------- summary
tiers = collections.Counter(o["tier"] for o in ob_rows if o["label"].startswith("INJECTABLE;"))
basis = collections.Counter(o["basis"].split(":")[0] for o in ob_rows if o["label"].startswith("INJECTABLE;"))
per_ep = collections.defaultdict(list)
for c in changes: per_ep[c["ndc9"] + "|" + c["posting"]].append(c)
n_ep = len(per_ep); amb = sum(1 for v in per_ep.values() if v[0]["own_product_ambiguous"])
unamb = [v[0] for v in per_ep.values() if not v[0]["own_product_ambiguous"]]
width = collections.Counter("0" if c["bound_width"] == 0 else "1–2" if c["bound_width"] <= 2 else "3–5" if c["bound_width"] <= 5 else "6+" for c in unamb)
flip = sum(1 for c in unamb if c["single_applicant_lower"] != c["single_applicant_upper"])
conf = collections.Counter(c["classification_confidence"] for c in unamb)
def med(xs): xs = sorted(xs); return xs[len(xs)//2] if xs else "n/a"
md = f"""# Stage 2b — harmonized market-definition rerun (bounded counts)

Legacy-injectable rows after corrections (bare 'INJECTION' no longer counts as evidence; premixed/dual-chamber containers
are their own class; prefilled devices are liquids): {dict(tiers)}; basis: {dict(basis)}

Episodes with a market: {n_ep}; own product unambiguous: {len(unamb)} ({dict(conf)}); ambiguous (alternatives reported, none selected): {amb}

## Bounds (unambiguous episodes)
| | lower (confirmed) | point (conf.+prov.) | upper (+compatible unresolved) | original unharmonized |
|---|---|---|---|---|
| median | {med([c['lower_confirmed'] for c in unamb])} | {med([c['point_confirmed_plus_provisional'] for c in unamb])} | {med([c['upper_plus_compatible_unresolved'] for c in unamb])} | {med([int(c['orig_unharmonized_count'] or 0) for c in unamb])} |

Bound width (upper − lower): {dict(width)}
Episodes whose single-applicant status differs between lower and upper bound: {flip} of {len(unamb)}
Single-applicant at point estimate: {sum(c['single_applicant_point'] for c in unamb)}; at lower: {sum(c['single_applicant_lower'] for c in unamb)}; at upper: {sum(c['single_applicant_upper'] for c in unamb)}

## Named test drugs (one representative episode each; full detail in tail_validation.csv)
| Drug | old market | harmonized market | orig | lower | point | upper | own tier |
|---|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| {n} | {c['old_market'][:45]} | {c['harmonized_market'][:60]} | {c['orig_unharmonized_count']} | {c['lower_confirmed']} | {c['point_confirmed_plus_provisional']} | {c['upper_plus_compatible_unresolved']} | {c['own_tier']} |"
    for n in NAMED for c in [next((c for c in changes if c["named_test_drug"] == n), None)] if c) + f"""

## Historical credibility check: bounds for episodes whose product came from the excluded (discontinued) file vs current file
""" + "\n".join(f"- {src}: n={len(v)}, median lower {med([c['lower_confirmed'] for c in v])}, point {med([c['point_confirmed_plus_provisional'] for c in v])}, upper {med([c['upper_plus_compatible_unresolved'] for c in v])}"
    for src, v in collections.defaultdict(list, {s: [c for c in unamb if E[c['ndc9']+'|'+c['posting']]['source'] == s] for s in ('current', 'excluded')}).items()) + """

Files: market_definition_changes.csv, market_bounds.csv, tail_validation.csv, legacy_exception_audit.csv, provenance.log
"""
open(os.path.join(OUT, "stage2b_summary.md"), "w").write(md); print(md)
