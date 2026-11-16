"""06_shock, 07_rankings, 08_validation (plus diagnostics that never replace the official numbers)."""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

from common import (COMPONENTS, LABEL, LEGACY_COMPONENTS, LEGACY_WEIGHTS, ROOT, SANITY_PLAYERS, WEIGHTS, Registry, load, metric_row)

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import player_ratings as pr  # noqa: E402

reg = Registry("c")
P = load()
legal, work, balls, matches = P["legal"], P["work"], P["balls"], P["matches"]
L = pd.read_pickle(ROOT / "research_readout" / "_cache" / "legal_shock.pkl")
bat, bowl = P["batters"], P["bowlers"]
lbat, lbowl = P["legacy_batters"], P["legacy_bowlers"]

# ---------------------------------------------------------------- 06 shock
MATCH, INN = 40767, 2
m = matches.loc[matches["match_id"].eq(MATCH)].iloc[0]
inn = L.loc[L["match_id"].eq(MATCH) & L["innings"].eq(INN)].sort_values("n")
illegal_inn = work.loc[work["match_id"].eq(MATCH) & work["innings"].eq(INN) & ~work["is_legal"]]
timeline = pd.DataFrame({
    "legal_ball_n": inn["n"], "innings_ball_num": inn["innings_ball_num"], "over": inn["overid"], "ball_in_over": inn["over_ball_num"],
    "striker": inn["striker_name"], "bowler": inn["bowler_name"], "arm": inn["pace_or_spin"], "phase": inn["phase"],
    "bat_runs": inn["bat_runs"], "is_wicket": inn["wicket_flag"], "dismissal_type": inn["dismissal_type"],
    "dismissed_player_id": inn["dismissed_player_id"], "striker_out": inn["striker_out"].astype(int), "bowler_wicket": inn["bowler_wicket"].astype(int),
    "runs_before": inn["runs_before"], "wickets_before": inn["wickets_before"], "target": inn["target"], "rrr": inn["rrr"],
    "occasion": inn["occasion"], "competition": inn["competition"], "ball_bat": inn["ball_bat"], "ball_bowl": inn["ball_bowl"],
    "count_shock_bat": inn["count_shock_bat"], "excess_shock_bat": inn["excess_shock_bat"], "shock_bat": inn["shock_bat"],
    "count_shock_bowl": inn["count_shock_bowl"], "excess_shock_bowl": inn["excess_shock_bowl"], "shock_bowl": inn["shock_bowl"],
    "run_of_play_bat": inn["delta_bat"], "run_of_play_bowl": inn["delta_bowl"],
    "pressure_bat": inn["pressure_bat"], "band_bat": inn["band"], "pressure_bowl": inn["pressure_bowl"], "band_bowl": inn["band_bowl"],
    "x_runs": inn["x_runs"], "x_wicket": inn["x_wicket"], "e_bat": inn["e_bat"], "e_bowl": inn["e_bowl"],
})
reg.save(timeline, "06_shock/shock_innings_timeline.csv", "legal frame after fit_elo (match 40767 innings 2) + replicated count/excess split",
         "every legal ball of the IPL 2025 final chase")
claimed = [30, 51, 58, 73, 98, 100, 104]
actual_n = inn.loc[inn["wicket_flag"].eq(1), "n"].astype(int).tolist()
actual_ibn = inn.loc[inn["wicket_flag"].eq(1), "innings_ball_num"].astype(int).tolist()
reg.fact("shock_match", f"{m['home_team']} v {m['away_team']}, {m['comp_name']} {m['stage']}, {pd.to_datetime(m['match_date']).date()}, result: {m['result']}")
reg.fact("shock_claimed_wicket_balls", claimed)
reg.fact("shock_actual_wicket_legal_n", actual_n)
reg.fact("shock_actual_wicket_innings_ball_num", actual_ibn)
reg.fact("shock_claim_verified_legal_n", actual_n == claimed)
reg.fact("shock_wickets_on_illegal_deliveries", int(illegal_inn["wicket_flag"].sum()))
reg.fact("shock_innings_total", float(inn["team_run"].sum() + illegal_inn["team_run"].sum()))
reg.fact("shock_innings_legal_balls", int(len(inn)))
reg.fact("shock_target", float(inn["target"].iloc[0]))
reg.fact("shock_high_band_balls_bat", int(inn["band"].eq("high").sum()))
reg.fact("shock_high_band_balls_bowl", int(inn["band_bowl"].eq("high").sum()))
reg.fact("shock_occasion", float(inn["occasion"].iloc[0]))
reg.fact("shock_ball19_delta_bat", float(inn.loc[inn["n"].eq(19), "delta_bat"].iloc[0]))
reg.fact("shock_ball19_delta_bowl", float(inn.loc[inn["n"].eq(19), "delta_bowl"].iloc[0]))
reg.fact("shock_peak_pressure_bat", float(inn["pressure_bat"].max()))
reg.fact("shock_peak_pressure_bat_n", int(inn.loc[inn["pressure_bat"].idxmax(), "n"]))
ex10 = pd.read_csv(ROOT / "exports" / "10_sample_innings_timeline.csv")
reg.fact("export10_count_shock_bat_equals_final_shock", bool(np.allclose(ex10["count_shock_bat"], inn["shock_bat"])))
reg.fact("export10_count_shock_bat_equals_count_part", bool(np.allclose(ex10["count_shock_bat"], inn["count_shock_bat"])))

