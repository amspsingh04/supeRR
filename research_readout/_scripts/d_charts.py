"""10_charts: matplotlib PNGs on a white background, one folder per slide."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import COMPONENTS, LABEL, LEGACY_WEIGHTS, OUT, WEIGHTS, Registry, load  # noqa: E402

reg = Registry("d")
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 12, "axes.titleweight": "bold"})
C = {"bat": "#1f4e79", "bowl": "#b5462f", "grey": "#8c8c8c", "pace": "#c0504d", "spin": "#4f81bd", "top": "#2e75b6", "middle": "#70ad47", "lower": "#ed7d31",
     "accent": "#7030a0"}
COMP_COLORS = {"baseline": "#4472c4", "band_zero": "#a5a5a5", "band_medium": "#ffc000", "band_high": "#c00000", "clutch": "#7030a0", "peers": "#70ad47", "consistency": "#264478"}
P = load()
legal = P["legal"]
L = pd.read_pickle(OUT / "_cache" / "legal_shock.pkl")
CH = OUT / "10_charts"


def save(fig, folder, name, source, method):
    path = CH / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    reg.note(f"10_charts/{folder}/{name}", source, method)


def foot(ax, text, y=-0.27):
    ax.annotate(text, xy=(0, y), xycoords="axes fraction", fontsize=7.5, color="#555555", ha="left", va="top")


# slide 02 dataset
cs = pd.read_csv(OUT / "01_dataset/cleaning_summary.csv").set_index("metric")["value"]
vals = [int(cs["silver_deliveries"]), int(cs["illegal_deliveries_wide_noball_other"]), int(cs["legal_balls_used_in_ratings"]), int(cs["super_over_legal_balls_included"])]
fig, ax = plt.subplots(figsize=(8, 4))
labels = ["All deliveries", "Wides, no-balls,\n'other' (not legal)", "Legal balls\nused in ratings", "of which\nsuper-over balls"]
bars = ax.bar(labels, vals, color=[C["grey"], "#d9d9d9", C["bat"], C["bowl"]])
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=10)
ax.set_ylabel("Deliveries")
ax.set_title("From raw deliveries to legal balls")
foot(ax, f"Source: silver/ball_by_ball.csv via player_ratings.add_situation. No delivery is deleted in cleaning; illegal deliveries are excluded from ball value.\nSuper overs are kept: {int(cs['super_over_deliveries_included'])} deliveries in {int(cs['super_over_matches'])} matches.")
save(fig, "slide_02_dataset", "cleaning_funnel.png", "01_dataset/cleaning_summary.csv", "bar")

tab = legal.groupby(["season", "ladder"]).size().unstack().reindex(columns=["IPL", "T20I", "T20"]).fillna(0)
fig, ax = plt.subplots(figsize=(8, 4))
bottom = np.zeros(len(tab))
for lad, col in zip(tab.columns, [C["bat"], C["bowl"], C["grey"]]):
    ax.bar(tab.index.astype(str), tab[lad], bottom=bottom, color=col, label={"T20": "T20 (Emerging/Rising, weight 0.5)"}.get(lad, lad))
    bottom += tab[lad].to_numpy()
for x, t in zip(tab.index.astype(str), bottom):
    ax.text(x, t, f"{int(t):,}", ha="center", va="bottom", fontsize=9)
ax.set_ylabel("Legal balls")
ax.set_title("Legal balls by season and ladder")
ax.legend(frameon=False, fontsize=9)
foot(ax, f"Source: legal frame ({len(legal):,} legal balls, super overs included). Seasons use the earlier year of split seasons.")
save(fig, "slide_02_dataset", "legal_balls_by_season_ladder.png", "legal frame", "stacked bar")

# slide 03 pressure
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(L["pressure_bat"], bins=120, color=C["bat"], alpha=0.85)
p50, p80 = L["pressure_bat"].quantile(0.5), L["pressure_bat"].quantile(0.8)
for v, t in [(p50, f"p50 = {p50:.3f}"), (p80, f"p80 = {p80:.3f}")]:
    ax.axvline(v, color="black", ls="--", lw=1)
    ax.text(v, ax.get_ylim()[1] * 0.92, " " + t, fontsize=9)
ax.set_xlabel("Batter pressure (final, after the expected-wicket shock term)")
ax.set_ylabel("Legal balls")
ax.set_title("Batter pressure distribution and band cut-offs")
foot(ax, "Zero band < p50 <= medium < p80 <= high. Source: legal frame after fit_elo.")
save(fig, "slide_03_pressure", "batter_pressure_histogram.png", "02_pressure/pressure_percentiles.csv", "histogram")

sop = pd.read_csv(OUT / "02_pressure/super_over_pressure.csv")
sop["label"] = sop["match_id"].astype(str) + " " + sop["stage"] + " inn " + sop["innings"].astype(str)
order = list(dict.fromkeys(sop["label"]))
fig, ax = plt.subplots(figsize=(9, 4.2))
for i, lab in enumerate(order):
    part = sop.loc[sop["label"].eq(lab)]
    ax.scatter(np.full(len(part), i) + np.linspace(-0.2, 0.2, len(part)), part["pressure_bat"], color=C["bat"], s=28, zorder=3)
ax.axhline(p50, color="black", ls=":", lw=1)
ax.axhline(p80, color="black", ls="--", lw=1)
ax.text(len(order) - 0.5, p80 + 0.04, f"high cut p80 = {p80:.3f}", fontsize=8, ha="right", va="bottom")
ax.text(len(order) - 0.5, p50 + 0.04, f"medium cut p50 = {p50:.3f}", fontsize=8, ha="right", va="bottom")
ax.set_xticks(range(len(order)))
ax.set_xticklabels(order, rotation=30, ha="right", fontsize=8)
ax.set_ylim(min(-0.1, sop["pressure_bat"].min() - 0.1), p80 + 0.4)
ax.set_ylabel("Batter pressure")
ax.set_title("Super-over balls: knockout occasion, but no shock yet")
foot(ax, "Each dot is a legal super-over ball. Occasion = max(stage occasion, 1.5); death phase; chase rate in innings 4. Shock and run of play reset at the start\nof the innings, so every super-over ball sits in the medium band. Source: 02_pressure/super_over_pressure.csv.", y=-0.45)
save(fig, "slide_03_pressure", "super_over_pressure.png", "02_pressure/super_over_pressure.csv", "strip plot")

fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, arm in zip(axes, ["Pace", "Spin"]):
    s = L.loc[L["pace_or_spin"].eq(arm), "pressure_bowl"]
    ax.hist(s, bins=100, color=C[arm.lower()], alpha=0.85)
    for q in (0.5, 0.8):
        ax.axvline(s.quantile(q), color="black", ls="--", lw=1)
        ax.text(s.quantile(q), ax.get_ylim()[1] * 0.9, f" p{int(q * 100)} = {s.quantile(q):.3f}", fontsize=8.5)
    ax.set_title(f"{arm}: bowler pressure")
    ax.set_xlabel("Bowler pressure")
axes[0].set_ylabel("Legal balls")
foot(axes[0], "Bowler bands are cut separately within pace and within spin. Source: legal frame after fit_elo.")
save(fig, "slide_03_pressure", "bowler_pressure_pace_spin.png", "02_pressure/pressure_band_summary.csv", "histogram")

ph = pd.read_csv(OUT / "02_pressure/phase_bowling_pressure.csv")
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(3)
for i, arm in enumerate(["Pace", "Spin"]):
    sub = ph.loc[ph["arm"].eq(arm)].set_index("phase").reindex(["powerplay", "middle", "death"])
    b = ax.bar(x + (i - 0.5) * 0.38, sub["share_bowler_high"] * 100, 0.38, color=C[arm.lower()], label=arm)
    for rect, n, v in zip(b, sub["legal_balls"], sub["share_bowler_high"] * 100):
        ax.text(rect.get_x() + rect.get_width() / 2, v, f"{v:.1f}%\n(n={int(n):,})", ha="center", va="bottom", fontsize=8)
ax.set_xticks(x, ["Powerplay", "Middle", "Death"])
ax.set_ylabel("Share of balls in the bowler high band (%)")
ax.set_ylim(0, 32)
ax.axhline(20, color=C["grey"], lw=0.8, ls=":")
ax.set_title("Bowler high-pressure share by phase and arm")
ax.legend(frameon=False)
foot(ax, "Dotted line: 20% (the high band is the top fifth within each arm). Source: 02_pressure/phase_bowling_pressure.csv")
save(fig, "slide_03_pressure", "phase_arm_high_share.png", "02_pressure/phase_bowling_pressure.csv", "grouped bar")

# slide 04 what high pressure captures
se = pd.read_csv(OUT / "06_shock/shock_event_summary.csv").dropna(subset=["metric"]).set_index("metric")["value"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
ax = axes[0]
v = [se["batter_high_band_share_within_6_after_wicket"] * 100, se["batter_high_band_share_otherwise"] * 100]
b = ax.bar(["Within 6 balls\nafter a wicket", "All other balls"], v, color=[C["bat"], C["grey"]])
for rect, val in zip(b, v):
    ax.text(rect.get_x() + rect.get_width() / 2, val, f"{val:.2f}%", ha="center", va="bottom")
ax.set_ylabel("Share of balls in the batter high band (%)")
ax.set_title("Batter high band = just after a wicket")
ax = axes[1]
v = [se["share_of_bowler_high_band_balls_with_four_or_six_in_last_6"] * 100, se["share_of_bowler_zero_band_balls_with_four_or_six_in_last_6"] * 100]
b = ax.bar(["Bowler high band", "Bowler zero band"], v, color=[C["bowl"], C["grey"]])
for rect, val in zip(b, v):
    ax.text(rect.get_x() + rect.get_width() / 2, val, f"{val:.2f}%", ha="center", va="bottom")
ax.set_ylabel("Balls with a four or six in the previous 6 (%)")
ax.set_title("Bowler high band = just after a boundary")
foot(axes[0], f"{se['share_of_batter_high_band_balls_within_6_after_wicket'] * 100:.2f}% of batter high-band balls fall within 6 balls of a wicket. Source: 06_shock/shock_event_summary.csv")
save(fig, "slide_04_high_pressure_meaning", "high_band_triggers.png", "06_shock/shock_event_summary.csv", "bar")

bs = pd.read_csv(OUT / "02_pressure/pressure_band_summary.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
sub = bs.loc[bs["scope"].eq("batter_all")]
axes[0].bar(sub["band"], sub["strike_rate"], color=[C["grey"], "#ffc000", "#c00000"])
for i, (sr, o) in enumerate(zip(sub["strike_rate"], sub["striker_out_rate"])):
    axes[0].text(i, sr, f"SR {sr:.1f}\nout {o * 100:.2f}%", ha="center", va="bottom", fontsize=8.5)
axes[0].set_title("Batters: strike rate by band")
axes[0].set_ylabel("Strike rate (bat runs per 100 legal balls)")
axes[0].set_ylim(0, 175)
for j, arm in enumerate(["pace", "spin"]):
    sub = bs.loc[bs["scope"].eq(f"bowler_{arm}")]
    xs = np.arange(3) + (j - 0.5) * 0.38
    axes[1].bar(xs, sub["economy_legal_balls"], 0.38, color=C[arm], label=arm.title())
    for xx, e in zip(xs, sub["economy_legal_balls"]):
        axes[1].text(xx, e, f"{e:.2f}", ha="center", va="bottom", fontsize=8.5)
axes[1].set_xticks(np.arange(3), ["zero", "medium", "high"])
axes[1].set_title("Bowlers: economy by band (legal balls)")
axes[1].set_ylabel("Runs per over charged on legal balls")
axes[1].legend(frameon=False)
foot(axes[0], "Source: 02_pressure/pressure_band_summary.csv. Bowler economy here excludes wide and no-ball runs (legal balls only).")
save(fig, "slide_04_high_pressure_meaning", "outcomes_by_band.png", "02_pressure/pressure_band_summary.csv", "bar")

# slide 05 expectation models
xr = pd.read_csv(OUT / "05_expectation_models/xruns_calibration_deciles.csv")
xw = pd.read_csv(OUT / "05_expectation_models/xwickets_calibration_deciles.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
sub = xr.loc[xr["scope"].eq("all") & xr["target"].str.startswith("bat_runs")]
axes[0].plot(sub["mean_predicted"], sub["mean_actual"], "o-", color=C["bat"], label="bat runs")
lim = [sub["mean_predicted"].min() * 0.95, sub["mean_predicted"].max() * 1.05]
axes[0].plot(lim, lim, color=C["grey"], ls="--", lw=1, label="perfect calibration")
axes[0].set_xlabel("Mean predicted xR (decile)")
axes[0].set_ylabel("Mean actual bat runs per ball")
axes[0].set_title("xRuns calibration by decile")
axes[0].legend(frameon=False)
for tgt, col, lab in [("bowler_wicket", C["bowl"], "bowler wicket (training target)"), ("striker_out", C["bat"], "striker out (used for batters)")]:
    sub = xw.loc[xw["scope"].eq("all") & xw["target"].str.startswith(tgt)]
    axes[1].plot(sub["mean_predicted"] * 100, sub["mean_actual"] * 100, "o-", color=col, label=lab)
lim = [3, 9.5]
axes[1].plot(lim, lim, color=C["grey"], ls="--", lw=1)
axes[1].set_xlabel("Mean predicted xW (%)")
axes[1].set_ylabel("Actual rate (%)")
axes[1].set_title("xWicket calibration by decile")
axes[1].legend(frameon=False, fontsize=8.5)
foot(axes[0], "Sequential predictions made inside run_elo using only earlier balls. Source: 05_expectation_models/*_calibration_deciles.csv")
save(fig, "slide_05_expectation_models", "calibration_deciles.png", "05_expectation_models", "decile calibration")

rw = pd.read_csv(OUT / "05_expectation_models/residual_by_wickets_fallen.csv")
sub = rw.loc[rw["phase"].eq("all")]
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(sub))
ax.bar(x - 0.2, sub["mean_e_bat"], 0.4, color=C["bat"], label="mean batter ball value")
ax.bar(x + 0.2, sub["mean_e_bowl"], 0.4, color=C["bowl"], label="mean bowler ball value")
ax.set_ylim(-0.5, 0.5)
for xx, n in zip(x, sub["legal_balls"]):
    ax.text(xx, 0.45, f"n={int(n):,}", ha="center", fontsize=8)
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x, sub["wickets_before"])
ax.set_xlabel("Wickets down before the ball")
ax.set_ylabel("Mean ball value (runs-equivalent)")
ax.set_title("Ball value drifts with wickets fallen (not in the expectation model)")
ax.legend(frameon=False, loc="lower left")
foot(ax, "The expectation cells are ladder x phase x arm only. Source: 05_expectation_models/residual_by_wickets_fallen.csv")
save(fig, "slide_05_expectation_models", "ball_value_by_wickets_fallen.png", "05_expectation_models/residual_by_wickets_fallen.csv", "bar")

# slide 06 elo
bh = pd.read_csv(OUT / "04_elo/batter_elo_history.csv")
wh = pd.read_csv(OUT / "04_elo/bowler_elo_history.csv")
for frame, players, fname, title in [(bh, ["Jos Buttler", "Virat Kohli", "David Miller", "Rilee Rossouw"], "batter_elo_trajectories.png", "Batter Elo paths"),
                                     (wh, ["Jasprit Bumrah", "Rashid Khan", "Matthew Humphreys", "Corbin Bosch"], "bowler_elo_trajectories.png", "Bowler Elo paths")]:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, ladder in zip(axes, ["IPL", "T20I"]):
        for i, name in enumerate(players):
            sub = frame.loc[frame["player_name"].eq(name) & frame["ladder"].eq(ladder)]
            if len(sub) < 30:
                continue
            ax.plot(sub["seq_in_ladder"], sub["rating_after_raw"], lw=1.2, label=f"{name} ({len(sub)} balls)", color=plt.cm.tab10(i))
        ax.axhline(1500, color=C["grey"], ls=":", lw=1)
        ax.set_title(f"{title}: {ladder}")
        ax.set_xlabel("Legal balls in this ladder")
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel("Raw Elo after ball")
    foot(axes[0], "Ratings are kept separately per ladder; start 1500; steps 4/16 (runs/wicket), not halved. Paths with < 30 balls omitted.")
    save(fig, "slide_06_elo", fname, "04_elo histories", "line")

# slide 07 shock timeline
tl = pd.read_csv(OUT / "06_shock/shock_innings_timeline.csv")
fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
ax = axes[0]
ax.plot(tl["legal_ball_n"], tl["pressure_bat"], color=C["bat"], label="batter pressure")
ax.plot(tl["legal_ball_n"], tl["pressure_bowl"], color=C["bowl"], label="bowler pressure")
ax.axhline(L["pressure_bat"].quantile(0.8), color=C["bat"], ls=":", lw=1, label="batter high cut (p80)")
for i, n in enumerate(tl.loc[tl["is_wicket"].eq(1), "legal_ball_n"]):
    for a in axes:
        a.axvline(n, color="black", lw=0.8, alpha=0.6)
    ax.text(n, 5.3 + 0.35 * (i % 2), f"W{n}", ha="center", fontsize=7.5)
ax.set_ylim(top=6.0)
ax.set_ylabel("Pressure")
ax.set_title("IPL 2025 final, PBKS chase of 191: pressure by legal ball")
ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
ax = axes[1]
ax.plot(tl["legal_ball_n"], tl["shock_bat"], color=C["bat"], label="batter shock (count + excess)")
ax.plot(tl["legal_ball_n"], tl["shock_bowl"], color=C["bowl"], label="bowler shock")
ax.plot(tl["legal_ball_n"], tl["run_of_play_bowl"], color=C["accent"], lw=0.9, ls="--", label="bowler run of play")
ax.set_ylabel("Shock / run of play")
ax.set_xlabel("Legal ball of the innings")
ax.legend(frameon=False, fontsize=8, ncol=3, loc="lower right")
foot(ax, "Vertical lines: wickets at legal balls 30, 51, 58, 73, 98, 100, 104. Ball 19 run of play is pinned at 1.0 by the indexing bug. Source: 06_shock/shock_innings_timeline.csv")
save(fig, "slide_07_shock", "ipl2025_final_shock_timeline.png", "06_shock/shock_innings_timeline.csv", "line")

# slide 08 components and weights
infl = pd.read_csv(OUT / "08_validation/component_influence.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
x = np.arange(len(COMPONENTS))
cur = [WEIGHTS[c] for c in COMPONENTS]
leg = [LEGACY_WEIGHTS[c] for c in COMPONENTS]
axes[0].bar(x - 0.2, cur, 0.4, color=C["bat"], label="current (7 terms)")
axes[0].bar(x + 0.2, leg, 0.4, color=C["grey"], label="git 29956ed (8 terms, Form 0.05 not shown)")
axes[0].set_xticks(x, [LABEL[c] for c in COMPONENTS], rotation=35, ha="right")
axes[0].set_ylabel("Nominal weight")
axes[0].set_title("Composite weights")
axes[0].legend(frameon=False, fontsize=8)
for j, skill in enumerate(["batter", "bowler"]):
    sub = infl.loc[infl["skill"].eq(skill)].set_index("component").reindex(COMPONENTS)
    axes[1].bar(x + (j - 0.5) * 0.4, sub["variance_share_of_composite"] * 100, 0.4, color=C["bat" if skill == "batter" else "bowl"], label=f"{skill}s")
axes[1].set_xticks(x, [LABEL[c] for c in COMPONENTS], rotation=35, ha="right")
axes[1].set_ylabel("Share of composite variance (%)")
axes[1].set_title("Realised influence among ranked players")
axes[1].axhline(0, color="black", lw=0.8)
axes[1].legend(frameon=False, fontsize=8)
foot(axes[0], "Variance share = cov(w*z, composite)/var(composite). Source: 03_components, 08_validation/component_influence.csv")
save(fig, "slide_08_components", "weights_and_influence.png", "08_validation/component_influence.csv", "bar")

dist = pd.read_csv(OUT / "07_rankings/composite_distribution.csv")
fig, ax = plt.subplots(figsize=(8, 4))
for skill, col in [("batter", C["bat"]), ("bowler", C["bowl"])]:
    s = P["batters" if skill == "batter" else "bowlers"]
    s = s.loc[s["ranked"], "composite"]
    ax.hist(s, bins=30, alpha=0.6, color=col, label=f"ranked {skill}s (n={len(s)})")
ax.set_xlabel("Composite score")
ax.set_ylabel("Players")
ax.set_title("Composite score distribution")
ax.legend(frameon=False)
foot(ax, "Composite = weighted sum of capped z-scores. Source: 07_rankings/composite_distribution.csv")
save(fig, "slide_08_components", "composite_distribution.png", "07_rankings/composite_distribution.csv", "histogram")

# slides 09/10 rankings
for skill, fname, folder in [("batter", "top10_batters_contributions.png", "slide_09_top_batters"), ("bowler", "top10_bowlers_contributions.png", "slide_10_top_bowlers")]:
    top = pd.read_csv(OUT / f"07_rankings/top10_{skill}s.csv").iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5))
    left_pos = np.zeros(len(top))
    left_neg = np.zeros(len(top))
    y = np.arange(len(top))
    for comp in COMPONENTS:
        v = top[f"contrib_{comp}"].to_numpy()
        pos = np.where(v > 0, v, 0)
        neg = np.where(v < 0, v, 0)
        ax.barh(y, pos, left=left_pos, color=COMP_COLORS[comp], label=LABEL[comp])
        ax.barh(y, neg, left=left_neg, color=COMP_COLORS[comp])
        left_pos += pos
        left_neg += neg
    ax.scatter(top["composite"], y, color="black", zorder=3, s=18, label="composite")
    ax.set_yticks(y, [f"{int(r)}. {n} ({ro})" for r, n, ro in zip(top["rank"], top["player_name"], top["role"])])
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Contribution to composite (weight x z)")
    ax.set_title(f"Top 10 {skill}s: what builds the score")
    ax.legend(frameon=False, fontsize=8, ncol=8, loc="upper center", bbox_to_anchor=(0.4, -0.12))
    foot(ax, f"Source: 07_rankings/top10_{skill}s.csv (current 7-term model).", y=-0.22)
    save(fig, folder, fname, f"07_rankings/top10_{skill}s.csv", "stacked bar")

# slide 11 sanity
sp = pd.read_csv(OUT / "08_validation/sanity_check_players.csv")
fig, ax = plt.subplots(figsize=(10, 5.5))
sub = sp.sort_values(["skill", "composite"], ascending=[True, True]).reset_index(drop=True)
cols = [C["bat"] if s == "batter" else C["bowl"] for s in sub["skill"]]
ax.barh(np.arange(len(sub)), sub["composite"], color=cols, alpha=[1.0 if r else 0.35 for r in sub["ranked"]] if False else 0.9)
for i, r in sub.iterrows():
    txt = f"rank {int(r['rank'])}/{int(r['ranked_pool'])}" if r["ranked"] else f"not ranked ({r['reason_not_ranked']})"
    ax.text(r["composite"] + (0.02 if r["composite"] >= 0 else -0.02), i, txt, va="center", ha="left" if r["composite"] >= 0 else "right", fontsize=8)
ax.set_yticks(np.arange(len(sub)), [f"{n} ({s})" for n, s in zip(sub["player_name"], sub["skill"])])
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Composite score")
ax.set_title("Sanity-check players: composite and rank")
foot(ax, "Blue = batting rating, red = bowling rating. Source: 08_validation/sanity_check_players.csv")
save(fig, "slide_11_sanity_checks", "sanity_players.png", "08_validation/sanity_check_players.csv", "bar")

# slide 12 ablation
vb = pd.read_csv(OUT / "08_validation/ablation_batter_rank_changes.csv")
vw = pd.read_csv(OUT / "08_validation/ablation_bowler_rank_changes.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, frame, skill, hl in [(axes[0], vb, "batters", ["Vaibhav Sooryavanshi", "Rahmanullah Gurbaz", "Rilee Rossouw"]), (axes[1], vw, "bowlers", ["Corbin Bosch", "Matthew Humphreys", "Jasprit Bumrah"])]:
    ax.scatter(frame["baseline_only"], frame["full_current"], s=10, color=C["grey"])
    n = len(frame)
    ax.plot([1, n], [1, n], color="black", lw=0.8, ls="--")
    for name in hl:
        r = frame.loc[frame["player_name"].eq(name)]
        if len(r):
            ax.scatter(r["baseline_only"], r["full_current"], s=30, color=C["accent"])
            ax.annotate(f"{name}\n({int(r['baseline_only'].iloc[0])} -> {int(r['full_current'].iloc[0])})", (r["baseline_only"].iloc[0], r["full_current"].iloc[0]),
                        fontsize=7.5, xytext=(5, 5), textcoords="offset points")
    ax.invert_xaxis()
    ax.invert_yaxis()
    ax.set_xlabel("Rank on baseline only")
    ax.set_ylabel("Rank on full composite")
    ax.set_title(f"Ranked {skill}: baseline-only vs full")
foot(axes[0], "Source: 08_validation/ablation_*_rank_changes.csv")
save(fig, "slide_12_ablation", "baseline_vs_full_rank.png", "08_validation/ablation_*_rank_changes.csv", "scatter")

ab = pd.read_csv(OUT / "08_validation/ablation_summary.csv")
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
order = [v for v in ab.loc[ab["skill"].eq("batter"), "variant"]]
for k, (ax, skill) in enumerate(zip(axes, ["batter", "bowler"])):
    sub = ab.loc[ab["skill"].eq(skill)].set_index("variant").reindex(order)
    y = np.arange(len(order))
    ax.barh(y, sub["top20_overlap"], color=[C["accent"] if v.startswith("diagnostic") else (C["bat"] if skill == "batter" else C["bowl"]) for v in order])
    for yy, (o, rho) in enumerate(zip(sub["top20_overlap"], sub["spearman_vs_full"])):
        if pd.notna(o):
            ax.text(o + 0.2, yy, f"{int(o)}/20  rho={rho:.3f}", va="center", fontsize=7.5)
    ax.set_yticks(y, order if k == 0 else [""] * len(order), fontsize=8)
    ax.set_xlim(0, 30)
    ax.invert_yaxis()
    ax.set_xlabel("Top-20 overlap with the official ranking")
    ax.set_title(f"{skill.title()}s")
foot(axes[0], "rho = Spearman vs official among ranked players. Purple = diagnostic (ball-19 bug removed), not official. Source: 08_validation/ablation_summary.csv")
save(fig, "slide_12_ablation", "ablation_overlap.png", "08_validation/ablation_summary.csv", "bar")

# slide 13 correlations
for skill in ["batters", "bowlers"]:
    cm = pd.read_csv(OUT / f"08_validation/component_correlation_{skill}.csv")
    cm = cm.loc[cm["method"].eq("pearson")].set_index("component")[COMPONENTS + ["composite"]].loc[COMPONENTS + ["composite"]]
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm.to_numpy(dtype=float), cmap="RdBu_r", vmin=-1, vmax=1)
    labs = [LABEL.get(c, c.title()) for c in cm.columns]
    ax.set_xticks(range(len(labs)), labs, rotation=45, ha="right")
    ax.set_yticks(range(len(labs)), labs)
    for i in range(len(labs)):
        for j in range(len(labs)):
            ax.text(j, i, f"{cm.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8, color="white" if abs(cm.iloc[i, j]) > 0.6 else "black")
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(f"Component correlations, ranked {skill} (Pearson)")
    save(fig, "slide_13_component_correlations", f"correlation_{skill}.png", f"08_validation/component_correlation_{skill}.csv", "heatmap")

# slide 14 roles
rr = pd.read_csv(OUT / "08_validation/role_ranking_representation.csv")
fig, ax = plt.subplots(figsize=(9, 4.2))
labels = ["current_with_role_split", "current_without_role_split", "legacy_8term_with_role_split", "legacy_8term_without_role_split"]
nice = ["Current, role-split z", "Current, pooled z", "Legacy 8-term, role-split z", "Legacy 8-term, pooled z"]
y = np.arange(len(labels))
left = np.zeros(len(labels))
for role in ["top", "middle", "lower"]:
    v = [int(rr.loc[rr["ranking"].eq(l) & rr["top_k"].astype(str).eq("20"), role].iloc[0]) for l in labels]
    ax.barh(y, v, left=left, color=C[role], label=f"{role} order")
    for yy, (lv, vv) in enumerate(zip(left, v)):
        if vv:
            ax.text(lv + vv / 2, yy, str(vv), ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    left += v
pool = P["batters"].loc[P["batters"]["ranked"], "role"].value_counts()
ax.set_yticks(y, nice)
ax.invert_yaxis()
ax.set_xlabel("Players in the batting top 20")
ax.set_title("Batting top 20 by role")
ax.legend(frameon=False, ncol=3, loc="lower right", fontsize=8)
foot(ax, f"Ranked pool: top {pool.get('top order', 0)}, middle {pool.get('middle order', 0)}, lower {pool.get('lower order', 0)}. Source: 08_validation/role_ranking_representation.csv")
save(fig, "slide_14_roles", "top20_role_composition.png", "08_validation/role_ranking_representation.csv", "stacked bar")

cov = pd.read_csv(OUT / "08_validation/role_coverage.csv")
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(cov))
ax.bar(x - 0.2, cov["n_eff_ge_30_reference"], 0.4, color=C["grey"], label="reference pool (n_eff >= 30)")
ax.bar(x + 0.2, cov["ranked"], 0.4, color=C["bat"], label="ranked (n_eff >= 120 and high n_eff >= 30)")
for xx, a, b in zip(x, cov["n_eff_ge_30_reference"], cov["ranked"]):
    ax.text(xx - 0.2, a, str(int(a)), ha="center", va="bottom", fontsize=8)
    ax.text(xx + 0.2, b, str(int(b)), ha="center", va="bottom", fontsize=8)
ax.set_xticks(x, [f"{s}\n{r}" for s, r in zip(cov["skill"], cov["role"])])
ax.set_ylabel("Players")
ax.set_title("Who is eligible to be ranked")
ax.legend(frameon=False, fontsize=8)
foot(ax, "Source: 08_validation/role_coverage.csv")
save(fig, "slide_14_roles", "role_coverage.png", "08_validation/role_coverage.csv", "bar")

# slide 15 limitations: ball-19 bug
by_n = L.loc[L["n"].le(40)].groupby("n").agg(bat=("band", lambda s: s.eq("high").mean()), bowl=("band_bowl", lambda s: s.eq("high").mean()),
                                             rop_bowl=("delta_bowl", "mean"), rop_bowl_fix=("delta_bowl_bugfree_diagnostic", "mean"))
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].plot(by_n.index, by_n["bat"] * 100, "o-", ms=3, color=C["bat"], label="batter high band")
axes[0].plot(by_n.index, by_n["bowl"] * 100, "o-", ms=3, color=C["bowl"], label="bowler high band")
axes[0].axvline(19, color="black", ls=":", lw=1)
axes[0].set_xlabel("Legal ball of the innings")
axes[0].set_ylabel("Share in high band (%)")
axes[0].set_title("High-band share by ball number (balls 1-40)")
axes[0].legend(frameon=False, fontsize=8)
axes[1].plot(by_n.index, by_n["rop_bowl"], "o-", ms=3, color=C["bowl"], label="as executed")
axes[1].plot(by_n.index, by_n["rop_bowl_fix"], "o-", ms=3, color=C["grey"], label="bug removed (diagnostic)")
axes[1].axvline(19, color="black", ls=":", lw=1)
axes[1].set_xlabel("Legal ball of the innings")
axes[1].set_ylabel("Mean bowler run-of-play term")
axes[1].set_title("Run-of-play term: ball-19 indexing bug")
axes[1].legend(frameon=False, fontsize=8)
foot(axes[0], "No shock before ball 7 and no run of play before ball 19. Source: legal frame + section 02 replication.")
save(fig, "slide_15_limitations", "ball19_bug_and_early_balls.png", "02_pressure replication", "line")

reg.close()
print("d done")
