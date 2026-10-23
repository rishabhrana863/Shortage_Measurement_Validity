#!/usr/bin/env python3
"""
Publication figures for the OSCM manuscript, built from the stage4 outputs (never from summary statistics).
  Figure 2  paired difference R1 - R2(latest onset) for the 173 common-cohort drugs: strip + box of the body,
            separate panel for the long right tail, 365-day threshold marked, extreme cases labelled.
  Figure 3  top-20 persistence membership under R1, R2-earliest, R2-latest: one row per drug in the union (24),
            dot per scenario where the drug is in the top 20; DEFINITE vs POSSIBLE separated; note on the 11 unrankable.
  Figure 1  data-flow and cohort diagram, drawn from the counts fixed in the manuscript.
Greyscale-safe: one hue (ink blue) for data, neutral greys for reference lines; all identity carried by labels.
"""
import csv, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = "stage4_compare/figures"; os.makedirs(OUT, exist_ok=True)
INK, INK2, GRID, BLUE, BLUE_L, WARN = "#111111", "#555555", "#dddddd", "#1f4e79", "#9db7d1", "#8a5a00"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})

P = list(csv.DictReader(open("stage4_compare/paired_durations_common_set.csv")))
for p in P:
    for k in ("R1_days", "R2_earliest_days", "R2_latest_days", "entry_bracket_days", "event"): p[k] = int(p[k])
    p["diff"] = p["R1_days"] - p["R2_latest_days"]
assert len(P) == 173

# ------------------------------------------------------------------ Figure 2
diffs = sorted(p["diff"] for p in P)
body = [p for p in P if p["diff"] <= 365]; tail = sorted([p for p in P if p["diff"] > 365], key=lambda p: -p["diff"])
import statistics as st
med, q1, q3 = st.median(diffs), st.quantiles(diffs, n=4)[0], st.quantiles(diffs, n=4)[2]

fig, (ax, axt) = plt.subplots(1, 2, figsize=(7.4, 3.6), dpi=300, gridspec_kw={"width_ratios": [3, 2.6], "wspace": 0.55})
# left: body, strip with jitter + box
import random; random.seed(7)
ys = [0.32 + random.uniform(-0.12, 0.12) for _ in body]
ax.scatter([p["diff"] for p in body], ys, s=14, color=BLUE, alpha=0.55, linewidths=0, zorder=3)
ax.boxplot([p["diff"] for p in body], orientation="horizontal", positions=[0.58], widths=0.2, showfliers=False, zorder=2,
           boxprops=dict(color=INK2, lw=1), whiskerprops=dict(color=INK2, lw=1), capprops=dict(color=INK2, lw=1), medianprops=dict(color=INK, lw=1.4))
