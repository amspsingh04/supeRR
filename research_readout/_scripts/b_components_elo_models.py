"""03_components, 04_elo, 05_expectation_models."""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

from common import (COMPONENTS, ELO_PLAYERS, LEGACY_WEIGHTS, ROOT, WEIGHTS, Registry, load, metric_row)

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import player_ratings as pr  # noqa: E402

reg = Registry("b")
P = load()
legal, work = P["legal"], P["work"]
bat, bowl = P["batters"].copy(), P["bowlers"].copy()
lbat, lbowl = P["legacy_batters"], P["legacy_bowlers"]
T, LT = P["traces"], P["legacy_traces"]

# ---------------------------------------------------------------- 03 components
BLEND_SCOPE = (f"batters: {pr.ROLE_BLEND} x z within top/middle/lower order + {1 - pr.ROLE_BLEND} x z across all batters (ROLE_BLEND); "
               "bowlers all together")
defs = pd.DataFrame([
    ("baseline", 0.20, 0.20, "batter: 0.5 z(shrunk SR - phase-expected SR) + 0.5 z(shrunk average - phase-expected average); bowler: 0.5 z(expected economy - shrunk economy) + 0.5 z(expected balls/wicket - shrunk balls/wicket)",
     "career totals, level-weighted (no season decay)", "SR and economy shrink to the phase(-arm) expectation with 120 balls; average and balls/wicket with 4 dismissals/wickets",
     BLEND_SCOPE, "score_batters / score_bowlers 'base'"),
    ("band_zero", 0.10, 0.10, "decay- and level-weighted mean ball value (e_bat or e_bowl) on balls in the zero pressure band",
     "season decay 0.9^(2026-season) x level weight", "shrunk to 0 with 30 weighted balls", BLEND_SCOPE, "career_rate + shrink + zscore_blend / zscore"),
    ("band_medium", 0.15, 0.15, "same, medium band", "same", "same", "same", "same"),
    ("band_high", 0.20, 0.20, "same, high band (top 20% of pressure; bowlers cut within pace and within spin)", "same", "same", "same", "same"),
    ("clutch", 0.15, 0.15, "per innings, high-band balls only (>=6 balls): own gap = (spell SR - career SR)/scale [bowler: (legal-ball career economy - legal-ball spell economy)/scale]; if gap>0 it is multiplied by max(teammate z,0)",
     "level-weighted mean over spells (no season decay)", "shrunk to 0 with 5 spells", BLEND_SCOPE, "_clutch_spell, innings_comparisons"),
    ("peers", 0.10, 0.10, "per innings (>=6 balls): mean of z vs teammates in the same innings and z vs the other side's players (capped +-3), on SR or economy",
     "level-weighted mean over innings (no season decay)", "shrunk to 0 with 5 innings", BLEND_SCOPE, "innings_comparisons"),
    ("consistency", 0.10, 0.05, "minus the level-weighted SD of match-mean ball value over matches with >=6 balls",
     "level-weighted (no season decay)", "SD shrunk toward the reference-pool typical SD with 8 matches", BLEND_SCOPE, "consistency_parts"),
    ("form", 0.00, 0.05, "REMOVED in the current code. Legacy: share of the previous 8 innings above the player's FULL-CAREER SR/economy minus 0.5 (look-ahead)",
     "legacy: decay x level weighted", "legacy: shrunk to 0 with 8 innings", "legacy: batters within order group", "git 29956ed form_by_season"),
], columns=["component", "weight_current", "weight_legacy_git_head", "raw_input", "aggregation_weighting", "shrinkage", "zscore_scope", "code"])
defs["zscore"] = "z on reference pool (n_eff >= 30 decay x level weighted legal balls), population SD, capped at +-3"
defs["status"] = np.where(defs["component"].eq("form"), "NOT_APPLICABLE", "EXISTING")
reg.save(defs, "03_components/component_definitions.csv", "player_ratings.py (working tree) and git 29956ed", "read from code")
reg.fact("weights_current_sum", float(sum(WEIGHTS.values())))
reg.fact("weights_legacy_sum", float(sum(LEGACY_WEIGHTS.values())))
reg.fact("legacy_weights_from_git", P["legacy_weights"])

