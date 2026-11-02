"""Table 8: administrative dating differences on ASHP-FDA paired spells, by spell-confidence tier.
Inputs: stage3_ashp/hybrid_spells.csv, stage3_ashp/ashp_fda_crosswalk.csv, ashp_resolved_bulletins.csv
Output: stage3_ashp/table8_register_timing.csv
Unit: one row per ASHP bulletin with an FDA identity candidate (166), classified CONFIRMED / PROBABLE / AMBIGUOUS.
Onset gap: FDA recorded posting minus ASHP creation, only where the FDA entry is observed (positive = FDA later).
Exit gap: ASHP last revision minus FDA Resolved determination, only where a resolution follows ASHP creation
with no internal absence (positive = ASHP later). Tiers: CONFIRMED; CONFIRMED+PROBABLE; all candidates.
"""
import pandas as pd
h = pd.read_csv("stage3_ashp/hybrid_spells.csv")
x = pd.read_csv("stage3_ashp/ashp_fda_crosswalk.csv").drop_duplicates(["ashp_id", "fda_generic"])
h = h.merge(x[["ashp_id", "fda_generic", "fda_posting"]], on=["ashp_id", "fda_generic"], how="left")
for c in ["ashp_created", "ashp_revised_(not_used_as_exit)", "fda_posting", "fda_resolution_decision_date"]:
    h[c] = pd.to_datetime(h[c], errors="coerce")
h["observed_entry"] = h["fda_entry_status"].astype(str).str.startswith("OBSERVED")
def summarize(d):
    d = d.dropna()
    return {"pairs": len(d), "median_days": int(round(d.median())) if len(d) else None,
            "q1_days": int(round(d.quantile(.25))) if len(d) else None, "q3_days": int(round(d.quantile(.75))) if len(d) else None,
            "within_30d": int((d.abs() <= 30).sum()), "within_90d": int((d.abs() <= 90).sum())}
tiers = {"CONFIRMED": h.spell_confidence == "CONFIRMED",
         "CONFIRMED+PROBABLE": h.spell_confidence.isin(["CONFIRMED", "PROBABLE"]),
         "All candidate bulletins": pd.Series(True, index=h.index)}
rows = []
for tier, m in tiers.items():
    s = h[m]; on = s[s.observed_entry]; ex = s[s.fda_resolution_decision_date.notna()]
    rows.append({"tier": tier, "comparison": "FDA posting minus ASHP creation (onset)", **summarize((on.fda_posting - on.ashp_created).dt.days)})
    rows.append({"tier": tier, "comparison": "ASHP last revision minus FDA Resolved determination (exit)", **summarize((ex["ashp_revised_(not_used_as_exit)"] - ex.fda_resolution_decision_date).dt.days)})
out = pd.DataFrame(rows); out.to_csv("stage3_ashp/table8_register_timing.csv", index=False)
A = pd.read_csv("ashp_resolved_bulletins.csv")
span = (pd.to_datetime(A.revised, errors="coerce") - pd.to_datetime(A.created, errors="coerce")).dt.days
print(out.to_string(index=False))
print(f"\nASHP bulletins open > 2 years: {(span > 730).sum()}; > 4 years: {(span > 1460).sum()} of {len(A)}")
