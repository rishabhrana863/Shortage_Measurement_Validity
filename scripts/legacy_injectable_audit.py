#!/usr/bin/env python3
"""
(1) Finalise reviewer decisions in form_route_harmonization.csv per the approved table, splitting oral liquids
    into distinct subtypes (REVISE).
(2) Legacy-injectable error and coverage audit, three-tier hierarchy per Orange Book product row:
      HIGH        explicit dosage-form evidence from the current NDC Directory (DOSAGEFORMNAME) for the same application
      PROVISIONAL strength-pattern inference (per-container vs concentration) with exception checks
      REVIEW      unresolved, contradictory, or strength pattern unclassifiable
    Reports validation by class, false-powder / false-solution with denominators, coverage of the legacy-label
    shortage episodes under HIGH-only vs HIGH+PROVISIONAL, applicant-market assignment changes, and the
    classified exception list. Nothing is applied to market counts.
"""
import csv, re, collections, sys, os
D = sys.argv[1]  # fda_inputs dir

# ------------------------------------------------------------------ (1) finalise map
rows = list(csv.DictReader(open("form_route_harmonization.csv")))
ORAL_LIQ = {"SOLUTION": "oral solution", "SUSPENSION": "oral suspension", "SYRUP": "oral syrup", "ELIXIR": "oral elixir",
            "CONCENTRATE": "oral concentrate", "EMULSION": "oral emulsion", "LIQUID": "oral liquid (unspecified)",
            "DROPS": "oral drops", "TINCTURE": "oral tincture"}
for r in rows:
    lab = r["original_df_route"]; form = lab.split(";")[0].upper()
    if r["formulation"].startswith("oral liquid"):
        sub = next((v for k, v in ORAL_LIQ.items() if form.startswith(k)), "oral liquid, other")
        er = " (extended release)" if re.search(r"EXTENDED", form) else ""
        r["formulation"] = sub + er; r["proposed_equivalence_group"] = f"oral | {sub}{er}"
        r["review_status"] = "AUTO"; r["reviewer_decision"] = "REVISE->ACCEPT (subtypes kept distinct)"
        r["rationale"] = "Reviewer decision: keep solution, suspension, syrup, concentrate distinct initially. " + r["rationale"]
    elif lab == "LIQUID;N/A" or r["family"] == "other/unclassified":
        r["reviewer_decision"] = "REVIEW (hold; do not infer route)"
    elif r["family"] == "parenteral" and r["formulation"].startswith("injectable, legacy"):
        r["reviewer_decision"] = "ACCEPT_CONDITIONAL (strength provisional; NDC-form evidence high; see legacy audit)"
    elif "Multi-route label" in r["rationale"] or "Co-packaged" in r["rationale"] or "Coated pellets" in r["rationale"]:
        r["reviewer_decision"] = "REVIEW"
    elif r["family"] in ("inhalation", "nasal") and r["review_status"] == "REVIEW":
        r["reviewer_decision"] = "REVIEW (hold device/delivery distinctions)"
    elif r["review_status"] == "AUTO":
        r["reviewer_decision"] = "ACCEPT"
    else:
        r["reviewer_decision"] = "REVIEW"