summ = []
for skill, table, math in [("batter", bat, T["batters"]["math"]), ("bowler", bowl, T["bowlers"]["math"])]:
    ref = table["player_id"].map(math.set_index("player_id")["reference"]).astype(bool)
    for pop, mask in [("all", pd.Series(True, index=table.index)), ("reference_n_eff_ge_30", ref), ("ranked", table["ranked"].astype(bool))]:
        for comp in COMPONENTS + ["composite"]:
            s = table.loc[mask, comp].astype(float)
            summ.append({"skill": skill, "population": pop, "component": comp, "n": len(s), "mean": s.mean(), "sd": s.std(ddof=0),
                         "min": s.min(), "p25": s.quantile(0.25), "median": s.median(), "p75": s.quantile(0.75), "max": s.max(),
                         "share_at_plus3_cap": float(s.ge(3).mean()), "share_at_minus3_cap": float(s.le(-3).mean()),
                         "weight": WEIGHTS.get(comp, np.nan), "status": "COMPUTED"})
summ = pd.DataFrame(summ)
reg.save(summ, "03_components/component_summary.csv", "ratings tables from score_batters/score_bowlers", "describe by population")
for _, r in summ.loc[summ["population"].eq("ranked")].iterrows():
    reg.fact(f"comp_{r['skill']}_{r['component']}_ranked_sd", float(r["sd"]))
    reg.fact(f"comp_{r['skill']}_{r['component']}_ranked_capshare", float(r["share_at_plus3_cap"] + r["share_at_minus3_cap"]))


def scores(table, math, legacy, skill):
    out = table.merge(math.drop(columns=[c for c in ["runs", "balls", "strike_rate", "average", "legal_balls", "wickets", "economy", "balls_per_wicket"] if c in math.columns]),
                      on="player_id", how="left")
    leg = legacy[["player_id", "form", "consistency", "composite", "rank"]].rename(columns={
        "form": "legacy_form_z", "consistency": "legacy_consistency_z", "composite": "legacy_composite", "rank": "legacy_rank"})
    out = out.merge(leg, on="player_id", how="left")
    for comp in COMPONENTS:
        out[f"contrib_{comp}"] = out[comp] * WEIGHTS[comp]
    out["contrib_sum_check"] = out[[f"contrib_{c}" for c in COMPONENTS]].sum(axis=1) - out["composite"]
    out.insert(0, "skill", skill)
    return out


bscore = scores(bat, T["batters"]["math"], lbat, "batter")
wscore = scores(bowl, T["bowlers"]["math"], lbowl, "bowler")
reg.save(bscore, "03_components/batter_component_scores.csv", "score_batters table + TRACES math + git 29956ed legacy scoring", "join on player_id")
reg.save(wscore, "03_components/bowler_component_scores.csv", "score_bowlers table + TRACES math + git 29956ed legacy scoring", "join on player_id")
reg.fact("comp_sum_check_maxgap", float(max(bscore["contrib_sum_check"].abs().max(), wscore["contrib_sum_check"].abs().max())))

contrib = []
for frame in (bscore, wscore):
    ranked = frame.loc[frame["ranked"]].sort_values("rank")
    for _, r in ranked.iterrows():
        row = {"skill": r["skill"], "rank": int(r["rank"]), "player_id": r["player_id"], "player_name": r["player_name"], "role": r["role"], "composite": r["composite"]}
        for comp in COMPONENTS:
            row[f"z_{comp}"] = r[comp]
            row[f"contrib_{comp}"] = r[f"contrib_{comp}"]
        pos = sum(max(row[f"contrib_{c}"], 0) for c in COMPONENTS)
        row["largest_positive_component"] = max(COMPONENTS, key=lambda c: row[f"contrib_{c}"])
        row["largest_negative_component"] = min(COMPONENTS, key=lambda c: row[f"contrib_{c}"])
        row["pressure_share_of_positive_contribution"] = (sum(max(row[f"contrib_{c}"], 0) for c in ["band_medium", "band_high", "clutch"]) / pos) if pos > 0 else np.nan
        contrib.append(row)
contrib = pd.DataFrame(contrib)
reg.save(contrib, "03_components/component_contributions.csv", "ratings tables", "weight x z per component for ranked players")
for skill in ["batter", "bowler"]:
    top = contrib.loc[contrib["skill"].eq(skill) & contrib["rank"].le(10)]
    for comp in COMPONENTS:
        reg.fact(f"contrib_top10_{skill}_{comp}_mean", float(top[f"contrib_{comp}"].mean()))

# ---------------------------------------------------------------- 04 elo
order_cols = ["match_date", "match_id", "innings", "innings_ball_num"]
Lw = legal.sort_values(order_cols, kind="mergesort").reset_index(drop=True)


