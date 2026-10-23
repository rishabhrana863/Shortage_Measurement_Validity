#!/usr/bin/env python3
"""
Two-level ASHP–FDA crosswalk and hybrid-spell feasibility audit.

Level 1 — pharmaceutical identity. Both names are parsed into: ingredient base (salt stripped but recorded), salt,
  family/formulation (parenteral/oral/ophthalmic/...; solution/powder/tablet/capsule/...), release (ER/DR/IR),
  strength tokens, presentation markers (bag, vial, syringe, premix, large/small volume), combination flag.
  Identity confidence: HIGH = ingredient + family + formulation + release agree and no presentation conflict;
  MEDIUM = ingredient + family agree, formulation unknown on one side; LOW = ingredient only or a presentation
  conflict (e.g. ASHP 'large volume bags' vs FDA vials).
Level 2 — spell identity. An FDA drug record (drug_spell_audit.csv row) is linked to an ASHP bulletin only if
  the FDA entry falls inside the ASHP spell: FDA posting within [created-90d, created+90d] when FDA entry is
  OBSERVED, or FDA first sighting within the ASHP spell when posting is unreliable. The FDA Resolved mark is an
  event for the pair only if (a) it falls after ASHP creation and (b) the FDA record shows no internal absence
  (no inferred recurrence) and (c) no second FDA entry for the same drug lies between ASHP creation and the
  Resolved mark. Otherwise the pair is right-censored at the FDA last sighting or AMBIGUOUS.
  Spell confidence: CONFIRMED = Level-1 HIGH + FDA entry observed inside spell + exit rule (a)(b)(c) decidable;
  PROBABLE = Level-1 HIGH/MEDIUM + timelines compatible but FDA entry left-censored or posting-only;
  AMBIGUOUS = Level-1 LOW, several candidate FDA records/presentations, FDA recurrence inside the ASHP spell,
  or FDA resolution before ASHP creation.
The FDA resolution DECISION date (FDA 'Date of Update' marked Resolved, from the workbook) is recorded separately
from the archive snapshot in which it was first observed (observation interval).
"""
import csv, re, collections, statistics as st, datetime as dt, sys, os
import openpyxl
sys.path.insert(0, ".")
from stage1_join_audit import parse_date
D = lambda s: dt.date.fromisoformat(s) if s else None

SALTS = r"HYDROCHLORIDE|HCL|SODIUM|POTASSIUM|CALCIUM|MAGNESIUM|SULFATE|ACETATE|MESYLATE|MALEATE|TARTRATE|BITARTRATE|CITRATE|PHOSPHATE|SUCCINATE|FUMARATE|BESYLATE|TOSYLATE|BROMIDE|CHLORIDE|LACTATE|GLUCONATE|DIMESYLATE|DISODIUM|MONOHYDRATE|HYDROBROMIDE|NITRATE|PAMOATE|DECANOATE|VALERATE|PROPIONATE|BENZOATE|TROMETHAMINE|MEGLUMINE|AXETIL|CAPROATE|ESYLATE|HYCLATE|DIPROPIONATE|PALMITATE|ACETONIDE"
FORM = {"tablet": r"\bTABLETS?\b|\bTAB\b", "capsule": r"\bCAPSULES?\b|\bCAP\b", "solution": r"\bSOLUTION\b|\bINJECTION\b|\bINJECTABLE\b|\bLIQUID\b", "powder": r"\bPOWDER\b|FOR INJECTION|LYOPHIL|FOR SOLUTION|FOR SUSPENSION|STERILE POWDER",
        "suspension": r"\bSUSPENSION\b", "emulsion": r"\bEMULSION\b", "ointment": r"\bOINTMENT\b", "cream": r"\bCREAM\b", "gel": r"\bGEL\b", "spray": r"\bSPRAY\b", "patch": r"\bPATCH|TRANSDERMAL SYSTEM", "drops": r"\bDROPS?\b", "strips": r"\bSTRIPS?\b", "kit": r"\bKIT\b", "inhalation": r"\bINHAL|\bNEBUL|\bAEROSOL"}