ax.axvline(0, color=INK2, lw=0.8, ls=":")
ax.set_xlim(-5, 380); ax.set_ylim(0, 1); ax.set_yticks([])
ax.set_xlabel("Recorded posting minus archive-observed onset (days)", fontsize=8)
ax.set_title(f"a. Body: {len(body)} drugs within 365 d", loc="left", fontsize=8.8, color=INK)
ax.grid(True, axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.annotate(f"median {med:.0f} d, IQR {q1:.0f}–{q3:.0f} d", xy=(med, 0.68), xytext=(med + 70, 0.86), fontsize=7.6, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.text(358, 0.97, "365 d", ha="right", va="top", fontsize=7.5, color=WARN)
ax.axvline(365, color=WARN, lw=0.9, ls="--")
# right: tail, one bar per drug, labelled
SHORT = {"Sodium Phosphate, Dibasic, Anhydrous, Sodium Phosphate, Monobasic, Monohydrate Injection": "Sodium phosphates inj.", "Atropa Belladonna, Opium Suppository": "Belladonna & opium supp."}
def short(n):
    for k, v in SHORT.items():
        if n.startswith(k[:30]): return v
    return n.replace(" Injection", " inj.").replace(" Hydrochloride", " HCl").replace("Sodium Chloride", "NaCl").replace(" Monohydrate", "")[:30]
labels = [short(p["generic"]) for p in tail]
axt.barh(range(len(tail)), [p["diff"] for p in tail], color=BLUE, height=0.62, zorder=3)
axt.set_yticks(range(len(tail))); axt.set_yticklabels(labels, fontsize=7.2); axt.invert_yaxis()
axt.axvline(365, color=WARN, lw=0.9, ls="--")
for i, p in enumerate(tail):
    axt.text(p["diff"] + 20, i, f"{p['diff']:,}", va="center", fontsize=7, color=INK2)
axt.set_xlim(0, max(p["diff"] for p in tail) * 1.22)
axt.set_xlabel("Days"); axt.grid(True, axis="x", color=GRID, lw=0.6); axt.set_axisbelow(True)
axt.set_title(f"b. Tail: {len(tail)} drugs beyond 365 d (all ongoing)", loc="left", fontsize=8.8, color=INK)
fig.suptitle("Figure 2. How far recorded posting dates precede archive-observed onset, 173 drugs", x=0.01, ha="left", fontsize=9.5, color=INK, y=0.995)
fig.tight_layout(rect=(0.01, 0.02, 0.99, 0.94))
fig.savefig(f"{OUT}/fig2_paired_onset_differences.pdf"); fig.savefig(f"{OUT}/fig2_paired_onset_differences.png"); plt.close(fig)

# ------------------------------------------------------------------ Figure 3
R = list(csv.DictReader(open("stage4_compare/rank_stability.csv")))
rows = [r for r in R if r["tier"] in ("DEFINITE", "POSSIBLE")]
n_unrank = sum(1 for r in R if r["tier"].startswith("UNRANKABLE"))
def dur(r): return int(r["R1_days"])
rows.sort(key=lambda r: (r["tier"] != "DEFINITE", -dur(r)))
fig, ax = plt.subplots(figsize=(7.2, 5.6), dpi=300)
cols = [("in_R1_top20", "R1\nrecorded posting"), ("in_R2_earliest_top20", "R2\nearliest onset"), ("in_R2_latest_top20", "R2\nlatest onset")]
for i, r in enumerate(rows):
    for j, (k, _) in enumerate(cols):
        on = r[k] == "1"
        ax.scatter(j, i, s=70 if on else 40, facecolor=BLUE if on else "white", edgecolor=BLUE if on else INK2, linewidths=0.9, zorder=3)
    lab = r["generic"].replace(" Injection", " inj.").replace(" Hydrochloride", " HCl").replace("Sodium Chloride", "NaCl")[:40]
    ax.text(-0.35, i, lab, ha="right", va="center", fontsize=7.4, color=INK)
    ax.text(2.45, i, f"{int(r['R1_days']):,} / {int(r['R2_latest_days']):,} d", ha="left", va="center", fontsize=7, color=INK2)
n_def = sum(1 for r in rows if r["tier"] == "DEFINITE")
ax.axhline(n_def - 0.5, color=INK2, lw=0.7, ls=":")
ax.text(3.35, (n_def - 1) / 2, f"DEFINITE\n(all three scenarios)\nn = {n_def}", va="center", fontsize=7.6, color=INK)
ax.text(3.35, n_def + (len(rows) - n_def - 1) / 2, f"POSSIBLE\n(some scenarios)\nn = {len(rows) - n_def}", va="center", fontsize=7.6, color=INK)
ax.set_xticks(range(3)); ax.set_xticklabels([c[1] for c in cols], fontsize=7.8)
ax.set_xlim(-0.5, 4.2); ax.set_ylim(len(rows) - 0.5, -0.8); ax.set_yticks([])
for sp in ("left", "bottom"): ax.spines[sp].set_visible(False)
ax.tick_params(axis="x", length=0); ax.xaxis.set_ticks_position("top")
ax.text(2.45, -0.75, "R1 / R2-latest\nduration", ha="left", va="bottom", fontsize=7, color=INK2)
fig.text(0.01, 0.01, f"Filled dot = in the top 20 under that scenario. Universe: 173 drugs with a decidable exit; "
         f"{n_unrank} ambiguous-exit drugs are outside the universe (unrankable). Durations for ongoing drugs are elapsed observation times.",
         fontsize=7, color=INK2, wrap=True)
fig.suptitle("Figure 3. Top-20 persistence membership under three onset definitions", x=0.01, ha="left", fontsize=9.5, color=INK, y=0.995)
fig.tight_layout(rect=(0, 0.05, 1, 0.96))
fig.savefig(f"{OUT}/fig3_rank_stability.pdf"); fig.savefig(f"{OUT}/fig3_rank_stability.png"); plt.close(fig)

# ------------------------------------------------------------------ Figure 1
fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=300); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
def box(x, y, w, h, title, body, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fill, ec=INK2, lw=0.9, zorder=2))
    ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="top", fontsize=7.8, color=INK, weight="bold", zorder=3)
    ax.text(x + w / 2, y + h / 2 - 1.5, body, ha="center", va="center", fontsize=6.9, color=INK2, zorder=3, linespacing=1.3)
