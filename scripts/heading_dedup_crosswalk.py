#!/usr/bin/env python3
"""
Duplicate-heading crosswalk for the FDA generic headings (Option 3, steps 1-3).

Step 1  Candidate pairs: headings whose deterministic normalisation agrees on ingredient base (salts stripped, USP /
        punctuation / case / plural removed) AND administration family AND formulation class AND release class.
Step 2  Adjudication evidence per pair: salt difference, strength-token overlap, presentation conflict, NDC overlap
        (any shared NDC9 or shared labeler code), temporal overlap of the two headings' observation windows.
Step 3  Classification:
        MERGE          same base, same formulation/release, no salt or presentation conflict, observation windows overlap
                       (duplicate administrative records of one spell)
        KEEP_SEPARATE  salt differs / release differs / presentation conflicts / windows do not overlap
                       (different presentation, or temporally distinct spells of the same medicine)
        REVIEW         same base and formulation but windows overlap only partly, or strengths disagree, or a
                       heading is a combination/multi-component product
Nothing is merged here; the output is a reviewed crosswalk with rationale.
"""
import csv, re, collections, sys, datetime as dt
import openpyxl
sys.path.insert(0, ".")
from stage1_join_audit import parse_date
from ashp_fda_crosswalk import parse   # the same Level-1 parser used for ASHP-FDA identity

wb = openpyxl.load_workbook("FDA_Recovery_Time_Validation.xlsx", read_only=True)
rows = list(wb["FDA Product Episodes"].iter_rows(values_only=True)); H = rows[3]
EP = [dict(zip(H, r)) for r in rows[4:] if r and r[0]]
for e in EP:
    e["ndc9"] = re.sub(r"\D", "", str(e["NDC9"]).replace("​", "")).zfill(9)
    for k in ("Initial posting", "First seen", "Last seen"): e[k] = parse_date(e[k])
by = collections.defaultdict(list)
for e in EP: by[e["Generic name"]].append(e)
heads = sorted(by)

# Heading-level base: keep the full active-ingredient phrase (salts included, since 'sodium chloride' and 'potassium
# chloride' are the ingredient, not a salt of something else); strip only form/route/presentation/grade vocabulary.
STRIP = re.compile(r"\b(INJECTION|INJECTABLE|INJ|TABLETS?|CAPSULES?|ORAL|SOLUTION|SUSPENSION|USP|NF|BP|FOR|IN|OF|THE|WITH|AND|EMULSION|POWDER|VIALS?|BAGS?|SYRINGES?|OPHTHALMIC|TOPICAL|CREAM|OINTMENT|GEL|SPRAY|NASAL|CHEWABLE|KIT|STERILE|PRESERVATIVE|FREE|LARGE|SMALL|VOLUME|INTRAVENOUS|IV|IM|SC|PREFILLED|PREMIX|LYOPHILIZED|SYSTEM|TRANSDERMAL|PATCH|DROPS?|STRIPS?|INHALATION|AEROSOL|CONCENTRATE|LIQUID|SYRUP|ELIXIR|IRRIGATION|SUPPOSITOR(Y|IES)|LOZENGES?|FILM|GRANULES?|PELLETS?|PLASTIC|CONTAINER|MONOHYDRATE|ANHYDROUS|DIHYDRATE|HYDROUS|EXTENDED|DELAYED|IMMEDIATE|RELEASE|ER|XR|SR|DR|LA)\b")
def norm(h):
    p = parse(h)
    u = re.sub(r"\(.*?\)", " ", h.upper()); u = re.sub(r"[\d\.]+\s*(%|MG|MCG|G|GM|ML|MEQ|UNITS?)(/\w+)?", " ", u)
    base = STRIP.sub(" ", u); base = re.sub(r"[^A-Z ]", " ", base); base = re.sub(r"\s+", " ", base).strip().rstrip("S")
    return base, p
info = {h: norm(h) for h in heads}
groups = collections.defaultdict(list)
for h, (base, p) in info.items():
    fam = p["family"] or "unspecified"
    form = (p["forms"].split(";")[0] if p["forms"] else "unspecified")
    groups[(base, fam, form, p["release"])].append(h)