def history(id_col, name_col, after_col, skill):
    frames = []
    for name in ELO_PLAYERS:
        sub = Lw.loc[Lw[name_col].eq(name)].copy()
        if sub.empty:
            continue
        sub["seq_in_ladder"] = sub.groupby("ladder").cumcount() + 1
        sub["rating_before_raw"] = sub.groupby("ladder")[after_col].shift(1).fillna(1500.0)
        sub["balls_seen_before"] = sub["seq_in_ladder"] - 1
        sub["rating_before_effective"] = (sub["balls_seen_before"] * sub["rating_before_raw"] + 30 * 1500.0) / (sub["balls_seen_before"] + 30)
        sub["rating_change"] = sub[after_col] - sub["rating_before_raw"]
        sub["player_name"] = name
        sub["player_id"] = sub[id_col]
        sub["rating_after_raw"] = sub[after_col]
        keep = ["player_name", "player_id", "ladder", "match_date", "season", "comp_name", "match_id", "innings", "n", "seq_in_ladder",
                "bat_runs", "charged_runs", "striker_out", "bowler_wicket", "x_runs", "x_runs_bowl", "x_wicket",
                "e_bat" if skill == "batter" else "e_bowl", "rating_before_raw", "rating_before_effective", "rating_after_raw", "rating_change"]
        frames.append(sub[keep])
    out = pd.concat(frames, ignore_index=True)
    out["match_date"] = pd.to_datetime(out["match_date"]).dt.strftime("%Y-%m-%d")
    return out


bh = history("striker_id", "striker_name", "batter_rating_after", "batter")
wh = history("bowler_id", "bowler_name", "bowler_rating_after", "bowler")
reg.save(bh, "04_elo/batter_elo_history.csv", "legal frame after fit_elo (batter_rating_after)", "per-ball path; before = previous after in the same ladder, start 1500")
reg.save(wh, "04_elo/bowler_elo_history.csv", "legal frame after fit_elo (bowler_rating_after)", "same")

existing_traj = pd.read_csv(ROOT / "exports" / "13_player_trajectory.csv")
mine_traj = Lw.loc[Lw["striker_name"].eq("Jos Buttler"), "batter_rating_after"].to_numpy()
reg.fact("elo_buttler_trajectory_matches_export", bool(len(existing_traj) == len(mine_traj) and np.allclose(existing_traj["raw_rating"], mine_traj)))
reg.fact("elo_buttler_export_mixes_ladders", bool(Lw.loc[Lw["striker_name"].eq("Jos Buttler"), "ladder"].nunique() > 1))

stab = []
for skill, hist, val in [("batter", bh, "e_bat"), ("bowler", wh, "e_bowl")]:
    for (name, ladder), sub in hist.groupby(["player_name", "ladder"]):
        by_match = sub.groupby("match_id", sort=False).agg(start=("rating_before_raw", "first"), end=("rating_after_raw", "last"))
        move = by_match["end"] - by_match["start"]
        row = {"skill": skill, "player_name": name, "ladder": ladder, "balls": len(sub), "matches": int(sub["match_id"].nunique()),
               "final_raw": float(sub["rating_after_raw"].iloc[-1]),
               "final_effective": float((len(sub) * sub["rating_after_raw"].iloc[-1] + 30 * 1500) / (len(sub) + 30)),
               "min_raw": float(sub["rating_after_raw"].min()), "max_raw": float(sub["rating_after_raw"].max()),
               "range_raw": float(sub["rating_after_raw"].max() - sub["rating_after_raw"].min()),
               "mean_abs_change_per_ball": float(sub["rating_change"].abs().mean()),
               "largest_match_gain": float(move.max()), "largest_match_loss": float(move.min()),
               "status": "COMPUTED"}
        for season in range(2022, 2027):
            part = sub.loc[sub["season"].eq(season)]
            row[f"end_{season}"] = float(part["rating_after_raw"].iloc[-1]) if len(part) else np.nan
        stab.append(row)
stab = pd.DataFrame(stab)

# year-over-year stability of season-end ratings, player-ladder keys with >=120 balls in both seasons
yoy = []
for skill, id_col, after_col in [("batter", "striker_id", "batter_rating_after"), ("bowler", "bowler_id", "bowler_rating_after")]:
    end = Lw.groupby([id_col, "ladder", "season"]).agg(rating=(after_col, "last"), balls=(after_col, "size")).reset_index()
    for season in range(2022, 2026):
        a = end.loc[end["season"].eq(season)]
        b = end.loc[end["season"].eq(season + 1)]
        m = a.merge(b, on=[id_col, "ladder"], suffixes=("_a", "_b"))
        m = m.loc[m["balls_a"].ge(120) & m["balls_b"].ge(120)]
        if len(m) >= 10:
            yoy.append({"skill": skill, "from_season": season, "to_season": season + 1, "pairs": len(m),
                        "pearson": float(m["rating_a"].corr(m["rating_b"])), "spearman": float(stats.spearmanr(m["rating_a"], m["rating_b"])[0])})