def arrow(x1, y1, x2, y2, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, color=INK2, lw=0.9, zorder=1))
    if label: ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.8, label, ha="center", fontsize=6.4, color=INK2)
# sources row
box(2, 78, 30, 18, "FDA Drug Shortage archive", "38 Internet Archive captures\n29 Dec 2019 – 21 Dec 2023\ngaps up to 308 d", "#eef3f8")
box(35, 78, 30, 18, "ASHP resolved bulletins", "958 bulletins, 2015–2026\ncreated and last-revised dates", "#eef3f8")
box(68, 78, 30, 18, "FDA Orange Book + NDC Directory", "product identity: application,\napplicant, form, route, strength", "#eef3f8")
# reconstruction row
box(2, 50, 30, 20, "Product episodes", "2,042 NDC episodes\n→ 298 drug headings\n(median 4 NDCs/drug, max 96)")
box(35, 50, 30, 20, "Two-level record linkage", "L1 identity: 327 HIGH / 17 MED / 74 LOW\nL2 spell: 27 CONFIRMED / 70 PROBABLE\n/ 69 AMBIGUOUS")
box(68, 50, 30, 20, "Harmonised markets (Appx C)", "304 form/route labels → 179 groups\nbounded applicant counts")
arrow(17, 78, 17, 70.5); arrow(50, 78, 50, 70.5); arrow(83, 78, 83, 70.5); arrow(32, 60, 35, 60); arrow(68, 60, 65, 60)
# cohort row
box(2, 22, 45, 20, "Entry-identifiable cohort: 184 drugs", "posting after first capture and entry bracketed\n51 resolved · 113 ongoing · 9 disappeared · 11 ambiguous exit\n→ analytical cohort 173 (ambiguous retained as a status)")
box(53, 22, 45, 20, "Left-censored: 114 drugs", "present at first capture or posted before it\nused for prevalence only, not onset-anchored duration")
arrow(17, 50, 17, 42.5); arrow(28, 50, 70, 42.5)
# rules row
box(2, 2, 96, 14, "Reconstruction rules compared on the 173-drug cohort with one shared exit rule",
    "R0 NDC-level (pseudoreplication demonstration) · R1 drug, recorded posting · R2 drug, archive-observed onset interval · R3 hybrid ASHP onset / FDA exit (linkage coverage only)")
arrow(24, 22, 40, 16.5); arrow(50, 42, 50, 36.5)
fig.suptitle("Figure 1. Sources, linkage, cohort selection and reconstruction workflow", x=0.01, ha="left", fontsize=9.5, color=INK, y=0.99)
fig.savefig(f"{OUT}/fig1_workflow.pdf", bbox_inches="tight"); fig.savefig(f"{OUT}/fig1_workflow.png", bbox_inches="tight"); plt.close(fig)
print("written:", sorted(os.listdir(OUT)))
print(f"fig2: body n={len(body)}, tail n={len(tail)}, median {med}, q1 {q1}, q3 {q3}, max {max(diffs)}")
print(f"fig3: rows {len(rows)} (definite {n_def}), unrankable {n_unrank}")