ev = []
for _, w in inn.loc[inn["wicket_flag"].eq(1)].iterrows():
    nxt = inn.loc[inn["n"].between(w["n"] + 1, w["n"] + 6)]
    ev.append({"scope": "IPL 2025 final, innings 2", "legal_ball_n": int(w["n"]), "over": f"{int(w['overid'])}.{int(w['over_ball_num'])}",
               "batter_out_id": w["dismissed_player_id"], "striker": w["striker_name"], "bowler": w["bowler_name"], "dismissal": w["dismissal_type"],
               "score_at_fall": f"{int(w['runs_before'] + w['team_run'])}/{int(w['wickets_before'] + 1)}",
               "shock_bat_on_ball": w["shock_bat"], "shock_bat_next_ball": nxt["shock_bat"].iloc[0] if len(nxt) else np.nan,
               "count_shock_bat_next_ball": nxt["count_shock_bat"].iloc[0] if len(nxt) else np.nan,
               "max_shock_bat_next6": nxt["shock_bat"].max() if len(nxt) else np.nan,
               "pressure_bat_next_ball": nxt["pressure_bat"].iloc[0] if len(nxt) else np.nan,
               "high_band_balls_next6": int(nxt["band"].eq("high").sum()), "next6_balls": len(nxt), "status": "COMPUTED"})
ev = pd.DataFrame(ev)
after = pd.Series(False, index=L.index)
wk_pos = L.loc[L["wicket_flag"].eq(1), ["match_id", "innings", "n"]]
lookup = L.set_index(["match_id", "innings", "n"]).index
for k in range(1, 7):
    shifted = pd.MultiIndex.from_arrays([wk_pos["match_id"], wk_pos["innings"], wk_pos["n"] + k])
    after |= lookup.isin(shifted)
all_rows = pd.DataFrame([
    {"scope": "all innings", "metric": "share_of_balls_within_6_after_a_wicket", "value": float(after.mean())},
    {"scope": "all innings", "metric": "batter_high_band_share_within_6_after_wicket", "value": float(L.loc[after, "band"].eq("high").mean())},
    {"scope": "all innings", "metric": "batter_high_band_share_otherwise", "value": float(L.loc[~after, "band"].eq("high").mean())},
    {"scope": "all innings", "metric": "mean_shock_bat_within_6_after_wicket", "value": float(L.loc[after, "shock_bat"].mean())},
    {"scope": "all innings", "metric": "mean_shock_bat_otherwise", "value": float(L.loc[~after, "shock_bat"].mean())},
    {"scope": "all innings", "metric": "mean_shock_bowl_after_six_in_last_6", "value": float(L.loc[L["count_shock_bowl"].ge(0.33), "shock_bowl"].mean())},
    {"scope": "all innings", "metric": "strike_rate_within_6_after_wicket", "value": float(100 * L.loc[after, "bat_runs"].mean())},
    {"scope": "all innings", "metric": "strike_rate_otherwise", "value": float(100 * L.loc[~after, "bat_runs"].mean())},
    {"scope": "all innings", "metric": "share_of_batter_high_band_balls_within_6_after_wicket", "value": float(after[L["band"].eq("high")].mean())},
    {"scope": "all innings", "metric": "share_of_bowler_high_band_balls_with_four_or_six_in_last_6", "value": float(L.loc[L["band_bowl"].eq("high"), "count_shock_bowl"].gt(0).mean())},
    {"scope": "all innings", "metric": "share_of_bowler_zero_band_balls_with_four_or_six_in_last_6", "value": float(L.loc[L["band_bowl"].eq("zero"), "count_shock_bowl"].gt(0).mean())},
    {"scope": "all innings", "metric": "share_of_bowler_high_band_balls_charged_runs_above_xr_last_6", "value": float(L.loc[L["band_bowl"].eq("high"), "excess_shock_bowl"].gt(0).mean())},
    {"scope": "all innings", "metric": "share_of_all_balls_charged_runs_above_xr_last_6", "value": float(L["excess_shock_bowl"].gt(0).mean())},
])
all_rows["status"] = "COMPUTED"
shock_events = pd.concat([ev, all_rows], ignore_index=True)
reg.save(shock_events, "06_shock/shock_event_summary.csv", "legal frame + replicated shock split", "per wicket of the final chase; dataset-wide after-wicket comparison")
for _, r in all_rows.iterrows():
    reg.fact("se_" + r["metric"], r["value"])