yoy = pd.DataFrame(yoy)

# step-size sensitivity (diagnostic only): rerun the walk with half and double steps and rescore
pre = P["legal_pre_pressure"].set_index(["match_id", "innings", "n"])
base_cols = [c for c in legal.columns if c not in {"e_bat", "e_bowl", "x_runs", "x_runs_bowl", "x_wicket", "batter_rating_after", "bowler_rating_after"}]
legal_pre = legal[base_cols].copy()
key = pd.MultiIndex.from_frame(legal_pre[["match_id", "innings", "n"]])
for col in ["shock_bat", "shock_bowl", "pressure_bat", "pressure_bowl", "band", "band_bowl"]:
    legal_pre[col] = pre[col].reindex(key).to_numpy()
check_rerun = pr.run_elo(legal_pre)
reg.fact("elo_rerun_reproduces_official", bool(np.allclose(check_rerun.sort_index()["e_bat"].to_numpy(), legal.sort_index()["e_bat"].to_numpy())))
sens = []
official_b = bat.set_index("player_id")
official_w = bowl.set_index("player_id")
for label, k in [("half_steps", (2.0, 8.0, 10.0)), ("double_steps", (8.0, 32.0, 40.0))]:
    alt = pr.run_elo(legal_pre, k_run=k[0], k_wicket=k[1], k_team=k[2])
    s = alt.attrs["elo_summary"]
    ab = pr.score_batters(alt).set_index("player_id")
    aw = pr.score_bowlers(alt, work).set_index("player_id")
    for skill, off, new in [("batter", official_b, ab), ("bowler", official_w, aw)]:
        both = off.loc[off["ranked"]].index.intersection(new.loc[new["ranked"]].index)
        rho = stats.spearmanr(off.loc[both, "composite"], new.loc[both, "composite"])[0]
        top20_off = set(off.loc[off["ranked"]].nsmallest(20, "rank").index)
        top20_new = set(new.loc[new["ranked"]].nsmallest(20, "rank").index)
        sens.append({"variant": label, "k_run": k[0], "k_wicket": k[1], "k_team": k[2], "skill": skill,
                     "elo_min": s[f"{skill}_elo_min"], "elo_max": s[f"{skill}_elo_max"], "elo_sd": s[f"{skill}_elo_sd"],
                     "within_acceptance_bounds": bool(s[f"{skill}_elo_min"] >= 600 and s[f"{skill}_elo_max"] <= 2800 and s[f"{skill}_elo_sd"] <= 250),
                     "composite_spearman_vs_official": float(rho), "top20_overlap_vs_official": len(top20_off & top20_new)})
sens = pd.DataFrame(sens)
for _, r in sens.iterrows():
    reg.fact(f"elo_sens_{r['variant']}_{r['skill']}_spearman", float(r["composite_spearman_vs_official"]))
    reg.fact(f"elo_sens_{r['variant']}_{r['skill']}_top20", int(r["top20_overlap_vs_official"]))

fs = P["final_summary"]
fr = P["first_summary"]
keys_bat = Lw.groupby(["striker_id", "ladder"]).size()
keys_bowl = Lw.groupby(["bowler_id", "ladder"]).size()
er = [
    metric_row("start_rating", 1500.0, "EXISTING", "run_elo"),
    metric_row("k_run_as_written", 4.0, "EXISTING", "run_elo signature"),
    metric_row("k_wicket_as_written", 16.0, "EXISTING", "run_elo signature"),
    metric_row("k_team_as_written", 20.0, "EXISTING", "run_elo signature"),
    metric_row("k_run_used", fs["k_run"], "COMPUTED", "fit_elo summary"),
    metric_row("k_wicket_used", fs["k_wicket"], "COMPUTED", "fit_elo summary"),
    metric_row("k_team_used", fs["k_team"], "COMPUTED", "fit_elo summary"),
    metric_row("step_sizes", fs["step_sizes"], "COMPUTED", "fit_elo summary", "halving fallback (2/8/10) was NOT triggered on this data"),
    metric_row("acceptance_min", 600, "EXISTING", "fit_elo"),
    metric_row("acceptance_max", 2800, "EXISTING", "fit_elo"),
    metric_row("acceptance_sd", 250, "EXISTING", "fit_elo"),
    metric_row("cold_start_balls", 30, "EXISTING", "COLD_BALLS", "rating used in the gap = (n*raw + 30*1500)/(n+30)"),
    metric_row("venue_shrink_balls", 2400, "EXISTING", "VENUE_BALLS"),
    metric_row("gap_formula", "0.15*(batter-bowler)/400 + 0.05*(batting side-bowling side)/400 + 0.10*(ground-1500)/400", "EXISTING", "run_elo"),
    metric_row("batter_update", "raw += k_run*(bat_runs - xR) - k_wicket*(striker_out - xW)", "EXISTING", "run_elo"),
    metric_row("bowler_update", "raw += -k_run*(charged - xR_bowl) + k_wicket*(bowler_wicket - xW)", "EXISTING", "run_elo"),
    metric_row("team_update", "per match, standard logistic Elo with k_team on the result (no result = 0.5)", "EXISTING", "run_elo"),
    metric_row("ratings_kept_per_ladder", True, "EXISTING", "run_elo keys (player, ladder)"),
]
for k in ["batter_elo_min", "batter_elo_max", "batter_elo_sd", "bowler_elo_min", "bowler_elo_max", "bowler_elo_sd", "team_elo_min", "team_elo_max", "grounds"]:
    er.append(metric_row(k, fs[k], "COMPUTED", "fit_elo summary (final raw ratings, all player-ladder keys)"))
    reg.fact("elo_" + k, fs[k])
