#!/usr/bin/env python3
"""
Build form_route_harmonization.csv from the Orange Book's own DF;Route label set. Proposes, does not apply.

Two levels:
  family       — administration family (normalises legacy route wording): oral, parenteral, ophthalmic, topical,
                 inhalation, nasal, otic, rectal, vaginal, transdermal, buccal/sublingual, irrigation, dialysis, other
  formulation  — market-relevant formulation preserving release and reconstitution distinctions
Proposed equivalence group = family | formulation. Route sub-specification inside the parenteral family
(IV vs IM,IV vs SC) is recorded but NOT used to split markets; whether to split is itself flagged for review.
Legacy 'INJECTABLE;INJECTION' cannot be resolved to solution vs powder from the label alone -> REVIEW, with the
proposed resolution of using the linked NDC Directory DOSAGEFORMNAME per application.
"""
import csv, re, collections, sys

labels = [(int(c), l) for c, l in (ln.rstrip("\n").split("\t") for ln in open(sys.argv[1]))]
touched = collections.Counter()
if len(sys.argv) > 2:
    for r in csv.DictReader(open(sys.argv[2])):
        if r.get("market_dfroute"): touched[r["market_dfroute"]] += 1

ROUTE_FAMILY = [
    (r"OPHTHALMIC", "ophthalmic"), (r"OTIC", "otic"), (r"NASAL", "nasal"), (r"INHALATION|RESPIRATORY", "inhalation"),
    (r"TRANSDERMAL", "transdermal"), (r"VAGINAL", "vaginal"), (r"RECTAL", "rectal"),
    (r"BUCCAL|SUBLINGUAL", "buccal/sublingual"), (r"IRRIGATION", "irrigation"),
    (r"INTRAPERITONEAL|HEMODIALYSIS|DIALYSIS", "dialysis/peritoneal"),
    (r"INJECTION|INTRAVENOUS|INTRAMUSCULAR|SUBCUTANEOUS|INTRATHECAL|EPIDURAL|INTRAVITREAL|INTRA-ARTICULAR|INTRADERMAL|INTRACAVERNOUS|INTRAVESICAL|INTRAARTERIAL|PERINEURAL|INFILTRATION|SPINAL|IM-IV|INTRA-ARTERIAL|INTRALESIONAL|INTRAOCULAR|INTRACAMERAL|INTRAUTERINE|INTRACARDIAC|INTRASYNOVIAL|INTRAPLEURAL|INTRACAVITARY|INTRAVENTRICULAR|INTRACEREBROVENTRICULAR|INTRATYMPANIC|IMPLANTATION|SUBDERMAL|INTRACORONARY", "parenteral"),
    (r"TOPICAL|DENTAL|PERIODONTAL|URETHRAL|PERCUTANEOUS|CUTANEOUS|SUBGINGIVAL|INTRAVESICAL", "topical/local"),
    (r"ORAL|ENTERAL|GASTROENTERAL", "oral"),
]
def family(route):
    for pat, fam in ROUTE_FAMILY:
        if re.search(pat, route): return fam
    return "other/unclassified"

def formulation(form, fam):
    f = form.upper()
    er = bool(re.search(r"EXTENDED RELEASE|EXTENDED-RELEASE|SUSTAINED|CONTROLLED|LONG ACTING|24 HR|12 HR", f))
    dr = bool(re.search(r"DELAYED REL", f))
    if fam == "parenteral":
        if f == "INJECTABLE": return "injectable, legacy label — solution vs powder unresolved", "REVIEW"
        if re.search(r"LIPOSOM", f): return "injectable, liposomal", "AUTO"
        if re.search(r"EMULSION", f): return "injectable, emulsion", "AUTO"
        if re.search(r"SUSPENSION", f) and not re.search(r"^FOR ", f): return "injectable, suspension" + (" (extended release)" if er else ""), "AUTO"
        if re.search(r"POWDER|FOR SOLUTION|FOR SUSPENSION|LYOPHIL|FOR INJECTION", f): return "injectable, powder/for reconstitution" + (" (extended release)" if er else ""), "AUTO"
        if re.search(r"SOLUTION|CONCENTRATE", f): return "injectable, ready-to-use solution" + (" (extended release)" if er else ""), "AUTO"
        if re.search(r"IMPLANT|PELLET|INSERT", f): return "implant", "AUTO"
        return "injectable, other: " + f, "REVIEW"
    if fam == "oral":
        if re.search(r"TABLET", f):
            if re.search(r"ORALLY DISINTEGRATING", f): return "tablet, orally disintegrating", "AUTO"
            if re.search(r"CHEWABLE", f): return "tablet, chewable", "AUTO"
            if re.search(r"FOR SUSPENSION|FOR SOLUTION|EFFERVESCENT|SOLUBLE", f): return "tablet, for dispersion/effervescent", "AUTO"
            if er: return "tablet, extended release", "AUTO"
            if dr: return "tablet, delayed release", "AUTO"
            return "tablet, immediate release", "AUTO"
        if re.search(r"CAPSULE", f):
            if er: return "capsule, extended release", "AUTO"
            if dr: return "capsule, delayed release", "AUTO"
            return "capsule, immediate release", "AUTO"
        if re.search(r"FOR SUSPENSION|FOR SOLUTION|POWDER|GRANULE|PELLET", f) and not re.search(r"TABLET", f):
            return ("oral powder/granule for reconstitution" + (" (extended release)" if er else "") + (" (delayed release)" if dr else "")), "AUTO"
        if re.search(r"SOLUTION|SYRUP|ELIXIR|CONCENTRATE|SUSPENSION|EMULSION|LIQUID|DROPS|TINCTURE", f):
            return "oral liquid (solution/suspension/syrup/elixir/concentrate)", "REVIEW"   # solution vs suspension may matter
        if re.search(r"FILM|LOZENGE|TROCHE|GUM|WAFER|STRIP", f): return "oral, other solid: " + f, "AUTO"
        return "oral, other: " + f, "REVIEW"
    # non-oral, non-parenteral: form kept nearly verbatim
    base = re.sub(r"\s+", " ", f)
    status = "AUTO"
    if fam in ("inhalation", "nasal") and re.search(r"AEROSOL|SPRAY|POWDER|SOLUTION|SUSPENSION", f): status = "REVIEW"  # device/delivery differences
    return base.lower() + (" (extended release)" if er else ""), status