FAMILY = {"ophthalmic": r"OPHTHALMIC|OPTHALMIC", "parenteral": r"INJECT|\bIV\b|INTRAVENOUS|INFUSION|VIALS?|PREFILLED|SYRINGE|\bBAGS?\b|PREMIX|FOR INJECTION|INTRAMUSCULAR|SUBCUTANEOUS", "topical": r"TOPICAL|CREAM|OINTMENT(?! .*OPHTH)|\bGEL\b|LOTION", "inhalation": r"INHAL|NEBUL|AEROSOL|RESPIRATORY", "nasal": r"NASAL", "rectal": r"RECTAL|SUPPOSITOR", "otic": r"OTIC", "vaginal": r"VAGINAL", "transdermal": r"TRANSDERMAL|PATCH", "oral": r"TABLET|CAPSULE|ORAL|SYRUP|ELIXIR|CHEWABLE|SOFTGEL|LOZENGE"}
PRES = {"bag": r"\bBAGS?\b|LARGE VOLUME|SMALL VOLUME|PREMIX|IN DEXTROSE|IN SODIUM CHLORIDE|GALAXY|DUPLEX", "vial": r"\bVIALS?\b|PHARMACY BULK", "syringe": r"SYRINGE|PREFILLED|AUTO-INJECTOR|\bPEN\b|CARTRIDGE", "ampule": r"AMPULE|AMP\b"}

def parse(name):
    u = re.sub(r"[™®]", "", name.upper()); u = re.sub(r"\((.*?)\)", r" \1 ", u)
    salt = ";".join(sorted(set(re.findall(rf"\b({SALTS})\b", u))))
    fam = next((k for k, p in FAMILY.items() if re.search(p, u)), "")
    forms = sorted(k for k, p in FORM.items() if re.search(p, u))
    if "solution" in forms and ("powder" in forms): forms = [f for f in forms if f != "solution"]
    # 'Injection' alone does not say solution vs powder: keep as unknown parenteral form unless SOLUTION/LIQUID is explicit
    if "solution" in forms and not re.search(r"\bSOLUTION\b|\bLIQUID\b|PREMIX|IN DEXTROSE|IN SODIUM CHLORIDE", u): forms = [f for f in forms if f != "solution"]
    rel = "ER" if re.search(r"EXTENDED|SUSTAINED|\bER\b|\bXR\b|\bXL\b|\bSR\b|\bLA\b|24.?HOUR|ONCE.DAILY", u) else "DR" if re.search(r"DELAYED|ENTERIC|\bDR\b|\bEC\b", u) else "IR"
    strengths = sorted(set(m.replace(" ", "") for m in re.findall(r"\d+(?:\.\d+)?\s*(?:MG|MCG|G\b|GM|%|MEQ|UNITS?|MMOL|MG/ML)", u)))
    pres = sorted(k for k, p in PRES.items() if re.search(p, u))
    combo = bool(re.search(r"\bAND\b|;|/(?!ML)", re.sub(r"\d+(\.\d+)?\s*(MG|MCG|G|GM|ML|%)", "", u))) or u.count(",") >= 2
    base = re.sub(rf"\b({SALTS})\b", " ", u)
    base = re.sub(r"\b(INJECTION|INJECTABLE|TABLETS?|CAPSULES?|ORAL|SOLUTION|SUSPENSION|USP|FOR|IN|OF|THE|WITH|EMULSION|POWDER|VIALS?|BAGS?|SYRINGES?|OPHTHALMIC|TOPICAL|CREAM|OINTMENT|GEL|SPRAY|NASAL|EXTENDED|DELAYED|RELEASE|IMMEDIATE|CHEWABLE|SOFTGEL|KIT|STERILE|PRESERVATIVE|FREE|LARGE|SMALL|VOLUME|ML|MG|MCG|GM|G|L|UNITS?|INTRAVENOUS|IV|IM|SC|PREFILLED|PREMIX|DEXTROSE|SODIUM CHLORIDE|LYOPHILIZED|SYSTEM|TRANSDERMAL|PATCH|DROPS?|STRIPS?|INHALATION|AEROSOL|NEBULIZER|CONCENTRATE|LIQUID|SYRUP|ELIXIR|MULTI-?DOSE|SINGLE-?DOSE|PHARMACY|BULK|PACKAGE|AUTO-?INJECTOR|PEN|CARTRIDGE|AMPULES?|CONTAINER|PLASTIC|FLEXIBLE|MINI-?BAG|DUPLEX|GALAXY)\b", " ", base)
    base = re.sub(r"[\d\.%/,:;\-\(\)]", " ", base); base = re.sub(r"\s+", " ", base).strip()
    return dict(base=base, salt=salt, family=fam, forms=";".join(forms), release=rel, strengths=";".join(strengths), pres=";".join(pres), combo=int(combo))