F = P  # facts from section a carry the scales
import json  # noqa: E402
fa = json.load(open(ROOT / "research_readout" / "_cache" / "facts_a.json"))
params = pd.DataFrame([
    ("window_balls", 6, "EXISTING", "previous six legal balls of the same innings; the current ball is excluded"),
    ("batter_wicket_step", 0.33, "EXISTING", "per wicket in window (Retire Out and Obstructing excluded; run outs and non-striker dismissals included)"),
    ("batter_dot_step", 0.05, "EXISTING", "per dot (no bat run, no wicket); leg-byes/byes count as dots"),
    ("batter_count_cap", 1.0, "EXISTING", "min(1, ...)"),
    ("bowler_six_step", 0.33, "EXISTING", "per six (bat_runs >= 6)"),
    ("bowler_four_step", 0.12, "EXISTING", "per four (bat_runs == 4)"),
    ("bowler_count_cap", 1.0, "EXISTING", "min(1, ...)"),
    ("batter_excess_input", "sum(bowler_wicket - x_wicket) over window", "EXISTING", "uses bowler-credited wickets only (run outs ignored here, unlike the count part)"),
    ("bowler_excess_input", "sum(charged_runs - x_runs_bowl) over window", "EXISTING", "legal balls only: wides and no-balls are not in the window"),
    ("batter_excess_scale_sd", fa["scale_excess_wicket"], "COMPUTED", "population SD of the window sums over all legal balls (zeros on balls 1-6 included)"),
    ("bowler_excess_scale_sd", fa["scale_excess_runs"], "COMPUTED", "same"),
    ("excess_clip", "[-0.5, 1.0]", "EXISTING", ""),
    ("final_shock_clip", "[-0.5, 1.0]", "EXISTING", "count + excess"),
    ("run_of_play_window", "last 6 vs last 18 legal balls", "EXISTING", "zero before ball 19"),
    ("run_of_play_batter_input", "wickets per ball", "EXISTING", ""),
    ("run_of_play_bowler_input", "bat runs per ball", "EXISTING", ""),
    ("run_of_play_wicket_scale_sd_as_executed", fa["scale_run_of_play_wicket"], "COMPUTED", "inflated by the ball-19 indexing bug"),
    ("run_of_play_runs_scale_sd_as_executed", fa["scale_run_of_play_runs"], "COMPUTED", "inflated by the ball-19 indexing bug"),
    ("run_of_play_wicket_scale_sd_bugfree", fa["bug_rop_scale_wicket_bugfree"], "COMPUTED", "diagnostic only"),
    ("run_of_play_runs_scale_sd_bugfree", fa["bug_rop_scale_runs_bugfree"], "COMPUTED", "diagnostic only"),
    ("run_of_play_clip", "[-0.5, 1.0]", "EXISTING", ""),
    ("bands_recut_after_excess", True, "EXISTING", "_add_expected_shock recomputes pressure and bands after the Elo walk"),
], columns=["parameter", "value", "status", "notes"])
reg.save(params, "06_shock/shock_parameters.csv", "player_ratings.py source; scales recomputed in section 02", "read from code + replicated")

# ---------------------------------------------------------------- 07 rankings


def ranking_table(table, legacy, skill):
    r = table.loc[table["ranked"]].sort_values("rank").copy()
    for comp in COMPONENTS:
        r[f"contrib_{comp}"] = r[comp] * WEIGHTS[comp]
    r = r.merge(legacy[["player_id", "rank", "composite", "form"]].rename(columns={"rank": "legacy_rank", "composite": "legacy_composite", "form": "legacy_form_z"}),
                on="player_id", how="left")
    r["rank_change_vs_legacy"] = r["legacy_rank"] - r["rank"]
    r.insert(0, "skill", skill)
    r["status"] = "COMPUTED"
    return r


fb = ranking_table(bat, lbat, "batter")
fw = ranking_table(bowl, lbowl, "bowler")
reg.save(fb, "07_rankings/final_batter_rankings.csv", "score_batters (current 7-term) + git 29956ed 8-term for legacy columns", "ranked players only")
reg.save(fw, "07_rankings/final_bowler_rankings.csv", "score_bowlers (current 7-term) + git 29956ed 8-term for legacy columns", "ranked players only")
for n in (10, 20):
    reg.save(fb.head(n), f"07_rankings/top{n}_batters.csv", "final_batter_rankings", f"first {n}")
    reg.save(fw.head(n), f"07_rankings/top{n}_bowlers.csv", "final_bowler_rankings", f"first {n}")
shipped_b = pd.read_csv(ROOT / "ratings" / "batters.csv")
reg.fact("rank_reproduces_shipped_batters", bool(shipped_b.set_index("player_id")["rank"].reindex(bat["player_id"]).fillna(-1).to_numpy().tolist() == bat["rank"].fillna(-1).tolist()))
reg.fact("ranked_batters", int(bat["ranked"].sum()))
reg.fact("ranked_bowlers", int(bowl["ranked"].sum()))
reg.fact("top10_batters", fb.head(10)[["rank", "player_name", "role", "composite"]].values.tolist())
reg.fact("top10_bowlers", fw.head(10)[["rank", "player_name", "role", "composite"]].values.tolist())
reg.fact("top20_batters", fb.head(20)[["rank", "player_name", "role", "composite", "legacy_rank"]].values.tolist())
reg.fact("top20_bowlers", fw.head(20)[["rank", "player_name", "role", "composite", "legacy_rank"]].values.tolist())