er.append(metric_row("first_pass_equals_final", bool(fr == {k: v for k, v in fs.items() if k != "step_sizes"}), "COMPUTED", "run_elo vs fit_elo"))
er.append(metric_row("batter_player_ladder_keys", len(keys_bat), "COMPUTED", "legal frame"))
er.append(metric_row("bowler_player_ladder_keys", len(keys_bowl), "COMPUTED", "legal frame"))
er.append(metric_row("batter_keys_under_30_balls", int(keys_bat.lt(30).sum()), "COMPUTED", "legal frame"))
er.append(metric_row("bowler_keys_under_30_balls", int(keys_bowl.lt(30).sum()), "COMPUTED", "legal frame"))
for ladder in ["IPL", "T20I", "T20"]:
    end_b = Lw.loc[Lw["ladder"].eq(ladder)].groupby("striker_id")["batter_rating_after"].last()
    end_w = Lw.loc[Lw["ladder"].eq(ladder)].groupby("bowler_id")["bowler_rating_after"].last()
    er.append(metric_row(f"batter_final_sd_{ladder}", float(end_b.std(ddof=0)), "COMPUTED", "legal frame"))
    er.append(metric_row(f"bowler_final_sd_{ladder}", float(end_w.std(ddof=0)), "COMPUTED", "legal frame"))
for _, r in yoy.iterrows():
    er.append(metric_row(f"season_end_rating_spearman_{r['skill']}_{r['from_season']}_{r['to_season']}", r["spearman"], "COMPUTED", "legal frame",
                         f"{r['pairs']} player-ladder keys with >=120 balls in both seasons"))
for _, r in sens.iterrows():
    er.append(metric_row(f"sensitivity_{r['variant']}_{r['skill']}_composite_spearman", r["composite_spearman_vs_official"], "COMPUTED",
                         "diagnostic rerun of run_elo + score_*", f"k={r['k_run']}/{r['k_wicket']}/{r['k_team']}; elo sd {r['elo_sd']:.1f}; top-20 overlap {r['top20_overlap_vs_official']}"))
er.append(metric_row("elo_used_in_composite_directly", False, "COMPUTED", "score_batters/score_bowlers",
                     "Elo enters only through xR/xW (the gap); the composite uses ball values, not ratings"))
er = pd.DataFrame(er)
reg.save(er, "04_elo/elo_summary.csv", "fit_elo summary; legal frame; diagnostic reruns", "see notes")
stab_out = pd.concat([stab, yoy.assign(player_name="ALL (year-over-year)", status="COMPUTED"),
                      sens.assign(player_name="ALL (step-size sensitivity, diagnostic)", status="COMPUTED")], ignore_index=True)
reg.save(stab_out, "04_elo/elo_stability.csv", "legal frame after fit_elo; diagnostic reruns", "per named player-ladder path stats; YoY Spearman; K sensitivity")
for _, r in stab.iterrows():
    reg.fact(f"elo_{r['skill']}_{r['player_name']}_{r['ladder']}_final", float(r["final_raw"]))
    reg.fact(f"elo_{r['skill']}_{r['player_name']}_{r['ladder']}_balls", int(r["balls"]))
    reg.fact(f"elo_{r['skill']}_{r['player_name']}_{r['ladder']}_min", float(r["min_raw"]))
    reg.fact(f"elo_{r['skill']}_{r['player_name']}_{r['ladder']}_max", float(r["max_raw"]))