def identity(a, f):
    if a["base"] != f["base"]: return "NONE", "ingredient differs"
    notes = []
    if a["family"] and f["family"] and a["family"] != f["family"]: return "LOW", f"family {a['family']} vs {f['family']}"
    if a["release"] != f["release"]: return "LOW", f"release {a['release']} vs {f['release']}"
    if a["pres"] and f["pres"] and not (set(a["pres"].split(";")) & set(f["pres"].split(";"))): return "LOW", f"presentation {a['pres']} vs {f['pres']}"
    if a["combo"] != f["combo"]: return "LOW", "combination vs single"
    if a["forms"] and f["forms"]:
        if set(a["forms"].split(";")) & set(f["forms"].split(";")): return "HIGH", "ingredient+family+form agree"
        return "LOW", f"form {a['forms']} vs {f['forms']}"
    if a["salt"] and f["salt"] and a["salt"] != f["salt"]: notes.append(f"salt {a['salt']} vs {f['salt']}")
    return "MEDIUM", "; ".join(notes) or "form unknown on one side"

# ------------------------------------------------------------------ data
A = list(csv.DictReader(open("ashp_resolved_bulletins.csv")))
F = list(csv.DictReader(open("stage2b_audit/drug_spell_audit.csv")))
M = list(csv.DictReader(open("stage2b_audit/market_definition_changes.csv")))
mk_by_drug = collections.defaultdict(list)
for m in M: mk_by_drug[m["generic"]].append(m)
# FDA resolution decision dates per drug (earliest Resolved mark) and first-seen snapshot of that mark
wb = openpyxl.load_workbook("FDA_Recovery_Time_Validation.xlsx", read_only=True)
rows = list(wb["FDA Product Episodes"].iter_rows(values_only=True)); H = rows[3]
EP = [dict(zip(H, r)) for r in rows[4:] if r and r[0]]
snap = sorted({parse_date(r[1]) for r in list(wb["Snapshot Audit"].iter_rows(values_only=True))[4:] if r and r[1] and parse_date(r[1])})
res_by_drug = collections.defaultdict(list)
for e in EP:
    if e["Event observed"]: res_by_drug[e["Generic name"]].append(parse_date(e["Resolution / censor"]))
def obs_snapshot_after(d):
    return next((s for s in snap if s >= d), None)

fp = {f["generic"]: parse(f["generic"]) for f in F}
ap = {a["ashp_id"]: parse(a["generic_name"]) for a in A}