dist = []
for skill, table in [("batter", bat), ("bowler", bowl)]:
    for pop, mask in [("ranked", table["ranked"]), ("all_players", pd.Series(True, index=table.index))]:
        s = table.loc[mask, "composite"]
        row = {"skill": skill, "population": pop, "row_type": "summary", "n": len(s), "mean": s.mean(), "sd": s.std(ddof=0), "min": s.min(),
               "p10": s.quantile(0.1), "p25": s.quantile(0.25), "median": s.median(), "p75": s.quantile(0.75), "p90": s.quantile(0.9), "max": s.max(),
               "skew": stats.skew(s), "top1_minus_top10": np.nan, "top10_minus_top20": np.nan}
        if pop == "ranked":
            srt = s.sort_values(ascending=False).to_numpy()
            row["top1_minus_top10"] = srt[0] - srt[9]
            row["top10_minus_top20"] = srt[9] - srt[19]
            row["gap_rank10_rank11"] = srt[9] - srt[10]
            row["gap_rank20_rank21"] = srt[19] - srt[20]
            reg.fact(f"dist_{skill}_ranked_mean", float(s.mean()))
            reg.fact(f"dist_{skill}_ranked_sd", float(s.std(ddof=0)))
            reg.fact(f"dist_{skill}_top1", float(srt[0]))
            reg.fact(f"dist_{skill}_rank10", float(srt[9]))
            reg.fact(f"dist_{skill}_rank20", float(srt[19]))
            reg.fact(f"dist_{skill}_gap_10_11", float(srt[9] - srt[10]))
        dist.append(row)
        if pop == "ranked":
            edges = np.arange(np.floor(s.min() * 10) / 10, np.ceil(s.max() * 10) / 10 + 0.1, 0.1)
            counts, edges = np.histogram(s, bins=edges)
            for lo, hi, c in zip(edges[:-1], edges[1:], counts):
                dist.append({"skill": skill, "population": pop, "row_type": "histogram_bin", "bin_low": lo, "bin_high": hi, "n": int(c)})
dist = pd.DataFrame(dist)
dist["status"] = "COMPUTED"
reg.save(dist, "07_rankings/composite_distribution.csv", "ratings tables", "summary + 0.1-wide histogram bins")

# ---------------------------------------------------------------- 08 validation: ablation


def order(score: pd.Series, ids: pd.Series) -> pd.Series:
    frame = pd.DataFrame({"s": score.to_numpy(), "id": ids.to_numpy()}).sort_values(["s", "id"], ascending=[False, True])
    return pd.Series(np.arange(1, len(frame) + 1), index=frame["id"].to_numpy())


def variants(table, legacy, pooled, diag, no_super, skill):
    r = table.loc[table["ranked"]].set_index("player_id")
    ids = pd.Series(r.index, index=r.index)
    out = {"full_current": r["rank"].astype(int)}
    z = r[COMPONENTS]
    out["baseline_only"] = order(r["baseline"], ids)
    out["pressure_only_bands_clutch"] = order(z[["band_zero", "band_medium", "band_high", "clutch"]].mul(pd.Series(WEIGHTS)).sum(axis=1), ids)
    out["no_pressure_baseline_peers_consistency"] = order(z[["baseline", "peers", "consistency"]].mul(pd.Series(WEIGHTS)).sum(axis=1), ids)
    out["equal_weights"] = order(z.mean(axis=1), ids)
    for comp in COMPONENTS:
        keep = [c for c in COMPONENTS if c != comp]
        out[f"drop_{comp}"] = order(z[keep].mul(pd.Series(WEIGHTS)[keep]).sum(axis=1), ids)
    lg = legacy.set_index("player_id").reindex(r.index)
    out["legacy_8_term_with_form"] = order(lg["composite"], ids)
    ns = no_super.set_index("player_id").reindex(r.index)
    out["exclude_super_overs"] = order(ns["composite"], ids)
    if pooled is not None:
        pooled_rank = pooled.set_index("player_id")["rank"].reindex(r.index)
        out["no_role_split_pooled_z"] = pooled_rank.astype(int)
    if diag is not None:
        d = diag.set_index("player_id").reindex(r.index)
        out["diagnostic_runofplay_bugfree"] = order(d["composite"], ids)
    frame = pd.DataFrame(out)
    frame.insert(0, "player_name", r["player_name"])
    frame.insert(1, "role", r["role"])
    frame.insert(0, "skill", skill)
    return frame


# Diagnostic: rebuild bands with the ball-19 bug removed, then rescore. Official numbers are untouched.
D = legal.copy()
D["pressure_bat"] = L["base_bat"].reindex(D.index) + L["shock_bat"].reindex(D.index) + L["delta_bat_bugfree_diagnostic"].reindex(D.index)
D["pressure_bowl"] = L["base_bowl"].reindex(D.index) + L["shock_bowl"].reindex(D.index) + L["delta_bowl_bugfree_diagnostic"].reindex(D.index)
D["band"] = pr._cut_band(D["pressure_bat"])
D["band_bowl"] = pr._cut_band_within(D["pressure_bowl"], D["pace_or_spin"])
reg.fact("diag_rop_band_agreement_bat", float((D["band"] == legal["band"]).mean()))
reg.fact("diag_rop_band_agreement_bowl", float((D["band_bowl"] == legal["band_bowl"]).mean()))
diag_bat = pr.score_batters(D)
diag_bowl = pr.score_bowlers(D, work)
reg.fact("diag_rop_ranked_batters", int(diag_bat["ranked"].sum()))
reg.fact("diag_rop_ranked_bowlers", int(diag_bowl["ranked"].sum()))

vb = variants(bat, lbat, P["pooled_current"], diag_bat, P["no_super_batters"], "batter")
vw = variants(bowl, lbowl, None, diag_bowl, P["no_super_bowlers"], "bowler")
for skill, ns, cur in [("batter", P["no_super_batters"], bat), ("bowler", P["no_super_bowlers"], bowl)]:
    reg.fact(f"noso_ranked_{skill}s", int(ns["ranked"].sum()))
    reg.fact(f"noso_same_ranked_set_{skill}", bool(set(ns.loc[ns["ranked"], "player_id"]) == set(cur.loc[cur["ranked"], "player_id"])))
    gap = (cur.set_index("player_id")["composite"] - ns.set_index("player_id")["composite"].reindex(cur["player_id"]).to_numpy()).abs()
    reg.fact(f"noso_max_abs_composite_change_{skill}", float(gap.max()))
