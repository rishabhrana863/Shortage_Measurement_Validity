#!/usr/bin/env python3
"""
Historical-validation priority register, deduplicated to market x posting-year, from stage2b outputs.
Priorities:
  1  single-applicant status flips between lower and upper bound
  2  wide bounds (upper - lower >= 6)
  3  own product approved after posting (pre-approval / NDC-identity anomaly)
  4  salt-form variants of one base ingredient in the same family|formulation (merge NOT applied; review only)
  5  markets with episodes recovered from the excluded (discontinued) file
Evidence required is stated per row: historical Orange Book edition (applicant/approval status at posting) and/or
historical NDC snapshot (listing/marketing status at posting).
"""
import csv, re, collections, statistics as st
C = list(csv.DictReader(open("stage2b_audit/market_definition_changes.csv")))
E = {r["ndc9"] + "|" + r["posting"]: r for r in csv.DictReader(open("stage2_audit/episode_measures.csv"))}
SALT = re.compile(r"\b(HYDROCHLORIDE|HCL|SODIUM|POTASSIUM|CALCIUM|MAGNESIUM|SULFATE|SULPHATE|ACETATE|MESYLATE|MALEATE|TARTRATE|BITARTRATE|CITRATE|PHOSPHATE|SUCCINATE|FUMARATE|BESYLATE|TOSYLATE|BROMIDE|CHLORIDE|LACTATE|GLUCONATE|DIMESYLATE|DISODIUM|MONOHYDRATE|DIHYDRATE|ANHYDROUS|HYDROBROMIDE|NITRATE|PAMOATE|DECANOATE|PALMITATE|VALERATE|PROPIONATE|BENZOATE|SALICYLATE|TROMETHAMINE|MEGLUMINE|ESTOLATE|STEARATE|AXETIL|HEMIHYDRATE|SESQUIHYDRATE)\b")
def base(ing): return re.sub(r"\s+", " ", SALT.sub("", ing)).strip(" ;,")

# ---- market x posting-year groups
G = collections.defaultdict(list)
for c in C:
    G[(c["harmonized_market"], c["posting"][:4])].append(c)
# ---- salt-form conflict detection across markets (same base ingredient + same formulation string)
fam_form = collections.defaultdict(set)
for c in C:
    ing, grp, rel = c["harmonized_market"].split(" | ")[0], " | ".join(c["harmonized_market"].split(" | ")[1:3]), c["harmonized_market"].split(" | ")[-1]
    fam_form[(base(ing), grp, rel)].add(ing)
salt_conf = {k: v for k, v in fam_form.items() if len(v) > 1}

reg = []
for (mk, yr), rows in G.items():
    ing = mk.split(" | ")[0]; grp = " | ".join(mk.split(" | ")[1:3]); rel = mk.split(" | ")[-1]
    lo = [int(r["lower_confirmed"]) for r in rows]; pt = [int(r["point_confirmed_plus_provisional"]) for r in rows]; up = [int(r["upper_plus_compatible_unresolved"]) for r in rows]
    flips = sum(1 for r in rows if r["single_applicant_lower"] != r["single_applicant_upper"])
    wide = sum(1 for r in rows if int(r["bound_width"]) >= 6)
    pre = sum(int(r["own_product_approved_after_posting"]) for r in rows)
    amb = sum(int(r["own_product_ambiguous"]) for r in rows)
    excl = sum(1 for r in rows if E[r["ndc9"] + "|" + r["posting"]]["source"] == "excluded")
    prov = set(); unres = set()
    for r in rows:
        prov |= {x for x in r["provisional_applicants"].split("; ") if x}; unres |= {x for x in r["unresolved_applicants"].split("; ") if x}
    own_prov = sum(1 for r in rows if "PROVISIONAL" in r["own_tier"])
    salt = (base(ing), grp, rel) in salt_conf
    src = []
    if prov: src.append(f"{len(prov)} provisional competitor(s) (strength-pattern classification)")
    if unres: src.append(f"{len(unres)} unresolved legacy competitor(s)")
    if own_prov: src.append("own product classified provisionally")
    if amb: src.append("own product ambiguous (alternatives reported)")
    if pre: src.append("own product approved after posting — NDC identity / application check")
    if salt: src.append("salt-form variants in same formulation: " + " vs ".join(sorted(salt_conf[(base(ing), grp, rel)])))
    ev = []
    if prov or unres or own_prov: ev.append(f"Orange Book edition ~{yr}: applicant list, dosage-form labels and approval status in this market at posting")
    if excl or prov: ev.append(f"NDC Directory snapshot ~{yr}: whether provisional/discontinued competitors were listed and marketed at posting")
    if pre: ev.append("Verify the shortage NDC's application number and approval date; check for NDC reuse or an unapproved/503B listing")
    if salt: ev.append("Pharmaceutical-equivalence review of the salt forms before any merge (naming normalisation only, no automatic merge)")
    pr = 1 if flips else 2 if wide else 3 if pre else 4 if salt else 5 if excl else 6
    if pre and pr > 3: pr = 3
    hier = []
    if prov or own_prov: hier.append("H1 historical application/product record (Orange Book edition at posting) — establishes approval status, not marketing")
    if pre: hier.append("H2 predecessor/successor application linkage (cumulative supplements)")
    if excl or prov: hier.append("H3 product-specific NDC listing/labeling at posting (dated NDC snapshot) — establishes marketing")
    hier.append("H4 retrospective inference from current records — current basis of all provisional counts; cannot establish a historical fact")
    reg.append({"priority": pr, "triggers": "+".join(t for t, f in (("flip", flips), ("wide", wide), ("preapproval", pre), ("salt", salt), ("discontinued", excl)) if f) or "none",
                "evidence_hierarchy": " | ".join(hier), "market_id": mk, "ingredient": ing, "formulation": grp, "release": rel, "posting_year": yr,
                "episodes": len(rows), "episodes_from_excluded_file": excl, "lower": st.median(lo), "point": st.median(pt), "upper": st.median(up),
                "bound_width": st.median(up) - st.median(lo), "single_applicant_flip_episodes": flips, "wide_bound_episodes": wide,
                "preapproval_anomaly_episodes": pre, "salt_form_conflict": int(salt),
                "uncertainty_source": "; ".join(src) or "none (zero-width bounds)",
                "provisional_competitors_to_verify": "; ".join(sorted(prov))[:200], "unresolved_competitors": "; ".join(sorted(unres))[:120],
                "historical_evidence_required": " | ".join(ev) or "none", "verification_status": "pending" if pr <= 5 else "not required"})