with open("form_route_harmonization.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
dec = collections.Counter(r["reviewer_decision"].split(" ")[0] for r in rows)

# ------------------------------------------------------------------ (2) legacy audit
ob = [r for r in csv.DictReader(open(f"{D}/ob/products.txt", encoding="utf-8", errors="replace"), delimiter="~")]
legacy = [r for r in ob if r["DF;Route"].startswith("INJECTABLE;")]
ndc_forms = collections.defaultdict(set)
for r in csv.DictReader(open(f"{D}/ndc/product.txt", encoding="utf-8", errors="replace"), delimiter="\t"):
    ap = re.sub(r"\D", "", r.get("APPLICATIONNUMBER") or ""); f = (r.get("DOSAGEFORMNAME") or "").upper()
    if ap and f and f != "KIT": ndc_forms[ap].add(f)

def form_class(f):
    if re.search(r"POWDER|LYOPHIL|FOR SOLUTION|FOR SUSPENSION", f): return "powder"
    if re.search(r"EMULSION", f): return "emulsion"
    if re.search(r"LIPOSOM", f): return "liposomal"
    if re.search(r"SUSPENSION", f): return "suspension"
    if re.search(r"SOLUTION|CONCENTRATE|INJECTION$", f): return "solution"   # bare 'INJECTION' = liquid in FDA SPL usage
    return "other"
def strength_class(s):
    s = s.upper()
    if re.search(r"/VIAL|/AMP|/BOTTLE|/CONTAINER|/PKG|/SYRINGE|/CARTRIDGE|/PEN", s): return "powder"      # per-container
    if re.search(r"/ML|/L\b|%|/HR|/24HR|/DOSE", s): return "solution"                                     # concentration
    return "unclassified"
def exception_type(sc, nc, strength, forms):
    if sc == "powder" and nc == "solution": return "liquid in container expressed per vial/syringe (premixed bag, multi-dose vial, prefilled syringe)"
    if sc == "solution" and nc == "powder": return "powder expressed as reconstituted concentration (per mL)"
    if sc == "solution" and nc == "emulsion": return "emulsion expressed per mL (class granularity, not a powder/solution error)"
    if sc == "solution" and nc == "suspension": return "suspension expressed per mL (class granularity)"
    if sc == "powder" and nc in ("emulsion", "suspension", "liposomal"): return f"{nc} expressed per container"
    return "other"

audit = []; by_appl = collections.defaultdict(list)
for r in legacy:
    ap = re.sub(r"\D", "", r["Appl_No"]); forms = ndc_forms.get(ap, set())
    classes = {form_class(f) for f in forms} - {"other"}
    nc = sorted(classes)[0] if len(classes) == 1 else ("mixed" if classes else "")
    sc = strength_class(r["Strength"])
    if nc and nc != "mixed":
        tier, final = "HIGH", nc
        if sc != "unclassified" and sc != nc and not (sc == "solution" and nc in ("emulsion", "suspension", "liposomal")):
            tier = "HIGH (strength contradicts; NDC evidence kept)"
    elif nc == "mixed":
        tier, final = "REVIEW (mixed NDC forms under one application)", ""
    elif sc != "unclassified":
        tier, final = "PROVISIONAL", sc
    else:
        tier, final = "REVIEW (no evidence; strength unclassifiable)", ""
    rec = {"ingredient": r["Ingredient"], "df_route": r["DF;Route"], "applicant": r["Applicant"], "appl_no": r["Appl_No"],
           "product_no": r["Product_No"], "strength": r["Strength"], "type": r["Type"], "ndc_form_evidence": "; ".join(sorted(forms))[:80],
           "ndc_class": nc, "strength_class": sc, "tier": tier, "final_formulation": final,
           "exception_type": exception_type(sc, nc, r["Strength"], forms) if (nc and nc != "mixed" and sc not in ("unclassified", nc)) else ""}
    audit.append(rec); by_appl[ap].append(rec)
with open("legacy_injectable_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(audit[0].keys())); w.writeheader(); w.writerows(audit)
exc = [a for a in audit if a["exception_type"]]
with open("legacy_injectable_exceptions.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(audit[0].keys())); w.writeheader(); w.writerows(exc)

# validation by class (rows where NDC evidence exists and strength classifiable)
val = collections.defaultdict(lambda: [0, 0])
for a in audit:
    if a["ndc_class"] and a["ndc_class"] != "mixed" and a["strength_class"] != "unclassified":
        ok = a["strength_class"] == a["ndc_class"]; val[a["ndc_class"]][1] += 1; val[a["ndc_class"]][0] += ok
false_powder = sum(1 for a in audit if a["strength_class"] == "powder" and a["ndc_class"] in ("solution", "emulsion", "suspension", "liposomal"))
pow_den = sum(1 for a in audit if a["strength_class"] == "powder" and a["ndc_class"] and a["ndc_class"] != "mixed")
false_solution = sum(1 for a in audit if a["strength_class"] == "solution" and a["ndc_class"] == "powder")
sol_den = sum(1 for a in audit if a["strength_class"] == "solution" and a["ndc_class"] and a["ndc_class"] != "mixed")
tiers = collections.Counter(a["tier"].split(" ")[0] for a in audit)

# coverage of legacy-label shortage episodes: resolved if the episode's own application has a single final formulation
E = list(csv.DictReader(open("stage2_audit/episode_measures.csv")))
S1 = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1_audit/match_by_episode.csv"))}
S1b = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage1b_audit/recovered_matches.csv"))}
leg_eps = [e for e in E if e.get("market_dfroute", "").startswith("INJECTABLE;")]
cov = {"HIGH only": collections.Counter(), "HIGH+PROVISIONAL": collections.Counter()}
for e in leg_eps:
    k = e["ndc9"] + "|" + e["posting"]; src = e["source"]
    ap = re.sub(r"\D", "", (S1[k]["ndc_appl_no"] if src == "current" else S1b[k]["appl_no"]) or "")
    recs = by_appl.get(ap, [])
    for spec, ok_tiers in (("HIGH only", ("HIGH",)), ("HIGH+PROVISIONAL", ("HIGH", "PROVISIONAL"))):
        fin = {a["final_formulation"] for a in recs if a["tier"].split(" ")[0] in ok_tiers and a["final_formulation"]}
        cov[spec]["resolved: " + sorted(fin)[0] if len(fin) == 1 else ("conflict within application" if len(fin) > 1 else "unresolved")] += 1

# applicant-market assignment changes: per legacy ingredient market, distinct applicants whose rows would move to a sub-market
def changes(ok_tiers):
    moved = total = 0
    for a in audit:
        total += 1
        if a["tier"].split(" ")[0] in ok_tiers and a["final_formulation"]: moved += 1
    return moved, total
m_h, tot = changes(("HIGH",)); m_hp, _ = changes(("HIGH", "PROVISIONAL"))

exc_types = collections.Counter(a["exception_type"] for a in exc)
md = f"""# Legacy-injectable error and coverage audit

Map finalised: reviewer decisions {dict(dec)} across 304 labels; oral liquids split into distinct subtypes.

Legacy-label Orange Book product rows: {len(audit)} ({len(by_appl)} applications). Tier assignment:
{dict(tiers)}

## Validation of the strength rule where NDC-form evidence exists (agreement / rows, by true class)
| True class (NDC form) | Strength rule agrees |
|---|---|
{chr(10).join(f'| {k} | {v[0]}/{v[1]} ({100*v[0]/v[1]:.1f}%) |' for k, v in sorted(val.items()))}

False-powder (strength says per-container, NDC says liquid): {false_powder}/{pow_den} ({100*false_powder/max(1,pow_den):.1f}%)
False-solution (strength says concentration, NDC says powder): {false_solution}/{sol_den} ({100*false_solution/max(1,sol_den):.1f}%)

## Exception list ({len(exc)} rows) by error type — see legacy_injectable_exceptions.csv
{chr(10).join(f'- {k}: {v}' for k, v in exc_types.most_common())}

## Coverage of the {len(leg_eps)} legacy-label shortage episodes
| Outcome | HIGH only | HIGH + PROVISIONAL |
|---|---|---|
{chr(10).join(f"| {k} | {cov['HIGH only'].get(k,0)} | {cov['HIGH+PROVISIONAL'].get(k,0)} |" for k in sorted(set(cov['HIGH only'])|set(cov['HIGH+PROVISIONAL'])))}

## Applicant-market assignment changes (legacy rows that would move from the undifferentiated legacy market into a formulation sub-market)
- HIGH only: {m_h}/{tot} rows ({100*m_h/tot:.1f}%)
- HIGH + PROVISIONAL: {m_hp}/{tot} rows ({100*m_hp/tot:.1f}%)
Rows not moved stay in the undifferentiated legacy market (REVIEW stratum), never merged into solution or powder.

## Reading
- HIGH-only is the proposed primary specification; HIGH+PROVISIONAL the sensitivity specification.
- Per-container strength is not conclusive evidence of a powder: the exception list shows the liquid-in-container cases.
- A shortage episode is 'resolved' only when every classified row of its own application agrees on one formulation.
"""
open("legacy_injectable_audit.md", "w").write(md); print(md)