reg.save(vb.reset_index(), "08_validation/ablation_batter_rank_changes.csv", "ratings tables; git 29956ed legacy; diagnostic rescoring",
         "rank of each ranked batter under each variant (ties broken by player_id as in score_batters)")
reg.save(vw.reset_index(), "08_validation/ablation_bowler_rank_changes.csv", "ratings tables; git 29956ed legacy; diagnostic rescoring", "same for bowlers")

ex23 = pd.read_csv(ROOT / "exports" / "23_ablation_ranks.csv")
chk = bat.loc[bat["ranked"]].copy()
chk["bmin"] = chk["baseline"].rank(ascending=False, method="min")
e = ex23.loc[ex23["role"].eq("batter")].merge(chk[["player_name", "bmin", "rank"]], on="player_name")
reg.fact("export23_reproduced", bool((e["baseline_only_rank"] == e["bmin"]).all() and (e["full_composite_rank"] == e["rank"]).all()))

summary = []
for skill, frame in [("batter", vb), ("bowler", vw)]:
    full = frame["full_current"]
    for var in [c for c in frame.columns if c not in {"skill", "player_name", "role", "full_current"}]:
        alt = frame[var].dropna()
        f = full.loc[alt.index]
        rho = stats.spearmanr(f, alt)[0]
        tau = stats.kendalltau(f, alt)[0]
        row = {"skill": skill, "variant": var, "n": len(alt), "spearman_vs_full": rho, "kendall_tau_vs_full": tau,
               "mean_abs_rank_change": float((alt - f).abs().mean()), "median_abs_rank_change": float((alt - f).abs().median()),
               "max_abs_rank_change": int((alt - f).abs().max())}
        for k in (10, 20, 50):
            a, b = set(f[f <= k].index), set(alt[alt <= k].index)
            row[f"top{k}_overlap"] = len(a & b)
            row[f"top{k}_jaccard"] = len(a & b) / len(a | b)
        for name in ["Vaibhav Sooryavanshi", "Rahmanullah Gurbaz"]:
            hit = frame.loc[frame["player_name"].eq(name)]
            if len(hit):
                row[f"rank_{name.split()[-1]}_full"] = int(hit["full_current"].iloc[0])
                row[f"rank_{name.split()[-1]}_variant"] = int(hit[var].iloc[0]) if pd.notna(hit[var].iloc[0]) else np.nan
        summary.append(row)
summary = pd.DataFrame(summary)
summary["status"] = "COMPUTED"
summary["note"] = np.select(
    [summary["variant"].str.startswith("diagnostic"), summary["variant"].eq("exclude_super_overs"), summary["variant"].eq("legacy_8_term_with_form")],
    ["diagnostic only: shows the size of a documented bug; not an official result",
     "data variant: super-over rows removed before add_situation (the pipeline before super overs were included)",
     "git 29956ed scoring functions (8 terms with Form) on the same legal frame"],
    "re-weighting of the official component z-scores")
reg.save(summary, "08_validation/ablation_summary.csv", "ablation rank tables", "Spearman, Kendall tau-b, top-k overlap and Jaccard vs the official ranking")
for _, r in summary.iterrows():
    for c in ["spearman_vs_full", "kendall_tau_vs_full", "top10_overlap", "top20_overlap", "top10_jaccard", "top20_jaccard", "mean_abs_rank_change"]:
        reg.fact(f"abl_{r['skill']}_{r['variant']}_{c}", float(r[c]))
for name in ["Vaibhav Sooryavanshi", "Rahmanullah Gurbaz"]:
    hit = vb.loc[vb["player_name"].eq(name)]
    for c in vb.columns[3:]:
        reg.fact(f"abl_rank_{name}_{c}", int(hit[c].iloc[0]))

movers = []
for skill, frame in [("batter", vb), ("bowler", vw)]:
    for var, label in [("baseline_only", "full composite vs baseline only"), ("legacy_8_term_with_form", "current 7-term vs legacy 8-term"),
                       ("no_role_split_pooled_z", "role-split z vs pooled z"), ("diagnostic_runofplay_bugfree", "official vs ball-19 bug removed (diagnostic)"),
                       ("exclude_super_overs", "super overs included vs excluded")]:
        if var not in frame.columns:
            continue
        change = (frame[var] - frame["full_current"])  # positive = the full model ranks the player higher
        tmp = frame[["skill", "player_name", "role", "full_current", var]].copy()
        tmp["places_gained_in_full_model"] = change
        tmp = tmp.rename(columns={var: "comparison_rank"})
        tmp["comparison"] = label
        up = tmp.sort_values("places_gained_in_full_model", ascending=False).head(10).assign(direction="risers in the full model")
        down = tmp.sort_values("places_gained_in_full_model").head(10).assign(direction="fallers in the full model")
        movers.append(pd.concat([up, down]))
movers = pd.concat(movers, ignore_index=True)
movers["status"] = "COMPUTED"
reg.save(movers.reset_index(drop=True), "08_validation/ablation_top_movers.csv", "ablation rank tables", "ten largest moves each way per comparison")