for _, r in yoy.iterrows():
    reg.fact(f"elo_yoy_{r['skill']}_{r['from_season']}", float(r["spearman"]))

# ---------------------------------------------------------------- 05 expectation models


def deciles(pred, actual, scope, target):
    q = pd.qcut(pred.rank(method="first"), 10, labels=False) + 1
    f = pd.DataFrame({"decile": q, "pred": pred, "actual": actual})
    g = f.groupby("decile").agg(n_balls=("actual", "size"), pred_min=("pred", "min"), pred_max=("pred", "max"),
                                mean_predicted=("pred", "mean"), mean_actual=("actual", "mean")).reset_index()
    g["actual_minus_predicted"] = g["mean_actual"] - g["mean_predicted"]
    g["actual_over_predicted"] = g["mean_actual"] / g["mean_predicted"]
    g.insert(0, "target", target)
    g.insert(0, "scope", scope)
    g["status"] = "COMPUTED"
    return g


xr, xw = [], []
for scope, mask in [("all", pd.Series(True, index=legal.index))] + [(f"ladder_{l}", legal["ladder"].eq(l)) for l in ["IPL", "T20I", "T20"]]:
    sub = legal.loc[mask]
    xr.append(deciles(sub["x_runs"], sub["bat_runs"].astype(float), scope, "bat_runs vs x_runs (batter expectation)"))
    xr.append(deciles(sub["x_runs_bowl"], sub["charged_runs"].astype(float), scope, "charged_runs vs x_runs_bowl (bowler expectation)"))
    xw.append(deciles(sub["x_wicket"], sub["bowler_wicket"].astype(float), scope, "bowler_wicket vs x_wicket (what xW is trained on)"))
    xw.append(deciles(sub["x_wicket"], sub["striker_out"].astype(float), scope, "striker_out vs x_wicket (what the batter value uses)"))
xr, xw = pd.concat(xr, ignore_index=True), pd.concat(xw, ignore_index=True)
reg.save(xr, "05_expectation_models/xruns_calibration_deciles.csv", "legal frame after fit_elo", "deciles of the prediction (rank-based qcut)")
reg.save(xw, "05_expectation_models/xwickets_calibration_deciles.csv", "legal frame after fit_elo", "deciles of the prediction (rank-based qcut)")

ex_r = pd.read_csv(ROOT / "exports" / "14_calibration_bins.csv")
mine = xr.loc[xr["scope"].eq("all") & xr["target"].str.startswith("bat_runs")]
reg.fact("xr_deciles_match_export", bool(np.allclose(ex_r["mean_predicted_x_runs"], mine["mean_predicted"], atol=1e-6) and np.allclose(ex_r["mean_actual_bat_runs"], mine["mean_actual"], atol=1e-6)))
ex_w = pd.read_csv(ROOT / "exports" / "14b_calibration_wicket_bins.csv")
reg.fact("xw_export_decile_count", len(ex_w))


def logistic_recal(p, y):
    x = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    X = np.column_stack([np.ones_like(x), x])
    beta = np.array([0.0, 1.0])
    for _ in range(50):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        W = mu * (1 - mu)
        grad = X.T @ (y - mu)
        H = X.T @ (X * W[:, None])
        step = np.linalg.solve(H, grad)
        beta = beta + step
        if np.abs(step).max() < 1e-10:
            break
    return beta


def auc(p, y):
    r = stats.rankdata(p)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