rows = []
for cnt, lab in labels:
    form, _, route = lab.partition(";")
    fam = family(route.upper())
    frm, status = formulation(form, fam)
    if fam == "other/unclassified": status = "REVIEW"
    if route.upper().startswith("ORAL-"): frm += "; cycle pack (" + route + ")"   # ORAL-21/28 contraceptive packs
    extra = ""
    if re.search(r"CAPSULE", form.upper()) and re.search(r"TABLET", form.upper()):
        status, extra = "REVIEW", "Co-packaged tablet+capsule product; not a single-form market."
    if re.search(r"COATED PELLETS", form.upper()):
        status, extra = "REVIEW", "Coated pellets may be enteric (delayed release); confirm release profile."
    routes = [x.strip() for x in route.upper().split(",")]
    fams = {family(x) for x in routes if x}
    if len(fams) > 1:
        status, extra = "REVIEW", f"Multi-route label spanning families {sorted(fams)}; assign to the family of the shortage product, not merged."
    group = f"{fam} | {frm}"
    rationale = {
        "REVIEW": {
            "parenteral": "Legacy label: solution vs powder not stated. PROPOSED RESOLUTION (per Orange Book product row, not per label): strength denominator /VIAL, /AMP, /BOTTLE -> 'injectable, powder/for reconstitution'; /ML, /L or % -> 'injectable, ready-to-use solution'; other -> REVIEW. Validated against NDC Directory DOSAGEFORMNAME on 2,020 rows: 98.7% agreement; known exceptions are premixed frozen bags and multi-dose vials expressed per vial (see legacy_injectable_resolution_validation.csv). Route sub-specification recorded, not used to split.",
            "oral": "Oral liquids: solution vs suspension may or may not be substitutable; decide per ingredient or keep separate.",
            "inhalation": "Device/delivery differences (MDI vs DPI vs nebuliser solution) are market-relevant; keep separate unless reviewed.",
            "nasal": "Metered spray vs solution/drops; keep separate unless reviewed.",
        }.get(fam, "Unclassified route or form; manual assignment required."),
        "AUTO": "Standardised wording only; release characteristics and reconstitution status preserved; route sub-specification recorded but not used to split the market.",
    }[status]
    if extra: rationale = extra + " " + rationale
    rows.append({"original_df_route": lab, "ob_product_rows": cnt, "shortage_episodes_in_current_market": touched.get(lab, 0),
                 "family": fam, "formulation": frm, "proposed_equivalence_group": group,
                 "route_subspecification_recorded": route, "release": "ER" if "extended" in frm else "DR" if "delayed" in frm else "IR/NA",
                 "rationale": rationale, "review_status": status, "reviewer_decision": ""})

with open("form_route_harmonization.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

g = collections.defaultdict(list)
for r in rows: g[r["proposed_equivalence_group"]].append(r)
print(f"labels={len(rows)}  proposed groups={len(g)}  REVIEW={sum(1 for r in rows if r['review_status']=='REVIEW')}  AUTO={sum(1 for r in rows if r['review_status']=='AUTO')}")
print("\nGroups that would recombine >1 label (label count, OB rows, shortage episodes touched):")
for grp, rs in sorted(g.items(), key=lambda kv: -sum(x["shortage_episodes_in_current_market"] for x in kv[1])):
    if len(rs) > 1:
        print(f"  {grp}: {len(rs)} labels, {sum(r['ob_product_rows'] for r in rs)} rows, {sum(r['shortage_episodes_in_current_market'] for r in rs)} episodes  <- {', '.join(r['original_df_route'] for r in rs[:6])}{' …' if len(rs)>6 else ''}")
print("\nREVIEW labels touching shortage episodes:")
for r in sorted([r for r in rows if r["review_status"]=="REVIEW" and r["shortage_episodes_in_current_market"]], key=lambda r: -r["shortage_episodes_in_current_market"]):
    print(f"  {r['original_df_route']}: {r['shortage_episodes_in_current_market']} episodes -> {r['proposed_equivalence_group']}")