# ---------------------------------------------------------------- correlations and influence
for skill, table, legacy in [("batters", bat, lbat), ("bowlers", bowl, lbowl)]:
    r = table.loc[table["ranked"]].set_index("player_id")
    cols = COMPONENTS + ["composite"]
    data = r[cols].copy()
    data["legacy_form"] = legacy.set_index("player_id").reindex(r.index)["form"]
    blocks = []
    for method in ("pearson", "spearman"):
        cm = data.corr(method=method)
        cm.insert(0, "component", cm.index)
        cm.insert(0, "method", method)
        blocks.append(cm)
    out = pd.concat(blocks, ignore_index=True)
    out["population"] = f"ranked {skill} (n={len(r)})"
    reg.save(out, f"08_validation/component_correlation_{skill}.csv", "ratings tables (ranked players) + git 29956ed form z", "pairwise correlation matrix")
    pc = data.corr(method="pearson")
    for a in COMPONENTS:
        reg.fact(f"corr_{skill}_{a}_composite", float(pc.loc[a, "composite"]))
    reg.fact(f"corr_{skill}_band_high_band_medium", float(pc.loc["band_high", "band_medium"]))
    reg.fact(f"corr_{skill}_band_high_clutch", float(pc.loc["band_high", "clutch"]))
    reg.fact(f"corr_{skill}_baseline_band_high", float(pc.loc["baseline", "band_high"]))
    reg.fact(f"corr_{skill}_baseline_peers", float(pc.loc["baseline", "peers"]))
    off = pc.loc[COMPONENTS, COMPONENTS].where(~np.eye(len(COMPONENTS), dtype=bool)).stack()
    reg.fact(f"corr_{skill}_max_pair", [off.idxmax()[0], off.idxmax()[1], float(off.max())])
    reg.fact(f"corr_{skill}_min_pair", [off.idxmin()[0], off.idxmin()[1], float(off.min())])

infl = []
for skill, table, frame in [("batter", bat, vb), ("bowler", bowl, vw)]:
    r = table.loc[table["ranked"]].set_index("player_id")
    comp = r["composite"]
    eff = {c: WEIGHTS[c] * r[c].std(ddof=0) for c in COMPONENTS}
    tot = sum(eff.values())
    for c in COMPONENTS:
        part = WEIGHTS[c] * r[c]
        s = summary.loc[summary["skill"].eq(skill) & summary["variant"].eq(f"drop_{c}")].iloc[0]
        top20 = r.loc[r["rank"].le(20)]
        infl.append({"skill": skill, "component": c, "label": LABEL[c], "nominal_weight": WEIGHTS[c], "sd_among_ranked": r[c].std(ddof=0),
                     "effective_weight_w_x_sd": eff[c], "effective_share": eff[c] / tot,
                     "variance_share_of_composite": float(np.cov(part, comp, ddof=0)[0, 1] / comp.var(ddof=0)),
                     "pearson_with_composite": float(r[c].corr(comp)), "spearman_with_composite": float(stats.spearmanr(r[c], comp)[0]),
                     "drop_one_spearman": s["spearman_vs_full"], "drop_one_top20_overlap": int(s["top20_overlap"]),
                     "drop_one_mean_abs_rank_change": s["mean_abs_rank_change"],
                     "mean_contribution_top20": float((WEIGHTS[c] * top20[c]).mean()), "status": "COMPUTED"})
infl = pd.DataFrame(infl)
reg.save(infl, "08_validation/component_influence.csv", "ratings tables; ablation_summary", "nominal vs effective weight, variance share, drop-one effects")
for _, r in infl.iterrows():
    reg.fact(f"infl_{r['skill']}_{r['component']}_varshare", float(r["variance_share_of_composite"]))
    reg.fact(f"infl_{r['skill']}_{r['component']}_effshare", float(r["effective_share"]))
    reg.fact(f"infl_{r['skill']}_{r['component']}_drop_top20", int(r["drop_one_top20_overlap"]))
    reg.fact(f"infl_{r['skill']}_{r['component']}_drop_spearman", float(r["drop_one_spearman"]))

# ---------------------------------------------------------------- roles
cov = []
for skill, table in [("batter", bat), ("bowler", bowl)]:
    for role, g in table.groupby("role"):
        cov.append({"skill": skill, "role": role, "players": len(g), "n_eff_ge_30_reference": int(g["n_eff"].ge(30).sum()),
                    "n_eff_ge_120": int(g["n_eff"].ge(120).sum()), "high_n_eff_ge_30": int(g["high_n_eff"].ge(30).sum()),
                    "ranked": int(g["ranked"].sum()), "ranked_share_of_players": float(g["ranked"].mean()),
                    "ranked_share_of_reference": float(g["ranked"].sum() / max(g["n_eff"].ge(30).sum(), 1)),
                    "share_of_ranked_pool": float(g["ranked"].sum() / table["ranked"].sum()),
                    "fail_n_eff_only": int((g["n_eff"].lt(120) & g["high_n_eff"].ge(30)).sum()),
                    "fail_high_n_only": int((g["n_eff"].ge(120) & g["high_n_eff"].lt(30)).sum()),
                    "fail_both": int((g["n_eff"].lt(120) & g["high_n_eff"].lt(30)).sum()), "status": "COMPUTED"})