# ------------------------------------------------------------------ Level 1 + Level 2
cross, spells = [], []
for a in A:
    pa = ap[a["ashp_id"]]; ac, ar = D(a["created"]), D(a["revised"])
    cands = []
    for f in F:
        lvl, why = identity(pa, fp[f["generic"]])
        if lvl == "NONE": continue
        fpost, ffs, ffl = D(f["drug_posting"]), D(f["first_seen"]), D(f["last_seen"])
        # temporal compatibility of the spell
        entry_in = (f["entry_status"].startswith("OBSERVED") and abs((fpost - ac).days) <= 90) or (ac - dt.timedelta(days=90) <= ffs <= ar)
        overlap = ac <= ffl and ar >= ffs
        cands.append((f, lvl, why, entry_in, overlap))
    cands = [c for c in cands if c[4]]
    for f, lvl, why, entry_in, overlap in cands:
        cross.append({"ashp_id": a["ashp_id"], "ashp_name": a["generic_name"], "ashp_created": a["created"], "ashp_revised": a["revised"], "fda_generic": f["generic"],
                      "identity_confidence": lvl, "identity_evidence": why, "ashp_parse": f"{pa['base']}|{pa['family']}|{pa['forms']}|{pa['release']}|{pa['pres']}", "fda_parse": f"{fp[f['generic']]['base']}|{fp[f['generic']]['family']}|{fp[f['generic']]['forms']}|{fp[f['generic']]['release']}|{fp[f['generic']]['pres']}",
                      "fda_entry_status": f["entry_status"], "fda_posting": f["drug_posting"], "fda_first_seen": f["first_seen"], "fda_entry_inside_ashp_spell": int(entry_in), "n_fda_candidates_for_bulletin": len(cands)})
    if not cands: continue
    # Level 2 spell decision — one row per bulletin
    high = [c for c in cands if c[1] == "HIGH"]; use = high or [c for c in cands if c[1] == "MEDIUM"]
    if len({c[0]["generic"] for c in use}) > 1 or not use:
        spells.append({"ashp_id": a["ashp_id"], "ashp_name": a["generic_name"], "ashp_created": a["created"], "spell_confidence": "AMBIGUOUS",
                       "reason": f"{len(cands)} FDA candidates ({', '.join(sorted({c[1] for c in cands}))} identity)" if cands else "no candidate", "fda_generic": "; ".join(sorted({c[0]["generic"][:30] for c in cands}))})
        continue
    f, lvl, why, entry_in, _ = use[0]
    res = sorted(r for r in res_by_drug.get(f["generic"], []) if r)
    res_after = [r for r in res if r >= ac]
    recur = f["multiple_spells"].startswith("INFERRED")
    rec = {"ashp_id": a["ashp_id"], "ashp_name": a["generic_name"], "ashp_created": a["created"], "ashp_revised_(not_used_as_exit)": a["revised"], "fda_generic": f["generic"],
           "identity_confidence": lvl, "fda_entry_status": f["entry_status"][:12], "fda_entry_inside_ashp_spell": int(entry_in), "fda_internal_absence": int(recur),
           "fda_resolution_decision_date": res_after[0].isoformat() if res_after else "", "fda_resolution_first_observed_snapshot": obs_snapshot_after(res_after[0]).isoformat() if res_after and obs_snapshot_after(res_after[0]) else "",
           "fda_last_seen": f["last_seen"], "n_fda_resolutions_in_record": len(res)}
    if res and not res_after: rec.update(spell_confidence="AMBIGUOUS", reason="FDA resolution precedes ASHP creation (different spell)")
    elif recur: rec.update(spell_confidence="AMBIGUOUS", reason="FDA record shows internal absence (possible recurrence inside ASHP spell)")
    elif not entry_in: rec.update(spell_confidence="AMBIGUOUS", reason="FDA entry not inside ASHP spell window")
    elif lvl == "HIGH" and f["entry_status"].startswith("OBSERVED"): rec.update(spell_confidence="CONFIRMED", reason="identity HIGH; FDA observed entry inside spell")
    else: rec.update(spell_confidence="PROBABLE", reason=f"identity {lvl}; FDA entry {f['entry_status'][:13]}")
    if rec["spell_confidence"] != "AMBIGUOUS":
        if res_after:
            rec["event"] = 1; rec["onset_to_exit_days"] = (res_after[0] - ac).days
            rec["exit_observation_interval"] = f"({(snap[snap.index(obs_snapshot_after(res_after[0]))-1] if snap.index(obs_snapshot_after(res_after[0]))>0 else 'n/a')}, {obs_snapshot_after(res_after[0])}]" if obs_snapshot_after(res_after[0]) else ""
        else:
            rec["event"] = 0; rec["onset_to_exit_days"] = (D(f["last_seen"]) - ac).days; rec["exit_observation_interval"] = f"censored at {f['last_seen']}"
    mks = mk_by_drug.get(f["generic"], [])
    rec["has_bounded_applicant_count"] = int(bool(mks)); rec["market_lower"] = st.median([int(m["lower_confirmed"]) for m in mks]) if mks else ""; rec["market_point"] = st.median([int(m["point_confirmed_plus_provisional"]) for m in mks]) if mks else ""; rec["market_upper"] = st.median([int(m["upper_plus_compatible_unresolved"]) for m in mks]) if mks else ""
    spells.append(rec)