PF = P["prefix_legal"]
met = []
scopes = [("all", legal, pd.Series(True, index=legal.index))] + [(f"ladder_{l}", legal, legal["ladder"].eq(l)) for l in ["IPL", "T20I", "T20"]]
scopes += [(f"season_{s}", legal, legal["season"].eq(s)) for s in range(2022, 2027)]
scopes += [("all_pre_fix_model", PF, pd.Series(True, index=PF.index))]
for scope, frame, mask in scopes:
    sub = frame.loc[mask]
    for target, pcol, ycol in [("bat_runs", "x_runs", "bat_runs"), ("charged_runs", "x_runs_bowl", "charged_runs")]:
        p, y = sub[pcol].to_numpy(float), sub[ycol].to_numpy(float)
        slope, intercept, r, _, _ = stats.linregress(p, y)
        const = y.mean()
        met.append({"model": f"x{'R' if target == 'bat_runs' else 'R_bowl'}", "target": target, "scope": scope, "n": len(y),
                    "mean_predicted": p.mean(), "mean_actual": const, "bias_actual_minus_predicted": const - p.mean(),
                    "mae": np.abs(y - p).mean(), "rmse": np.sqrt(((y - p) ** 2).mean()),
                    "mae_constant_in_sample_mean": np.abs(y - const).mean(), "rmse_constant_in_sample_mean": np.sqrt(((y - const) ** 2).mean()),
                    "calibration_slope_ols": slope, "calibration_intercept_ols": intercept, "r_squared": r ** 2,
                    "spearman": stats.spearmanr(p, y)[0], "brier": np.nan, "brier_constant": np.nan, "log_loss": np.nan, "auc": np.nan})
    for target, ycol in [("bowler_wicket", "bowler_wicket"), ("striker_out", "striker_out")]:
        p, y = sub["x_wicket"].to_numpy(float), sub[ycol].astype(int).to_numpy()
        b = logistic_recal(p, y)
        const = y.mean()
        met.append({"model": "xW", "target": target, "scope": scope, "n": len(y), "mean_predicted": p.mean(), "mean_actual": const,
                    "bias_actual_minus_predicted": const - p.mean(), "mae": np.abs(y - p).mean(), "rmse": np.sqrt(((y - p) ** 2).mean()),
                    "mae_constant_in_sample_mean": np.abs(y - const).mean(), "rmse_constant_in_sample_mean": np.sqrt(((y - const) ** 2).mean()),
                    "calibration_slope_ols": np.nan, "calibration_intercept_ols": np.nan, "r_squared": np.nan,
                    "calibration_slope_logistic": b[1], "calibration_intercept_logistic": b[0],
                    "spearman": stats.spearmanr(p, y)[0], "brier": ((y - p) ** 2).mean(), "brier_constant": ((y - const) ** 2).mean(),
                    "log_loss": -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)), "auc": auc(p, y)})
met = pd.DataFrame(met)
met["status"] = "COMPUTED"
met["note"] = "constant baseline uses the in-sample mean (look-ahead); it is a reference, not a fair competitor"
met.loc[met["scope"].eq("all_pre_fix_model"), "note"] = "pre-fix model (expectation cells without the wickets-down level); same balls"
reg.save(met, "05_expectation_models/expectation_model_metrics.csv", "legal frame after fit_elo; pre-fix model legal frame", "ball-level metrics; OLS and logistic recalibration")
for _, r in met.loc[met["scope"].isin(["all", "all_pre_fix_model"])].iterrows():
    tag = f"{r['model']}_{r['target']}" + ("_pre_fix" if r["scope"] == "all_pre_fix_model" else "")
    for c in ["mean_predicted", "mean_actual", "bias_actual_minus_predicted", "mae", "rmse", "mae_constant_in_sample_mean", "rmse_constant_in_sample_mean",
              "calibration_slope_ols", "calibration_intercept_ols", "r_squared", "calibration_slope_logistic", "calibration_intercept_logistic",
              "brier", "brier_constant", "auc", "log_loss", "spearman"]:
        if c in r and pd.notna(r[c]):
            reg.fact(f"xm_{tag}_{c}", float(r[c]))

# residuals by wickets fallen (KI-03: the full cell now has a wickets-down level; the pre-fix model had none)
res = []
bucket = pd.cut(legal["wickets_before"], [-1, 1, 3, 5, 7, 10], labels=["0-1", "2-3", "4-5", "6-7", "8-9"])
pf_bucket = pd.cut(PF["wickets_before"], [-1, 1, 3, 5, 7, 10], labels=["0-1", "2-3", "4-5", "6-7", "8-9"])
for b, sub in PF.groupby(pf_bucket, observed=True):
    res.append({"model": "pre_fix", "wickets_before": str(b), "phase": "all", "legal_balls": len(sub),
                "mean_x_runs": sub["x_runs"].mean(), "mean_bat_runs": sub["bat_runs"].mean(), "runs_actual_minus_expected": sub["bat_runs"].mean() - sub["x_runs"].mean(),
                "mean_x_wicket": sub["x_wicket"].mean(), "bowler_wicket_rate": sub["bowler_wicket"].mean(), "striker_out_rate": sub["striker_out"].mean(),
                "bowler_wicket_minus_xw": sub["bowler_wicket"].mean() - sub["x_wicket"].mean(), "striker_out_minus_xw": sub["striker_out"].mean() - sub["x_wicket"].mean(),
                "mean_e_bat": sub["e_bat"].mean(), "mean_e_bowl": sub["e_bowl"].mean(), "status": "COMPUTED"})