cov = pd.DataFrame(cov)
reg.save(cov, "08_validation/role_coverage.csv", "ratings tables", "eligibility counts by role")
ex19 = pd.read_csv(ROOT / "exports" / "19_reference_population_sizes.csv")
reg.fact("export19", ex19.values.tolist())
for _, r in cov.iterrows():
    reg.fact(f"role_{r['skill']}_{r['role']}_ranked", int(r["ranked"]))
    reg.fact(f"role_{r['skill']}_{r['role']}_reference", int(r["n_eff_ge_30_reference"]))
    reg.fact(f"role_{r['skill']}_{r['role']}_share_pool", float(r["share_of_ranked_pool"]))

tok = {"top order": "top", "middle order": "middle", "lower order": "lower"}
rep = []
pool_b = bat.loc[bat["ranked"]]
lists = {
    "current_with_role_split": bat.loc[bat["ranked"]].sort_values("rank")[["player_name", "role"]].assign(role=lambda f: f["role"].map(tok)),
    "current_without_role_split": P["pooled_current"][["player_name", "role"]],
    "legacy_8term_with_role_split": lbat.loc[lbat["ranked"]].sort_values("rank")[["player_name", "role"]].assign(role=lambda f: f["role"].map(tok)),
    "legacy_8term_without_role_split": P["pooled_legacy"][["player_name", "role"]],
}
for label, lst in lists.items():
    for k in (10, 20, 50, len(lst)):
        head = lst.head(k)["role"].value_counts()
        rep.append({"skill": "batter", "ranking": label, "top_k": k if k != len(lst) else f"all ({k})",
                    "top": int(head.get("top", 0)), "middle": int(head.get("middle", 0)), "lower": int(head.get("lower", 0)),
                    "names": "; ".join(lst.head(k)["player_name"]) if k <= 20 else "", "status": "COMPUTED"})
for k in (10, 20, 50):
    lst = bowl.loc[bowl["ranked"]].sort_values("rank").head(k)["role"].value_counts()
    rep.append({"skill": "bowler", "ranking": "current", "top_k": k, "pace": int(lst.get("Pace", 0)), "spin": int(lst.get("Spin", 0)), "status": "COMPUTED"})
lst = bowl.loc[bowl["ranked"], "role"].value_counts()
rep.append({"skill": "bowler", "ranking": "current", "top_k": f"all ({int(bowl['ranked'].sum())})", "pace": int(lst.get("Pace", 0)), "spin": int(lst.get("Spin", 0)), "status": "COMPUTED"})
rep = pd.DataFrame(rep)
reg.save(rep, "08_validation/role_ranking_representation.csv", "ratings tables; _pooled_batter_order (current and git 29956ed)", "role counts in top-k")
for label in lists:
    row = rep.loc[rep["ranking"].eq(label) & rep["top_k"].eq(20)].iloc[0]
    reg.fact(f"rolerep_{label}_top20", [int(row["top"]), int(row["middle"]), int(row["lower"])])
    row = rep.loc[rep["ranking"].eq(label) & rep["top_k"].eq(10)].iloc[0]
    reg.fact(f"rolerep_{label}_top10", [int(row["top"]), int(row["middle"]), int(row["lower"])])
for k in (10, 20):
    row = rep.loc[rep["skill"].eq("bowler") & rep["top_k"].eq(k)].iloc[0]
    reg.fact(f"rolerep_bowler_top{k}", [int(row["pace"]), int(row["spin"])])
ex17 = pd.read_csv(ROOT / "exports" / "17_role_composition_with_split.csv")["role"].value_counts().to_dict()
ex18 = pd.read_csv(ROOT / "exports" / "18_role_composition_without_split.csv")["role"].value_counts().to_dict()
reg.fact("export17_roles", ex17)
reg.fact("export18_roles", ex18)

sd = []
for skill, table in [("batter", bat), ("bowler", bowl)]:
    for role, g in table.groupby("role"):
        for pop, h in [("all", g), ("ranked", g.loc[g["ranked"]])]:
            for col in ["legal_balls", "n_eff", "high_n_eff"]:
                s = h[col]
                sd.append({"skill": skill, "role": role, "population": pop, "variable": col, "n": len(s), "mean": s.mean(), "min": s.min(),
                           "p25": s.quantile(0.25), "median": s.median(), "p75": s.quantile(0.75), "max": s.max(), "status": "COMPUTED"})
        hb = table.loc[table["role"].eq(role)]
        sd.append({"skill": skill, "role": role, "population": "ranked", "variable": "high_n_share_of_n_eff",
                   "n": int(hb["ranked"].sum()), "mean": float((hb.loc[hb["ranked"], "high_n_eff"] / hb.loc[hb["ranked"], "n_eff"]).mean()), "status": "COMPUTED"})
sd = pd.DataFrame(sd)
reg.save(sd, "08_validation/role_sample_distribution.csv", "ratings tables", "sample-size distribution by role")
for _, r in sd.loc[sd["variable"].eq("high_n_share_of_n_eff")].iterrows():
    reg.fact(f"role_highshare_{r['skill']}_{r['role']}", float(r["mean"]))