reg.sort(key=lambda r: (r["priority"], -r["single_applicant_flip_episodes"], -r["bound_width"], -r["episodes"]))
with open("stage2b_audit/historical_validation_register.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(reg[0].keys())); w.writeheader(); w.writerows(reg)

# ---- summary at episode and market level
def n_markets(rows): return len({r["market_id"] for r in rows})
by_pr = collections.defaultdict(list)
for r in reg: by_pr[r["priority"]].append(r)
by_year = collections.Counter(); 
for r in reg:
    if r["priority"] <= 4: by_year[r["posting_year"]] += 1
lines = ["# Historical-validation priority register — summary", "",
         "Counting units: the Stage 2b summary reported 122 flip episodes among 1,842 unambiguous episodes (one assignment each). The register counts",
         "episode-assignments, so ambiguous products contribute one row per plausible market; both figures are preserved. Triggers overlap (a row may",
         "be flip+wide+preapproval), so priority totals are not additive — see the `triggers` column.", "",
         "Orange Book editions that would cover priority 1–4 market×year rows: " + ", ".join(f"{y}: {n}" for y, n in sorted(by_year.items())), "",
         f"Episode-assignments: {len(C)} | market×year groups: {len(reg)} | distinct harmonized markets: {n_markets(reg)}", "",
         "| Priority | Trigger | market×year groups | distinct markets | episodes |", "|---|---|---|---|---|"]
names = {1: "single-applicant flip", 2: "wide bounds (≥6)", 3: "own product approved after posting", 4: "salt-form conflict", 5: "discontinued-file episodes only", 6: "no validation required"}
for p in sorted(by_pr):
    rows = by_pr[p]; lines.append(f"| {p} | {names[p]} | {len(rows)} | {n_markets(rows)} | {sum(r['episodes'] for r in rows)} |")
flip_eps = sum(r["single_applicant_flip_episodes"] for r in reg); flip_mk = len({r["market_id"] for r in reg if r["single_applicant_flip_episodes"]})
wide_eps = sum(r["wide_bound_episodes"] for r in reg); wide_mk = len({r["market_id"] for r in reg if r["wide_bound_episodes"]})
pre_eps = sum(r["preapproval_anomaly_episodes"] for r in reg); pre_mk = len({r["market_id"] for r in reg if r["preapproval_anomaly_episodes"]})
lines += ["", f"Single-applicant flips: {flip_eps} episodes in {flip_mk} markets ({len([r for r in reg if r['single_applicant_flip_episodes']])} market×year groups)",
          f"Wide bounds: {wide_eps} episodes in {wide_mk} markets", f"Pre-approval anomalies: {pre_eps} episodes in {pre_mk} markets",
          f"Salt-form conflicts: {len(salt_conf)} base-ingredient/formulation sets: " + "; ".join(" vs ".join(sorted(v)) for v in list(salt_conf.values())[:12]), "",
          "## Priority 1 — flip markets (top 15 by flip episodes)", "", "| Market | Year | Episodes | lower / point / upper | provisional competitors to verify |", "|---|---|---|---|---|"]
for r in [r for r in reg if r["priority"] == 1][:15]:
    lines.append(f"| {r['ingredient'][:30]} · {r['formulation'].split('|')[-1].strip()[:28]} | {r['posting_year']} | {r['episodes']} | {r['lower']} / {r['point']} / {r['upper']} | {r['provisional_competitors_to_verify'][:70]} |")
lines += ["", "## Priority 3 — pre-approval anomalies (top 10)", "", "| Market | Year | Episodes | note |", "|---|---|---|---|"]
for r in [r for r in reg if r["preapproval_anomaly_episodes"]][:10]:
    lines.append(f"| {r['ingredient'][:30]} · {r['formulation'].split('|')[-1].strip()[:28]} | {r['posting_year']} | {r['preapproval_anomaly_episodes']} | own product's earliest Orange Book approval is after posting |")
open("stage2b_audit/historical_validation_register.md", "w").write("\n".join(lines)); print("\n".join(lines))