for (b, phase), sub in legal.groupby([bucket, "phase"], observed=True):
    res.append({"wickets_before": str(b), "phase": phase, "legal_balls": len(sub),
                "mean_x_runs": sub["x_runs"].mean(), "mean_bat_runs": sub["bat_runs"].mean(), "runs_actual_minus_expected": sub["bat_runs"].mean() - sub["x_runs"].mean(),
                "mean_x_wicket": sub["x_wicket"].mean(), "bowler_wicket_rate": sub["bowler_wicket"].mean(), "striker_out_rate": sub["striker_out"].mean(),
                "bowler_wicket_minus_xw": sub["bowler_wicket"].mean() - sub["x_wicket"].mean(), "striker_out_minus_xw": sub["striker_out"].mean() - sub["x_wicket"].mean(),
                "mean_e_bat": sub["e_bat"].mean(), "mean_e_bowl": sub["e_bowl"].mean(), "status": "COMPUTED"})
for b, sub in legal.groupby(bucket, observed=True):
    res.append({"wickets_before": str(b), "phase": "all", "legal_balls": len(sub),
                "mean_x_runs": sub["x_runs"].mean(), "mean_bat_runs": sub["bat_runs"].mean(), "runs_actual_minus_expected": sub["bat_runs"].mean() - sub["x_runs"].mean(),
                "mean_x_wicket": sub["x_wicket"].mean(), "bowler_wicket_rate": sub["bowler_wicket"].mean(), "striker_out_rate": sub["striker_out"].mean(),
                "bowler_wicket_minus_xw": sub["bowler_wicket"].mean() - sub["x_wicket"].mean(), "striker_out_minus_xw": sub["striker_out"].mean() - sub["x_wicket"].mean(),
                "mean_e_bat": sub["e_bat"].mean(), "mean_e_bowl": sub["e_bowl"].mean(), "status": "COMPUTED"})
res = pd.DataFrame(res)
res["model"] = res["model"].fillna("current")
res = pd.concat([res.loc[res["model"].eq("current")], res.loc[res["model"].eq("pre_fix")]], ignore_index=True)
reg.save(res, "05_expectation_models/residual_by_wickets_fallen.csv", "legal frame after fit_elo; pre-fix model legal frame",
         "group by wickets_before bucket x phase (current); bucket only (pre_fix rows)")
for _, r in res.loc[res["phase"].eq("all")].iterrows():
    sfx = "_pre_fix" if r["model"] == "pre_fix" else ""
    reg.fact(f"wf_{r['wickets_before']}_runs_resid{sfx}", float(r["runs_actual_minus_expected"]))
    reg.fact(f"wf_{r['wickets_before']}_bw_resid{sfx}", float(r["bowler_wicket_minus_xw"]))
    reg.fact(f"wf_{r['wickets_before']}_e_bat{sfx}", float(r["mean_e_bat"]))
    reg.fact(f"wf_{r['wickets_before']}_e_bowl{sfx}", float(r["mean_e_bowl"]))
    reg.fact(f"wf_{r['wickets_before']}_balls{sfx}", int(r["legal_balls"]))

# run-out mismatch (known issue)
reg.fact("xw_mean", float(legal["x_wicket"].mean()))
reg.fact("striker_out_rate", float(legal["striker_out"].mean()))
reg.fact("bowler_wicket_rate", float(legal["bowler_wicket"].mean()))
reg.fact("e_bat_mean", float(legal["e_bat"].mean()))
reg.fact("e_bowl_mean", float(legal["e_bowl"].mean()))
reg.fact("e_bat_wicket_part_mean", float((-4 * (legal["striker_out"].astype(float) - legal["x_wicket"])).mean()))
reg.fact("e_bowl_wicket_part_mean", float((4 * (legal["bowler_wicket"].astype(float) - legal["x_wicket"])).mean()))

pred_cols = ["match_id", "match_date", "innings", "n", "ladder", "phase", "pace_or_spin", "striker_id", "bowler_id"]
xrp = legal[pred_cols + ["x_runs", "bat_runs", "x_runs_bowl", "charged_runs", "e_bat", "e_bowl"]].copy()
xwp = legal[pred_cols + ["wickets_before", "x_wicket", "bowler_wicket", "striker_out", "dismissal_type"]].copy()
for f in (xrp, xwp):
    f["match_date"] = pd.to_datetime(f["match_date"]).dt.strftime("%Y-%m-%d")
    f.sort_values(["match_date", "match_id", "innings", "n"], inplace=True)
xwp["bowler_wicket"] = xwp["bowler_wicket"].astype(int)
xwp["striker_out"] = xwp["striker_out"].astype(int)
reg.save(xrp, "05_expectation_models/xruns_predictions.csv", "legal frame after fit_elo", "per-ball predictions as produced inside run_elo (sequential, past balls only)")
reg.save(xwp, "05_expectation_models/xwickets_predictions.csv", "legal frame after fit_elo", "same")
reg.close()
print("b done")