# ---------------------------------------------------------------- sanity players
ab_b = vb.set_index(vb.index)
rows = []
end_rating = legal.sort_values(["match_date", "match_id", "innings", "innings_ball_num"])
bat_elo = end_rating.groupby(["striker_id", "ladder"])["batter_rating_after"].last().unstack()
bowl_elo = end_rating.groupby(["bowler_id", "ladder"])["bowler_rating_after"].last().unstack()
for name in SANITY_PLAYERS:
    for skill, table, legacy, vframe, elo in [("batter", bat, lbat, vb, bat_elo), ("bowler", bowl, lbowl, vw, bowl_elo)]:
        hit = table.loc[table["player_name"].eq(name)]
        if hit.empty:
            continue
        h = hit.iloc[0]
        primary_bowler = name in {"Jasprit Bumrah", "Rashid Khan", "Matthew Humphreys", "Corbin Bosch", "Imad Wasim"}
        primary = primary_bowler if skill == "bowler" else not primary_bowler
        if not primary and h["legal_balls"] < 120:
            continue
        lg = legacy.loc[legacy["player_id"].eq(h["player_id"])].iloc[0]
        reason = "" if h["ranked"] else "; ".join(x for x in [
            f"n_eff {h['n_eff']:.1f} < 120" if h["n_eff"] < 120 else "", f"high_n_eff {h['high_n_eff']:.1f} < 30" if h["high_n_eff"] < 30 else ""] if x)
        row = {"player_name": name, "skill": skill, "player_id": h["player_id"], "role": h["role"], "legal_balls": h["legal_balls"],
               "n_eff": h["n_eff"], "high_n_eff": h["high_n_eff"], "ranked": bool(h["ranked"]), "reason_not_ranked": reason,
               "rank": h["rank"], "ranked_pool": int(table["ranked"].sum()),
               "rank_percentile": (1 - (h["rank"] - 1) / table["ranked"].sum()) if h["ranked"] else np.nan,
               "composite": h["composite"]}
        for c in COMPONENTS:
            row[c] = h[c]
        row["legacy_form_z"] = lg["form"]
        row["legacy_rank_8term"] = lg["rank"]
        if h["ranked"]:
            v = vframe.loc[h["player_id"]]
            row["baseline_only_rank"] = v["baseline_only"]
            row["no_role_split_rank"] = v.get("no_role_split_pooled_z", np.nan)
            row["bugfree_runofplay_rank_diagnostic"] = v.get("diagnostic_runofplay_bugfree", np.nan)
            row["rank_with_super_overs_excluded"] = v.get("exclude_super_overs", np.nan)
        if skill == "batter":
            row.update({"runs": h["runs"], "strike_rate_level_weighted": h["strike_rate"], "average_level_weighted": h["average"]})
        else:
            row.update({"wickets": h["wickets"], "economy_level_weighted": h["economy"], "balls_per_wicket_level_weighted": h["balls_per_wicket"]})
        for ladder in ["IPL", "T20I", "T20"]:
            row[f"elo_final_{ladder}"] = elo.loc[h["player_id"], ladder] if (h["player_id"] in elo.index and ladder in elo.columns) else np.nan
        row["status"] = "COMPUTED"
        rows.append(row)
sanity = pd.DataFrame(rows)
reg.save(sanity, "08_validation/sanity_check_players.csv", "ratings tables; legacy; ablation; final Elo per ladder", "one row per player and skill")
for _, r in sanity.iterrows():
    tag = f"{r['player_name']}_{r['skill']}"
    for c in ["rank", "composite", "legacy_rank_8term", "baseline_only_rank", "n_eff", "high_n_eff", "ranked", "no_role_split_rank", "bugfree_runofplay_rank_diagnostic"] + COMPONENTS:
        if c in r and pd.notna(r[c]):
            reg.fact(f"sp_{tag}_{c}", r[c] if not isinstance(r[c], (np.floating, float)) else float(r[c]))
    reg.fact(f"sp_{tag}_reason", r["reason_not_ranked"])

# ---------------------------------------------------------------- diagnostic: bowler clutch basis
bm = P["traces"]["bowlers"]["math"].set_index("player_id")
lw = legal.groupby("bowler_id").apply(lambda f: 6 * (f["charged_runs"] * f["level_weight"]).sum() / f["level_weight"].sum(), include_groups=False)
cb = pd.DataFrame({"economy_career_all_deliveries": bm["economy"], "economy_career_legal_balls_only": lw.reindex(bm.index)})
cb["difference"] = cb["economy_career_all_deliveries"] - cb["economy_career_legal_balls_only"]
scale = float(bm["clutch_scale"].iloc[0])
cb["difference_in_clutch_scale_units"] = cb["difference"] / scale
cb = cb.join(bowl.set_index("player_id")[["player_name", "ranked", "rank", "clutch"]])
cr = P["traces"]["bowlers"]["clutch"]
cr_beat = float((cr["own_gap"] > 0).mean())
alt_gap = (cr["bowler_id"].map(cb["economy_career_legal_balls_only"]) - cr["metric"]) / scale
reg.fact("clutch_bowl_scale", scale)
reg.fact("clutch_bowl_basis_diff_mean_ranked", float(cb.loc[cb["ranked"], "difference"].mean()))
reg.fact("clutch_bowl_basis_diff_units_mean_ranked", float(cb.loc[cb["ranked"], "difference_in_clutch_scale_units"].mean()))
reg.fact("clutch_bowl_share_spells_beating_own_rate_as_executed", cr_beat)
reg.fact("clutch_bowl_share_spells_beating_own_rate_same_basis", float((alt_gap > 0).mean()))
cb = cb.reset_index()
cb["status"] = "COMPUTED"
reg.save(cb, "08_validation/diagnostic_bowler_clutch_basis.csv", "TRACES bowler math; legal frame", "career economy with vs without wide/no-ball runs (the clutch comparison uses legal-ball spell economy)")
reg.close()
print("c done")