def window(h): return min(x["First seen"] for x in by[h]), max(x["Last seen"] for x in by[h])
def ndcs(h): return {x["ndc9"] for x in by[h]}
def labelers(h): return {x["ndc9"][:5] for x in by[h]}
def overlap(a, b): return a[0] <= b[1] and b[0] <= a[1]

out = []
for key, hs in groups.items():
    if len(hs) < 2: continue
    for i in range(len(hs)):
        for j in range(i + 1, len(hs)):
            a, b = hs[i], hs[j]; pa, pb = info[a][1], info[b][1]
            wa, wb_ = window(a), window(b)
            HYD = {"MONOHYDRATE", "DIHYDRATE", "ANHYDROUS"}
            sa_, sb_ = set(pa["salt"].split(";")) - HYD - {""}, set(pb["salt"].split(";")) - HYD - {""}
            salt_diff = bool(sa_ and sb_ and sa_ != sb_)
            pres_conflict = pa["pres"] and pb["pres"] and not (set(pa["pres"].split(";")) & set(pb["pres"].split(";")))
            sa, sb = set(pa["strengths"].split(";")) - {""}, set(pb["strengths"].split(";")) - {""}
            strength_conflict = bool(sa and sb and not (sa & sb))
            ndc_shared = len(ndcs(a) & ndcs(b)); lab_shared = len(labelers(a) & labelers(b))
            combo = pa["combo"] or pb["combo"]
            win = overlap(wa, wb_)
            post_gap = abs((min(x["Initial posting"] for x in by[a]) - min(x["Initial posting"] for x in by[b])).days)
            if salt_diff: cls, why = "KEEP_SEPARATE", f"salt differs ({pa['salt'] or 'none'} vs {pb['salt'] or 'none'})"
            elif pres_conflict: cls, why = "KEEP_SEPARATE", f"presentation conflict ({pa['pres']} vs {pb['pres']})"
            elif not win: cls, why = "KEEP_SEPARATE", "observation windows do not overlap: temporally distinct spells"
            elif combo: cls, why = "REVIEW", "combination / multi-component heading"
            elif strength_conflict: cls, why = "REVIEW", f"strength tokens disagree ({';'.join(sorted(sa))} vs {';'.join(sorted(sb))})"
            elif ndc_shared: cls, why = "MERGE", f"{ndc_shared} shared NDC9; same base, form, release; windows overlap"
            elif post_gap <= 90: cls, why = "MERGE", f"same base, form, release; windows overlap; postings {post_gap} d apart"
            else: cls, why = "REVIEW", f"windows overlap but postings {post_gap} d apart and no shared NDC: duplicate record or second spell?"
            out.append({"heading_a": a, "heading_b": b, "normalised_base": key[0], "family": key[1], "formulation": key[2], "release": key[3],
                        "salt_a": pa["salt"], "salt_b": pb["salt"], "strengths_a": pa["strengths"], "strengths_b": pb["strengths"], "pres_a": pa["pres"], "pres_b": pb["pres"],
                        "ndc_a": len(ndcs(a)), "ndc_b": len(ndcs(b)), "shared_ndc9": ndc_shared, "shared_labeler_codes": lab_shared,
                        "window_a": f"{wa[0]}..{wa[1]}", "window_b": f"{wb_[0]}..{wb_[1]}", "windows_overlap": int(win), "posting_gap_days": post_gap,
                        "classification": cls, "rationale": why, "reviewer_decision": ""})
out.sort(key=lambda r: (r["classification"] != "MERGE", r["classification"] != "REVIEW", r["normalised_base"]))
with open("stage4_compare/heading_dedup_crosswalk.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
c = collections.Counter(r["classification"] for r in out)
print(f"headings {len(heads)}; candidate pairs {len(out)}; {dict(c)}")
heads_in_merge = {h for r in out if r["classification"] == "MERGE" for h in (r["heading_a"], r["heading_b"])}
print(f"headings involved in a MERGE pair: {len(heads_in_merge)}")
for cls in ("MERGE", "REVIEW", "KEEP_SEPARATE"):
    print(f"\n{cls}:")
    for r in [r for r in out if r["classification"] == cls][:40]:
        print(f"  {r['heading_a'][:38]:38} | {r['heading_b'][:38]:38} | ndc {r['ndc_a']}/{r['ndc_b']} shared {r['shared_ndc9']} | gap {r['posting_gap_days']:4d} | {r['rationale'][:60]}")