os.makedirs("stage3_ashp", exist_ok=True)
keys = sorted({k for r in cross for k in r});
with open("stage3_ashp/ashp_fda_crosswalk.csv", "w", newline="") as f: w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(cross)
keys = sorted({k for r in spells for k in r})
with open("stage3_ashp/hybrid_spells.csv", "w", newline="") as f: w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(spells)

# ------------------------------------------------------------------ summary
conf = collections.Counter(s["spell_confidence"] for s in spells)
usable = [s for s in spells if s["spell_confidence"] in ("CONFIRMED", "PROBABLE")]
C = [s for s in spells if s["spell_confidence"] == "CONFIRMED"]
ev = [s for s in usable if s.get("event") == 1]; evC = [s for s in C if s.get("event") == 1]
dur = [s["onset_to_exit_days"] for s in ev]; durC = [s["onset_to_exit_days"] for s in evC]
neg = sum(1 for d in dur if d < 0); long_ = sum(1 for d in dur if d > 1460)
idc = collections.Counter(c["identity_confidence"] for c in cross)
amb_reasons = collections.Counter(s["reason"].split(" (")[0] for s in spells if s["spell_confidence"] == "AMBIGUOUS")
def q(x): return f"min {min(x)}, q1 {round(st.quantiles(x,n=4)[0])}, median {round(st.median(x))}, q3 {round(st.quantiles(x,n=4)[2])}, max {max(x)}" if len(x) > 3 else str(sorted(x))
md = f"""# Hybrid ASHP–FDA spell feasibility

ASHP bulletins: {len(A)}; with ≥1 FDA candidate overlapping in time: {len({c['ashp_id'] for c in cross})}; crosswalk rows (bulletin × FDA record): {len(cross)}
Level-1 identity on crosswalk rows: {dict(idc)}

## Spell classification (one row per ASHP bulletin with a candidate)
{dict(conf)}
AMBIGUOUS reasons: {dict(amb_reasons)}

## The metrics requested
| Metric | Value |
|---|---|
| ASHP bulletin coverage (unique bulletins matched to an FDA record) | {len({c['ashp_id'] for c in cross})} of {len(A)} |
| Confirmed spell pairs (distinct bulletins, HIGH identity, FDA entry observed inside spell) | {len(C)} ({len({s['fda_generic'] for s in C})} distinct FDA drugs) |
| Probable spell pairs | {conf.get('PROBABLE',0)} |
| Observed FDA resolutions — events (CONFIRMED / CONFIRMED+PROBABLE) | {len(evC)} / {len(ev)} |
| Right-censored spells (CONFIRMED / CONFIRMED+PROBABLE) | {len(C)-len(evC)} / {len(usable)-len(ev)} |
| Ambiguous / recurrent spells excluded | {conf.get('AMBIGUOUS',0)} |
| Duration plausibility, events (CONFIRMED) | {q(durC)} |
| Duration plausibility, events (CONFIRMED+PROBABLE) | {q(dur)}; negative {neg}; >4 years {long_} |
| Market-structure linkage: confirmed spells with bounded applicant counts | {sum(s['has_bounded_applicant_count'] for s in C)} of {len(C)} |

Resolution decision date (FDA Date of Update marked Resolved) and the archive snapshot where it was first observed
are recorded separately in hybrid_spells.csv; the exit observation interval is the snapshot gap containing the first sighting.

## Reading
- CONFIRMED pairs are the primary analytical sample; PROBABLE are a sensitivity set; AMBIGUOUS are excluded pending review.
- An FDA resolution is attached only when it follows ASHP creation and the FDA record shows no internal absence — never
  'first FDA resolution after ASHP creation' alone.
- Event counts and independent drug counts, not bulletin counts, determine what analysis is credible.
"""
open("stage3_ashp/hybrid_spell_feasibility.md", "w").write(md); print(md)
