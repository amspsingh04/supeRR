"""01_dataset and 02_pressure."""

from __future__ import annotations

import numpy as np
import pandas as pd

import os
import sys

from common import ROOT, Registry, describe, load, metric_row

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import player_ratings as pr  # noqa: E402

reg = Registry("a")
P = load()
balls, work, legal, matches = P["balls"], P["work"], P["legal"], P["matches"]
pre = P["legal_pre_pressure"]
PF = P["prefix_legal"]

# ---------------------------------------------------------------- 01 dataset
raw_balls = pd.read_csv(ROOT / "ball_by_ball.csv", usecols=["match_id", "innings", "innings_ball_num"])
raw_matches = pd.read_csv(ROOT / "matches.csv")
raw_xi = pd.read_csv(ROOT / "playing_eleven.csv", usecols=["match_id", "team_id", "player_id"])
silver_squad = pd.read_csv(ROOT / "silver" / "playing_eleven.csv", usecols=["match_id", "team_id", "player_id", "order_conflict"])
silver_xi = pd.read_csv(ROOT / "silver" / "playing_xi.csv", usecols=["match_id", "team_id", "player_id"])

S_BALLS = "silver/ball_by_ball.csv via player_ratings.load()"
rows = []
add = lambda *a, **k: rows.append(metric_row(*a, **k))
add("raw_deliveries_source_file", len(raw_balls), source="ball_by_ball.csv (repository root)")
add("silver_deliveries", len(balls), source=S_BALLS, notes="cleaning keeps every row; nothing is deleted")
add("rows_deleted_in_cleaning", len(raw_balls) - len(balls), source="raw vs silver row count")
dup = int(balls.duplicated(["match_id", "innings", "innings_ball_num"]).sum())
add("duplicate_delivery_keys_match_innings_ballnum", dup, source=S_BALLS)
add("super_over_deliveries_included", int(balls["is_super_over"].astype(bool).sum()), source=S_BALLS, notes="innings 3 and 4; kept in every rating")
add("super_over_legal_balls_included", int(legal["is_super_over"].sum()), source="add_situation legal frame")
add("super_over_matches", int(legal.loc[legal["is_super_over"], "match_id"].nunique()), source="add_situation legal frame")
add("deliveries_in_work_frame", len(work), source="add_situation work frame")
add("illegal_deliveries_wide_noball_other", int((~work["is_legal"]).sum()), source="add_situation work frame")
add("legal_balls_used_in_ratings", len(legal), source="add_situation legal frame")
for label, count in work.loc[~work["is_legal"], "extras_label"].value_counts().items():
    add(f"illegal_deliveries_{label}", int(count), source="add_situation work frame")
add("matches_in_matches_csv", len(raw_matches), source="matches.csv")
add("matches_with_deliveries", int(balls["match_id"].nunique()), source=S_BALLS)
add("matches_with_legal_balls", int(legal["match_id"].nunique()), source="legal frame")
add("matches_in_matches_csv_without_deliveries", int(len(set(raw_matches["match_id"]) - set(balls["match_id"]))), source="matches.csv vs ball_by_ball")
add("competitions_with_legal_balls", int(legal["comp_id"].nunique()), source="legal frame")
add("innings_including_super_overs", int(work.groupby(["match_id", "innings"]).ngroups), source="work frame")
add("first_match_date", str(legal["match_date"].min().date()), source="legal frame")
add("last_match_date", str(legal["match_date"].max().date()), source="legal frame")
add("unique_batters_faced_legal_ball", int(legal["striker_id"].nunique()), source="legal frame")
add("unique_bowlers_bowled_legal_ball", int(legal["bowler_id"].nunique()), source="legal frame")
add("unique_venues", int(legal["venue_id"].nunique()), source="legal frame")
add("grounds_seen_by_elo_walk", P["final_summary"]["grounds"], source="run_elo summary")
for ladder, frame in legal.groupby("ladder"):
    add(f"legal_balls_ladder_{ladder}", len(frame), source="legal frame")
    add(f"matches_ladder_{ladder}", int(frame["match_id"].nunique()), source="legal frame")
for group, count in legal["comp_group"].value_counts().items():
    add(f"legal_balls_comp_group_{group}", int(count), source="legal frame")
for season, count in legal["season"].value_counts().sort_index().items():
    add(f"legal_balls_season_{int(season)}", int(count), source="legal frame")
for stage, count in legal.drop_duplicates("match_id")["stage"].value_counts().items():
    add(f"matches_stage_{stage}", int(count), source="legal frame")
legal_per_innings = work.groupby(["match_id", "innings"])["is_legal"].sum()
add("innings_over_120_legal_balls", int(legal_per_innings.gt(120).sum()), source="work frame")
overs = work.groupby(["match_id", "innings", "overid"])["is_legal"].sum()
add("overs_with_more_than_6_legal_balls", int(overs.gt(6).sum()), source="work frame",
    notes="; ".join(f"{m}/{i}/over {o}" for (m, i, o) in overs[overs.gt(6)].index))
for col in ["striker_id", "bowler_id", "batting_order", "pace_or_spin", "venue_id", "batting_type", "bowling_type"]:
    add(f"missing_{col}_in_legal_balls", int(legal[col].isna().sum()), source="legal frame")
wk = work.loc[work["wicket_flag"].eq(1)]
add("wickets_missing_dismissal_type", int(wk["dismissal_type"].isna().sum()), source="work frame")
add("wickets_missing_dismissed_player", int(wk["dismissed_player_id"].isna().sum()), source="work frame")
add("deliveries_flagged_sheet_gap", int(balls["sheet_gap"].astype(bool).sum()), source=S_BALLS,
    notes="a player on the ball is absent from that side's squad sheet; rows kept")
add("ordinary_balls_with_extra_runs_kept_as_supplied", int((balls["extras_label"].eq("ordinary") & (balls["extras1_runs"] + balls["extras_2_runs"]).gt(0)).sum()), source=S_BALLS)
add("bye_or_legbye_with_zero_amount_kept_as_supplied", int((balls["extras_label"].isin(["bye", "leg-bye"]) & balls["extras1_runs"].eq(0)).sum()), source=S_BALLS)
add("playing_list_rows_raw", len(raw_xi), source="playing_eleven.csv")
add("playing_list_rows_after_dedup", len(silver_squad), source="silver/playing_eleven.csv")
add("playing_list_order_conflicts", int(silver_squad["order_conflict"].sum()), source="silver/playing_eleven.csv")
add("playing_xi_rows", len(silver_xi), source="silver/playing_xi.csv")
add("playing_xi_matches_two_clean_sides", int(silver_xi["match_id"].nunique()), source="silver/playing_xi.csv")
add("matches_no_result_no_winner", int(raw_matches["win_team_id"].isna().sum()), source="matches.csv")
dead = legal.loc[legal["occasion"].eq(0.4), "match_id"].nunique()
add("dead_rubber_matches_occasion_0_4", int(dead), source="legal frame occasion column")
cleaning = pd.DataFrame(rows)
reg.save(cleaning, "01_dataset/cleaning_summary.csv", "silver CSVs, raw CSVs, add_situation frames", "counts on the frames the pipeline builds")
for key in ["raw_deliveries_source_file", "super_over_deliveries_included", "super_over_legal_balls_included", "super_over_matches",
            "illegal_deliveries_wide_noball_other",
            "legal_balls_used_in_ratings", "matches_with_legal_balls", "duplicate_delivery_keys_match_innings_ballnum",
            "unique_batters_faced_legal_ball", "unique_bowlers_bowled_legal_ball", "dead_rubber_matches_occasion_0_4",
            "first_match_date", "last_match_date", "overs_with_more_than_6_legal_balls", "deliveries_flagged_sheet_gap",
            "innings_including_super_overs", "matches_no_result_no_winner"]:
    reg.fact("ds_" + key, cleaning.loc[cleaning["metric"].eq(key), "value"].iloc[0])
for ladder in ["IPL", "T20I", "T20"]:
    reg.fact(f"ds_legal_{ladder}", int(legal["ladder"].eq(ladder).sum()))
    reg.fact(f"ds_matches_{ladder}", int(legal.loc[legal["ladder"].eq(ladder), "match_id"].nunique()))

# Funnel check against the existing export.
funnel = pd.read_csv(ROOT / "exports" / "01_cleaning_funnel.csv").set_index("stage")["count"]
reg.fact("ds_funnel_export_matches", bool(funnel["legal_balls_used"] == len(legal) and funnel["raw_deliveries"] == len(balls)))

# delivery classification
CHARGE = {
    "ordinary": "bat runs charged to bowler",
    "wide": "all wide runs (extras1 + extras2) charged to bowler; ball not legal",
    "no-ball": "no-ball run (extras1) + bat runs charged; extras2 (byes off it) free; ball not legal",
    "other": "treated like a no-ball: extras1 + bat runs charged; ball not legal",
    "bye": "not charged to bowler",
    "leg-bye": "not charged to bowler",
    "penalty": "not charged to bowler",
}
dc = []
for label, frame in balls.groupby(balls["extras_label"].fillna("ordinary")):
    nso = frame
    wk_label = work.loc[work["extras_label"].fillna("ordinary").eq(label)]
    dc.append({
        "extras_label": label,
        "source_extras_type": ", ".join(sorted(frame["extras_type"].fillna("None").astype(str).unique())),
        "deliveries_all": len(frame),
        "deliveries_super_over": int(frame["is_super_over"].astype(bool).sum()),
        "deliveries_used": len(nso),
        "is_legal": bool(frame["is_legal"].astype(bool).all()),
        "counts_as_ball_faced": bool(frame["is_legal"].astype(bool).all()),
        "bat_runs": float(nso["runs"].sum()),
        "extras1_runs": float(nso["extras1_runs"].sum()),
        "extras2_runs": float(nso["extras_2_runs"].sum()),
        "runs_charged_to_bowler": float(wk_label["conceded"].sum()),
        "in_elo_and_ball_value": bool(frame["is_legal"].astype(bool).all()),
        "in_bowler_baseline_economy": True,
        "bowler_charging_rule": CHARGE.get(label, ""),
        "status": "COMPUTED",
    })
dc = pd.DataFrame(dc).sort_values("deliveries_all", ascending=False)
reg.save(dc, "01_dataset/delivery_classification.csv", S_BALLS + "; add_situation conceded", "group by extras_label")
reg.fact("ds_wides", int(work["extras_label"].eq("wide").sum()))
reg.fact("ds_noballs", int(work["extras_label"].eq("no-ball").sum()))
reg.fact("ds_other_extras", int(work["extras_label"].eq("other").sum()))
nonlegal_conceded = float(work.loc[~work["is_legal"], "conceded"].sum())
reg.fact("ds_runs_conceded_on_illegal_deliveries", nonlegal_conceded)
reg.fact("ds_runs_conceded_total", float(work["conceded"].sum()))

# dismissal classification
BOWLER = {"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"}
dd = []
wk_all = balls.loc[balls["is_wicket"].fillna(False).astype(bool)]
wk_used = work.loc[work["wicket_flag"].eq(1)]
wk_legal = legal.loc[legal["wicket_flag"].eq(1)]
for dtype in wk_all["dismissal_type"].fillna("(blank)").value_counts().index:
    a = wk_all.loc[wk_all["dismissal_type"].fillna("(blank)").eq(dtype)]
    u = wk_used.loc[wk_used["dismissal_type"].fillna("(blank)").eq(dtype)]
    lg = wk_legal.loc[wk_legal["dismissal_type"].fillna("(blank)").eq(dtype)]
    dd.append({
        "dismissal_type": dtype,
        "count_all": len(a),
        "count_super_over": int(a["is_super_over"].astype(bool).sum()),
        "count_used": len(u),
        "on_illegal_delivery": int((~u["is_legal"]).sum()),
        "on_legal_ball": len(lg),
        "striker_dismissed_on_legal_ball": int(lg["striker_out"].sum()),
        "non_striker_dismissed_on_legal_ball": int((~lg["striker_out"]).sum()),
        "is_bowler_wicket": dtype in BOWLER,
        "penalises_batter_ball_value_and_elo": "yes when the striker is out" if len(lg) else "",
        "credits_bowler_ball_value_and_elo": dtype in BOWLER,
        "credits_bowler_baseline_wickets": dtype in BOWLER,
        "counts_in_count_shock": dtype not in {"Retire Out", "Obstructing the field"},
        "counts_in_xwicket_training": dtype in BOWLER,
        "status": "COMPUTED",
    })
dd = pd.DataFrame(dd)
reg.save(dd, "01_dataset/dismissal_classification.csv", S_BALLS + "; legal frame striker_out and bowler_wicket", "group by dismissal_type")
reg.fact("ds_bowler_wickets_illegal_delivery", int(wk_used.loc[~wk_used["is_legal"], "is_bowler_wicket"].sum()))
reg.fact("ds_runouts_used", int(wk_used["dismissal_type"].eq("RunOut").sum()))
reg.fact("ds_striker_out_legal", int(legal["striker_out"].sum()))
reg.fact("ds_bowler_wicket_legal", int(legal["bowler_wicket"].sum()))
reg.fact("ds_striker_runouts_legal", int((legal["striker_out"] & legal["dismissal_type"].eq("RunOut")).sum()))
reg.fact("ds_nonstriker_dismissals_legal", int((legal["wicket_flag"].eq(1) & ~legal["striker_out"]).sum()))

assumptions = pd.DataFrame([
    ("Legal ball", "wide, no-ball (Overstep) and 'other' extras are illegal; bye, leg-bye, penalty and ordinary balls are legal", "data_cleaning.ipynb cell 10; ILLEGAL list", f"'other' counted legal would put 150 innings past 120 legal balls (data_exploration.ipynb); with it illegal the max is {int(legal_per_innings.max())}"),
    ("Super overs", "innings 3 and 4 are super overs and are kept in every rating. Each super-over ball is a death ball; occasion is max(stage occasion, 1.5), so a dead rubber or league super over counts as a knockout and a semi-final or final keeps 2 or 3; the second super over chases the first super over's total + 1",
     "data_cleaning.ipynb cell 10; add_situation; SUPER_OVER_OCCASION", f"{int(balls['is_super_over'].astype(bool).sum())} deliveries, {int(legal['is_super_over'].sum())} legal balls, {int(legal.loc[legal['is_super_over'], 'match_id'].nunique())} matches"),
    ("Ball order", "innings_ball_num is the ball sequence; rows sorted by match, innings, innings_ball_num", "data_cleaning.ipynb cell 10", f"duplicate keys: {dup}"),
    ("Season", "split seasons (2022/23 etc.) take the earlier year", "data_cleaning.ipynb cell 4", "seasons 2022-2026"),
    ("Competition group", "IPL by name prefix, T20I by match_format, everything else Other T20", "data_cleaning.ipynb cell 4", "Other T20 = Emerging Teams Asia Cup 2024 and Asia Cup Rising Stars 2025"),
    ("Ladders", "IPL, T20I, and T20 (Other T20). Elo and expectation cells never share across ladders", "player_ratings.add_situation, _expectation_keys, run_elo", ""),
    ("Lower level weight", "a T20 (Emerging/Rising) ball counts as 0.5 of a ball in every count and mean", "LOWER_LEVEL_WEIGHT", ""),
    ("Season decay", "0.9^(2026-season) weights band rates and n_eff (not baseline rates, peers, clutch or consistency)", "WEIGHT, _row_weights", "2022 weight 0.6561, 2026 weight 1.0"),
    ("Bowler wicket", "Caught, Bowled, LBW, Stump, Hit Wicket credit the bowler; run outs, retired out, obstructing do not", "data_cleaning.ipynb BOWLER_WICKETS", ""),
    ("Extras charged to bowler", "wide: all runs; no-ball/other: extras1 + bat runs; byes, leg-byes, penalty free", "add_situation conceded", ""),
    ("Reduced matches", "revised overs columns are ball counts; blank second innings copies the first; a blank both stays 120", "data_cleaning.ipynb cell 8", ""),
    ("Chase target", "revised_target used as supplied; otherwise first-innings total + 1; reduced match without a target gets no required rate; the second super over (innings 4) chases the first super over's total + 1", "add_situation", ""),
    ("Phases", "powerplay is ball <= round(0.3*length), death is ball > round(0.8*length) using legal-ball position; every super-over ball is death", "_phase_labels; add_situation", "full innings: balls 1-36, 37-96, 97-120"),
    ("Batting role", "modal batting order: 1-3 top, 4-6 middle, 7+ lower", "_batting_role", ""),
    ("Bowling arm", "modal pace_or_spin over legal balls", "score_bowlers", ""),
    ("Duplicated playing-list rows", "40 duplicate (match, team, player) rows collapsed; conflicting batting orders blanked", "data_cleaning.ipynb cell 12", f"order conflicts: {int(silver_squad['order_conflict'].sum())}"),
    ("Odd extras amounts", "rows whose amount does not fit the type are kept as supplied", "data_cleaning.ipynb cell 10", "3 rows: 17555/1/29, 36097/2/49, 37099/1/82"),
    ("bowl_speed", "dropped", "data_cleaning.ipynb cell 10", ""),
], columns=["assumption", "rule_as_implemented", "location", "evidence"])
assumptions["status"] = "EXISTING"
reg.save(assumptions, "01_dataset/cleaning_assumptions.csv", "data_cleaning.ipynb and player_ratings.py source", "read from code")

# DLS / reduced
mx = matches.drop_duplicates("match_id")
reduced = mx.loc[mx["is_reduced"].fillna(False).astype(bool)]
chase = legal.loc[legal["innings"].eq(2)]
red_chase = chase.loc[chase["is_reduced"].fillna(False).astype(bool)]
no_target = red_chase["revised_target"].isna() | red_chase["revised_target"].le(0)
dls = [
    metric_row("matches_total", len(mx), source="silver/matches.csv"),
    metric_row("matches_is_reduced", len(reduced), source="silver/matches.csv"),
    metric_row("reduced_matches_with_revised_target", int(reduced["revised_target"].notna().sum()), source="silver/matches.csv"),
    metric_row("reduced_matches_without_revised_target", int(reduced["revised_target"].isna().sum()), source="silver/matches.csv"),
    metric_row("non_reduced_matches_with_revised_target", int(mx.loc[~mx["is_reduced"].fillna(False).astype(bool), "revised_target"].notna().sum()), source="silver/matches.csv"),
    metric_row("reduced_matches_with_legal_balls", int(legal.loc[legal["is_reduced"].fillna(False).astype(bool), "match_id"].nunique()), source="legal frame"),
    metric_row("reduced_chases_excluded_from_required_rate_matches", int(red_chase.loc[no_target, "match_id"].nunique()), source="legal frame", notes="no supplied target in a reduced match: rrr left blank"),
    metric_row("reduced_chases_excluded_from_required_rate_balls", int(no_target.sum()), source="legal frame"),
    metric_row("second_innings_legal_balls", len(chase), source="legal frame"),
    metric_row("second_innings_balls_with_required_rate", int(chase["rrr"].notna().sum()), source="legal frame"),
    metric_row("second_innings_balls_rrr_ge_8", int(chase["rrr"].ge(8).sum()), source="legal frame"),
    metric_row("second_innings_balls_rrr_ge_12", int(chase["rrr"].ge(12).sum()), source="legal frame"),
    metric_row("legal_balls_in_reduced_matches", int(legal["is_reduced"].fillna(False).astype(bool).sum()), source="legal frame"),
    metric_row("super_over_chase_legal_balls", int(legal["innings"].eq(4).sum()), source="legal frame"),
    metric_row("super_over_chase_balls_with_required_rate", int(legal.loc[legal["innings"].eq(4), "rrr"].notna().sum()), source="legal frame"),
]
for value, count in reduced["first_innings_balls"].value_counts().sort_index().items():
    dls.append(metric_row(f"reduced_first_innings_length_{int(value)}_balls", int(count), source="silver/matches.csv"))
dls.append(metric_row("dls_par_score_or_resource_table", "not in data", status="REQUIRES_DATA", notes="only revised overs and revised target are supplied; no DLS par or resources"))
dls = pd.DataFrame(dls)
reg.save(dls, "01_dataset/dls_summary.csv", "silver/matches.csv; legal frame", "counts")
reg.fact("dls_reduced_matches", len(reduced))
reg.fact("dls_excluded_matches", int(red_chase.loc[no_target, "match_id"].nunique()))

# ---------------------------------------------------------------- 02 pressure
L = legal.sort_values(["match_id", "innings", "n"], kind="mergesort").copy()
grp = L.groupby(["match_id", "innings"], sort=False)
real_w = (L["wicket_flag"].eq(1) & ~L["dismissal_type"].isin(["Retire Out", "Obstructing the field"])).astype(float)
dot = (L["bat_runs"].eq(0) & real_w.eq(0)).astype(float)
four = L["bat_runs"].eq(4).astype(float)
six = L["bat_runs"].ge(6).astype(float)


def prev_sum(values: pd.Series, window: int) -> pd.Series:
    return values.groupby([L["match_id"], L["innings"]], sort=False).transform(lambda s: s.shift(1).rolling(window).sum())


w6, d6, f6, s6 = prev_sum(real_w, 6), prev_sum(dot, 6), prev_sum(four, 6), prev_sum(six, 6)
count_bat = np.minimum(1.0, 0.33 * w6 + 0.05 * d6).fillna(0.0)
count_bowl = np.minimum(1.0, 0.33 * s6 + 0.12 * f6).fillna(0.0)
w18 = prev_sum(real_w, 18)
r6, r18 = prev_sum(L["bat_runs"].astype(float), 6), prev_sum(L["bat_runs"].astype(float), 18)
gap_w = (w6 / 6 - w18 / 18).where(w18.notna())
gap_r = (r6 / 6 - r18 / 18).where(r18.notna())
wicket_scale = float(gap_w.std(ddof=0))
run_scale = float(gap_r.std(ddof=0))
delta_bat = (gap_w / wicket_scale).clip(-0.5, 1.0).fillna(0.0)
delta_bowl = (gap_r / run_scale).clip(-0.5, 1.0).fillna(0.0)
# The pre-fix _shock_and_delta read cum[end - 18] = cum[-1], the innings total, on legal ball 19.
# Rebuilt here only to document BUG-01 and checked against the pre-fix model's own columns.
at19 = L["n"].eq(19)
tot_w = real_w.groupby([L["match_id"], L["innings"]], sort=False).transform("sum")
tot_r = L["bat_runs"].astype(float).groupby([L["match_id"], L["innings"]], sort=False).transform("sum")
gap_w_bug, gap_r_bug = gap_w.copy(), gap_r.copy()
gap_w_bug[at19] = w6[at19] / 6 - (w18[at19] - tot_w[at19]) / 18
gap_r_bug[at19] = r6[at19] / 6 - (r18[at19] - tot_r[at19]) / 18
wicket_scale_bug = float(gap_w_bug.std(ddof=0))
run_scale_bug = float(gap_r_bug.std(ddof=0))
L["delta_bat_pre_fix"] = (gap_w_bug / wicket_scale_bug).clip(-0.5, 1.0).fillna(0.0)
L["delta_bowl_pre_fix"] = (gap_r_bug / run_scale_bug).clip(-0.5, 1.0).fillna(0.0)
keys = pd.MultiIndex.from_frame(L[["match_id", "innings", "n"]])
PFa = PF.set_index(["match_id", "innings", "n"]).reindex(keys)
reg.fact("bug_rop_replica_vs_pre_fix_model_maxgap", float(max(np.abs(L["delta_bat_pre_fix"].to_numpy() - PFa["delta_bat"].to_numpy()).max(),
                                                             np.abs(L["delta_bowl_pre_fix"].to_numpy() - PFa["delta_bowl"].to_numpy()).max())))
reg.fact("bug_rop_balls_at_19", int(at19.sum()))
reg.fact("bug_rop_delta_bat_mean_at_19", float(L.loc[at19, "delta_bat"].mean()))
reg.fact("bug_rop_delta_bowl_mean_at_19", float(L.loc[at19, "delta_bowl"].mean()))
reg.fact("bug_rop_delta_bat_mean_at_19_pre_fix", float(L.loc[at19, "delta_bat_pre_fix"].mean()))
reg.fact("bug_rop_delta_bowl_mean_at_19_pre_fix", float(L.loc[at19, "delta_bowl_pre_fix"].mean()))
reg.fact("bug_rop_scale_wicket_pre_fix", wicket_scale_bug)
reg.fact("bug_rop_scale_runs_pre_fix", run_scale_bug)
reg.fact("bug_rop_delta_bowl_mean_all", float(L["delta_bowl"].mean()))
reg.fact("bug_rop_delta_bowl_mean_all_pre_fix", float(L["delta_bowl_pre_fix"].mean()))
reg.fact("bug_rop_delta_bat_mean_all", float(L["delta_bat"].mean()))
reg.fact("bug_rop_delta_bat_mean_all_pre_fix", float(L["delta_bat_pre_fix"].mean()))
reg.fact("bug_rop_ball19_bowler_high_share_pre_fix", float(PFa.loc[at19.to_numpy(), "band_bowl"].eq("high").mean()))
reg.fact("bug_rop_ball19_batter_high_share_pre_fix", float(PFa.loc[at19.to_numpy(), "band"].eq("high").mean()))
ex_w = prev_sum(L["bowler_wicket"].astype(float) - L["x_wicket"], 6).fillna(0.0)
ex_r = prev_sum(L["charged_runs"].astype(float) - L["x_runs_bowl"], 6).fillna(0.0)
ex_w_scale = float(ex_w.std(ddof=0))
ex_r_scale = float(ex_r.std(ddof=0))
excess_bat = (ex_w / ex_w_scale).clip(-0.5, 1.0)
excess_bowl = (ex_r / ex_r_scale).clip(-0.5, 1.0)
shock_bat = (count_bat + excess_bat).clip(-0.5, 1.0)
shock_bowl = (count_bowl + excess_bowl).clip(-0.5, 1.0)
pre_aligned = pre.set_index(["match_id", "innings", "n"]).reindex(pd.MultiIndex.from_frame(L[["match_id", "innings", "n"]]))
checks = {
    "count_shock_bat_vs_pre_elo": float(np.abs(count_bat.to_numpy() - pre_aligned["shock_bat"].to_numpy()).max()),
    "count_shock_bowl_vs_pre_elo": float(np.abs(count_bowl.to_numpy() - pre_aligned["shock_bowl"].to_numpy()).max()),
    "delta_bat": float(np.abs(delta_bat - L["delta_bat"]).max()),
    "delta_bowl": float(np.abs(delta_bowl - L["delta_bowl"]).max()),
    "final_shock_bat": float(np.abs(shock_bat - L["shock_bat"]).max()),
    "final_shock_bowl": float(np.abs(shock_bowl - L["shock_bowl"]).max()),
}
L["count_shock_bat"], L["count_shock_bowl"] = count_bat, count_bowl
L["excess_shock_bat"], L["excess_shock_bowl"] = excess_bat, excess_bowl
WEIGHT_P = pr.PRESSURE_WEIGHTS
part_sd = {}
for side, shock, delta in [("bat", shock_bat, delta_bat), ("bowl", shock_bowl, delta_bowl)]:
    parts = {"situation": L["occasion"] * L["competition"] * L[f"ball_{side}"], "shock": shock, "run_of_play": delta}
    total = pd.Series(0.0, index=L.index)
    for name, part in parts.items():
        part_sd[(name, side)] = float(part.std(ddof=0))
        L[f"w_{name}_{side}"] = WEIGHT_P[name] * part / part_sd[(name, side)]
        total = total + L[f"w_{name}_{side}"]
    checks[f"pressure_{side}"] = float(np.abs(total - L[f"pressure_{side}"]).max())
    checks[f"situation_{side}"] = float(np.abs(parts["situation"] - L[f"situation_{side}"]).max())
L.to_pickle(P_PATH := (ROOT / "research_readout" / "_cache" / "legal_shock.pkl"))
for k, v in checks.items():
    reg.fact("replication_maxgap_" + k, v)
reg.fact("scale_run_of_play_wicket", wicket_scale)
reg.fact("scale_run_of_play_runs", run_scale)
reg.fact("scale_excess_wicket", ex_w_scale)
reg.fact("scale_excess_runs", ex_r_scale)
reg.fact("pressure_weights", WEIGHT_P)
for (name, side), v in part_sd.items():
    reg.fact(f"pressure_sd_{name}_{side}", v)

pace = L["pace_or_spin"].eq("Pace")
spin = L["pace_or_spin"].eq("Spin")
cut = {
    "batter": (L["pressure_bat"].quantile(0.5), L["pressure_bat"].quantile(0.8)),
    "bowler_pace": (L.loc[pace, "pressure_bowl"].quantile(0.5), L.loc[pace, "pressure_bowl"].quantile(0.8)),
    "bowler_spin": (L.loc[spin, "pressure_bowl"].quantile(0.5), L.loc[spin, "pressure_bowl"].quantile(0.8)),
}
pre_cut = {
    "batter": (pre["pressure_bat"].quantile(0.5), pre["pressure_bat"].quantile(0.8)),
}
existing_cut = pd.read_csv(ROOT / "exports" / "08_band_cutoffs.csv").set_index("metric")

summary = []
for var, label in [("pressure_bat", "final batter pressure"), ("pressure_bowl", "final bowler pressure"),
                   ("situation_bat", "situation: occasion x competition x batter ball difficulty"), ("situation_bowl", "situation: occasion x competition x bowler ball difficulty"),
                   ("w_situation_bat", f"weighted situation term in batter pressure ({WEIGHT_P['situation']} x situation / its SD)"),
                   ("w_shock_bat", f"weighted shock term in batter pressure ({WEIGHT_P['shock']} x shock / its SD)"),
                   ("w_run_of_play_bat", f"weighted run-of-play term in batter pressure ({WEIGHT_P['run_of_play']} x run of play / its SD)"),
                   ("w_situation_bowl", "weighted situation term in bowler pressure"), ("w_shock_bowl", "weighted shock term in bowler pressure"),
                   ("w_run_of_play_bowl", "weighted run-of-play term in bowler pressure"),
                   ("occasion", "occasion multiplier"), ("competition", "competition multiplier"),
                   ("ball_bat", "batter ball difficulty (0-1)"), ("ball_bowl", "bowler ball difficulty (0-1)"),
                   ("count_shock_bat", "batter count shock (wickets, dots)"), ("count_shock_bowl", "bowler count shock (fours, sixes)"),
                   ("excess_shock_bat", "batter excess-wicket shock"), ("excess_shock_bowl", "bowler excess-runs shock"),
                   ("shock_bat", "final batter shock"), ("shock_bowl", "final bowler shock"),
                   ("delta_bat", "batter run of play"), ("delta_bowl", "bowler run of play")]:
    row = describe(L[var], var)
    row["label"] = label
    summary.append(row)
summary = pd.DataFrame(summary)
for side in ("bat", "bowl"):
    total = f"pressure_{side}"
    var_total = L[total].var(ddof=0)
    for name in ("situation", "shock", "run_of_play"):
        share = float(np.cov(L[f"w_{name}_{side}"], L[total], ddof=0)[0, 1] / var_total)
        summary.loc[summary["variable"].eq(f"w_{name}_{side}"), f"variance_share_of_{total}"] = share
        reg.fact(f"pr_var_share_{name}_{side}", share)
    # The pre-fix index was the raw sum situation + shock + run of play (run of play with the ball-19 bug).
    pf_parts = {"situation": PF["occasion"] * PF["competition"] * PF[f"ball_{side}"], "shock": PF[f"shock_{side}"], "run_of_play": PF[f"delta_{side}"]}
    pf_var = PF[total].var(ddof=0)
    for name, part in pf_parts.items():
        reg.fact(f"pr_var_share_{name}_{side}_pre_fix", float(np.cov(part, PF[total], ddof=0)[0, 1] / pf_var))
summary["status"] = "COMPUTED"
reg.save(summary, "02_pressure/pressure_summary.csv", "legal frame after fit_elo; shock parts replicated from player_ratings formulas",
         "describe(); variance share = cov(weighted term, total)/var(total), so the three shares sum to 1")
w_s, w_k, w_r = WEIGHT_P["situation"], WEIGHT_P["shock"], WEIGHT_P["run_of_play"]
formula = pd.DataFrame([
    ("pressure_bat", f"{w_s} x situation_bat / {part_sd[('situation', 'bat')]:.5f} + {w_k} x shock_bat / {part_sd[('shock', 'bat')]:.5f} + {w_r} x delta_bat / {part_sd[('run_of_play', 'bat')]:.5f}",
     "_combine_pressure, called by _attach_pressure and again by _add_expected_shock (final); each SD is the population SD over all legal balls"),
    ("pressure_bowl", f"{w_s} x situation_bowl / {part_sd[('situation', 'bowl')]:.5f} + {w_k} x shock_bowl / {part_sd[('shock', 'bowl')]:.5f} + {w_r} x delta_bowl / {part_sd[('run_of_play', 'bowl')]:.5f}",
     "_combine_pressure (final)"),
    ("situation_bat / situation_bowl", "occasion x competition x ball_bat (ball_bowl)", "_combine_pressure"),
    ("weights", f"PRESSURE_WEIGHTS = situation {w_s}, shock {w_k}, run of play {w_r}. Before the fix the three terms were added raw (pressure = situation + shock + run of play)", "PRESSURE_WEIGHTS"),
    ("occasion", "Final 3.0, Semi Final 2.0, Qualifier 1.5, Eliminator 1.5, Super 4 1.3, League 1.0, Others 0.8; dead bilateral rubber 0.4; unknown 1.0", "OCCASION, _dead_series_matches"),
    ("competition", "0.7 if comp_group is Other T20 or the name contains Emerging/Rising, else 1.0", "_competition_weight"),
    ("ball_bat", "clip(phase term [PP 0.25, middle 0.10, death 0.40] + wickets term [0-1 down 0, 2-4 0.15, 5+ 0.30] + chase rate term [rrr>=12 0.30, rrr>=8 0.15], 0, 1)", "_ball_difficulty"),
    ("ball_bowl", "clip(phase term [PP 0.32, middle 0.24, death 0.32 if striker order<=7 else 0.14] + wickets term [0-1 0, 2-4 -0.10, 5+ -0.25] + same chase rate term, 0, 1)", "_ball_difficulty"),
    ("count shock bat", "min(1, 0.33 x wickets + 0.05 x dots) over previous 6 legal balls of the innings; wickets exclude Retire Out and Obstructing; zero for the first 6 balls", "_shock_and_delta"),
    ("count shock bowl", "min(1, 0.33 x sixes + 0.12 x fours) over previous 6 legal balls", "_shock_and_delta"),
    ("excess shock bat", f"clip(sum over previous 6 of (bowler_wicket - x_wicket) / {ex_w_scale:.5f}, -0.5, 1)", "_add_expected_shock"),
    ("excess shock bowl", f"clip(sum over previous 6 of (charged_runs - x_runs_bowl) / {ex_r_scale:.5f}, -0.5, 1)", "_add_expected_shock"),
    ("final shock", "clip(count shock + excess shock, -0.5, 1)", "_add_expected_shock"),
    ("delta_bat", f"clip((wickets/6 over last 6 - wickets/18 over last 18) / {wicket_scale:.5f}, -0.5, 1); 0 before ball 19. FIXED: on ball 19 the 18-ball sum is now balls 1-18 (the pre-fix code subtracted the innings total there; its scale was {wicket_scale_bug:.5f})", "_shock_and_delta"),
    ("delta_bowl", f"clip((bat runs/6 over last 6 - bat runs/18 over last 18) / {run_scale:.5f}, -0.5, 1); 0 before ball 19. Same fix (pre-fix scale {run_scale_bug:.5f})", "_shock_and_delta"),
    ("bands", "high >= p80, medium >= p50, else zero; batters on all legal balls; bowlers within Pace and within Spin", "_cut_band, _cut_band_within"),
], columns=["term", "as_executed", "code"])
formula["status"] = "COMPUTED"
reg.save(formula, "02_pressure/pressure_formula_as_executed.csv", "player_ratings.py source + scales recomputed from data", "read from code; scales replicated (max gap in facts)")

pct = pd.DataFrame({"percentile": list(range(1, 100))})
for name, series in [("pressure_bat", L["pressure_bat"]), ("pressure_bowl_all", L["pressure_bowl"]),
                     ("pressure_bowl_pace", L.loc[pace, "pressure_bowl"]), ("pressure_bowl_spin", L.loc[spin, "pressure_bowl"])]:
    pct[name] = [float(series.quantile(p / 100)) for p in pct["percentile"]]
reg.save(pct, "02_pressure/pressure_percentiles.csv", "legal frame after fit_elo", "Series.quantile (linear)")

bands = []
for scope, mask, pcol, bcol in [("batter_all", pd.Series(True, index=L.index), "pressure_bat", "band"),
                                ("bowler_pace", pace, "pressure_bowl", "band_bowl"),
                                ("bowler_spin", spin, "pressure_bowl", "band_bowl")]:
    sub = L.loc[mask]
    p50, p80 = cut["batter" if scope == "batter_all" else scope]
    key = {"batter_all": "pressure_bat", "bowler_pace": "pressure_bowl_pace", "bowler_spin": "pressure_bowl_spin"}[scope]
    for band in ["zero", "medium", "high"]:
        b = sub.loc[sub[bcol].eq(band)]
        bands.append({
            "scope": scope, "band": band, "p50_cutoff": p50, "p80_cutoff": p80,
            "existing_export_p50": existing_cut.loc[key, "p50"], "existing_export_p80": existing_cut.loc[key, "p80"],
            "balls": len(b), "share": len(b) / len(sub), "intended_share": {"zero": 0.5, "medium": 0.3, "high": 0.2}[band],
            "pressure_min": b[pcol].min(), "pressure_mean": b[pcol].mean(), "pressure_max": b[pcol].max(),
            "bat_runs_per_ball": b["bat_runs"].mean(), "strike_rate": 100 * b["bat_runs"].mean(),
            "striker_out_rate": b["striker_out"].mean(), "bowler_wicket_rate": b["bowler_wicket"].mean(),
            "economy_legal_balls": 6 * b["charged_runs"].mean(), "boundary_rate": b["bat_runs"].ge(4).mean(),
            "mean_e_bat": b["e_bat"].mean(), "mean_e_bowl": b["e_bowl"].mean(),
            "share_death": b["phase"].eq("death").mean(), "share_chase": b["innings"].eq(2).mean(),
            "share_knockout_occasion_gt_1": b["occasion"].gt(1).mean(), "status": "COMPUTED",
        })
bands = pd.DataFrame(bands)
reg.save(bands, "02_pressure/pressure_band_summary.csv", "legal frame after fit_elo; exports/08_band_cutoffs.csv", "band labels from the pipeline; cutoffs recomputed")
for scope, (a, b) in cut.items():
    reg.fact(f"pr_{scope}_p50", float(a))
    reg.fact(f"pr_{scope}_p80", float(b))
reg.fact("pr_pre_elo_batter_p50", float(pre_cut["batter"][0]))
reg.fact("pr_pre_elo_batter_p80", float(pre_cut["batter"][1]))
same_band = float((pre_aligned["band"].to_numpy() == L["band"].to_numpy()).mean())
reg.fact("pr_band_agreement_pre_vs_final", same_band)
reg.fact("pr_cutoffs_match_export", bool(np.isclose(cut["batter"][1], existing_cut.loc["pressure_bat", "p80"]) and np.isclose(cut["bowler_spin"][1], existing_cut.loc["pressure_bowl_spin", "p80"])))
for _, r in bands.iterrows():
    reg.fact(f"pr_share_{r['scope']}_{r['band']}", float(r["share"]))
    reg.fact(f"pr_sr_{r['scope']}_{r['band']}", float(r["strike_rate"]))
    reg.fact(f"pr_out_{r['scope']}_{r['band']}", float(r["striker_out_rate"]))
    reg.fact(f"pr_econ_{r['scope']}_{r['band']}", float(r["economy_legal_balls"]))
    reg.fact(f"pr_bw_{r['scope']}_{r['band']}", float(r["bowler_wicket_rate"]))
    reg.fact(f"pr_death_{r['scope']}_{r['band']}", float(r["share_death"]))

phase_rows = []
for (phase, arm), sub in L.groupby(["phase", "pace_or_spin"]):
    phase_rows.append({
        "phase": phase, "arm": arm, "legal_balls": len(sub), "share_of_arm_balls": len(sub) / int(L["pace_or_spin"].eq(arm).sum()),
        "mean_ball_bowl": sub["ball_bowl"].mean(), "mean_pressure_bowl": sub["pressure_bowl"].mean(),
        "share_bowler_high": sub["band_bowl"].eq("high").mean(), "share_bowler_medium": sub["band_bowl"].eq("medium").mean(),
        "share_bowler_zero": sub["band_bowl"].eq("zero").mean(),
        "mean_pressure_bat": sub["pressure_bat"].mean(), "share_batter_high": sub["band"].eq("high").mean(),
        "economy_legal_balls": 6 * sub["charged_runs"].mean(), "bowler_wicket_rate": sub["bowler_wicket"].mean(),
        "high_band_bowler_balls": int(sub["band_bowl"].eq("high").sum()),
        "share_of_arm_high_band": int(sub["band_bowl"].eq("high").sum()) / int(L.loc[L["pace_or_spin"].eq(arm), "band_bowl"].eq("high").sum()),
        "status": "COMPUTED",
    })
phase_tab = pd.DataFrame(phase_rows)
phase_tab["phase"] = pd.Categorical(phase_tab["phase"], ["powerplay", "middle", "death"])
phase_tab = phase_tab.sort_values(["arm", "phase"])
reg.save(phase_tab, "02_pressure/phase_bowling_pressure.csv", "legal frame after fit_elo", "group by phase x pace_or_spin")
for _, r in phase_tab.iterrows():
    reg.fact(f"pr_phase_{r['arm']}_{r['phase']}_share_high", float(r["share_bowler_high"]))
    reg.fact(f"pr_phase_{r['arm']}_{r['phase']}_share_of_arm_high", float(r["share_of_arm_high_band"]))
    reg.fact(f"pr_phase_{r['arm']}_{r['phase']}_balls", int(r["legal_balls"]))
for arm in ("Pace", "Spin"):
    high_pre = PFa["band_bowl"].eq("high").to_numpy() & L["pace_or_spin"].eq(arm).to_numpy()
    for phase_name in ("powerplay", "middle", "death"):
        in_phase = L["phase"].eq(phase_name).to_numpy()
        reg.fact(f"pr_phase_{arm}_{phase_name}_share_of_arm_high_pre_fix", float((high_pre & in_phase).sum() / high_pre.sum()))
        arm_phase = L["pace_or_spin"].eq(arm).to_numpy() & in_phase
        reg.fact(f"pr_phase_{arm}_{phase_name}_share_high_pre_fix", float((PFa["band_bowl"].to_numpy()[arm_phase] == "high").mean()))

obs = []
o = lambda k, v, n="": obs.append({"observation": k, "value": v, "notes": n, "status": "COMPUTED"})
high = L["band"].eq("high")
o("batter_high_band_share_in_death_overs", float(L.loc[high, "phase"].eq("death").mean()))
o("batter_high_band_share_in_powerplay", float(L.loc[high, "phase"].eq("powerplay").mean()))
o("batter_high_band_share_in_chases", float(L.loc[high, "innings"].eq(2).mean()))
o("batter_high_band_share_from_occasion_above_1", float(L.loc[high, "occasion"].gt(1).mean()))
o("share_of_all_legal_balls_with_occasion_above_1", float(L["occasion"].gt(1).mean()))
o("share_of_final_balls_in_batter_high_band", float(L.loc[L["stage"].eq("Final"), "band"].eq("high").mean()))
o("share_of_league_balls_in_batter_high_band", float(L.loc[L["stage"].eq("League"), "band"].eq("high").mean()))
o("share_of_dead_rubber_balls_in_batter_high_band", float(L.loc[L["occasion"].eq(0.4), "band"].eq("high").mean()))
o("share_balls_batter_count_shock_positive", float(L["count_shock_bat"].gt(0).mean()))
o("share_balls_batter_final_shock_negative", float(L["shock_bat"].lt(0).mean()))
o("share_balls_shock_bat_at_cap_1", float(L["shock_bat"].ge(1).mean()))
o("share_balls_shock_bowl_at_cap_1", float(L["shock_bowl"].ge(1).mean()))
o("share_balls_ball_bat_clipped_at_1", float(L["ball_bat"].ge(1).mean()))
o("share_balls_ball_bowl_clipped_at_0", float(L["ball_bowl"].le(0).mean()))
o("corr_pressure_bat_pressure_bowl", float(L["pressure_bat"].corr(L["pressure_bowl"])))
o("corr_pressure_bat_bat_runs", float(L["pressure_bat"].corr(L["bat_runs"])))
o("corr_pressure_bat_striker_out", float(L["pressure_bat"].corr(L["striker_out"].astype(float))))
o("corr_pressure_bowl_charged_runs", float(L["pressure_bowl"].corr(L["charged_runs"])))
o("band_agreement_pre_elo_vs_final", same_band, "bands are recut after the expected-shock term is added; the final bands are the ones used")
o("high_band_balls_first_6_of_innings", int((high & L["n"].le(6)).sum()), "no shock is possible on balls 1-6")
o("share_of_ball_19_in_batter_high_band", float(L.loc[at19, "band"].eq("high").mean()), "ball 19 carried the run-of-play indexing bug before the fix (BUG-01)")
o("share_of_ball_19_in_bowler_high_band", float(L.loc[at19, "band_bowl"].eq("high").mean()), "after the BUG-01 fix")
o("share_of_ball_19_in_bowler_high_band_pre_fix", float(PFa.loc[at19.to_numpy(), "band_bowl"].eq("high").mean()), "pre-fix model, with the bug")
o("share_of_ball_18_in_batter_high_band", float(L.loc[L["n"].eq(18), "band"].eq("high").mean()), "neighbour ball for comparison")
o("share_of_ball_20_in_batter_high_band", float(L.loc[L["n"].eq(20), "band"].eq("high").mean()), "neighbour ball for comparison")
o("share_of_balls_1_to_18_in_batter_high_band", float(L.loc[L["n"].le(18), "band"].eq("high").mean()), "run of play is zero before ball 19")
o("share_of_balls_19_plus_in_batter_high_band", float(L.loc[L["n"].ge(19), "band"].eq("high").mean()))
o("share_of_balls_1_to_18_in_bowler_high_band", float(L.loc[L["n"].le(18), "band_bowl"].eq("high").mean()))
o("share_balls_excess_wicket_term_at_floor_minus_0_5", float(L["excess_shock_bat"].le(-0.5).mean()), "no wicket in the last six balls pushes the batter excess term to its floor")
for label, mask_now, mask_pre in [("final", L["stage"].eq("Final"), PF["stage"].eq("Final")), ("league", L["stage"].eq("League"), PF["stage"].eq("League")),
                                  ("death", L["phase"].eq("death"), PF["phase"].eq("death")), ("powerplay", L["phase"].eq("powerplay"), PF["phase"].eq("powerplay")),
                                  ("super_over", L["is_super_over"], PF["is_super_over"].astype(bool))]:
    o(f"share_of_{label}_balls_in_batter_high_band_now", float(L.loc[mask_now, "band"].eq("high").mean()), "current model")
    o(f"share_of_{label}_balls_in_batter_high_band_pre_fix", float(PF.loc[mask_pre, "band"].eq("high").mean()), "pre-fix model (raw-sum pressure)")
o("pressure_bat_p80_cutoff", float(cut["batter"][1]))
o("pressure_bowl_pace_p80_cutoff", float(cut["bowler_pace"][1]))
o("pressure_bowl_spin_p80_cutoff", float(cut["bowler_spin"][1]))
for k, v in checks.items():
    o("replication_max_abs_gap_" + k, v, "readout recomputation of the shock and run-of-play terms vs pipeline columns")
so = L["is_super_over"]
o("super_over_legal_balls", int(so.sum()))
o("super_over_mean_occasion", float(L.loc[so, "occasion"].mean()))
o("super_over_mean_pressure_bat", float(L.loc[so, "pressure_bat"].mean()))
o("super_over_mean_pressure_bowl", float(L.loc[so, "pressure_bowl"].mean()))
o("super_over_share_in_batter_high_band", float(L.loc[so, "band"].eq("high").mean()), "shock and run of play start at zero in a new innings; the situation term (knockout occasion, death ball) now carries them")
o("super_over_share_in_bowler_high_band", float(L.loc[so, "band_bowl"].eq("high").mean()))
o("super_over_share_in_batter_medium_band", float(L.loc[so, "band"].eq("medium").mean()))
o("super_over_min_pressure_bat_vs_p80_cutoff", float(L.loc[so, "pressure_bat"].min() - cut["batter"][1]), "negative means at least one super-over ball is below the high cut")
knock = L["stage"].isin(["Qualifier", "Eliminator", "Semi Final", "Final"]) & ~so
o("knockout_match_mean_pressure_bat_excluding_super_overs", float(L.loc[knock, "pressure_bat"].mean()))
o("knockout_match_share_in_batter_high_band", float(L.loc[knock, "band"].eq("high").mean()))
o("death_overs_mean_pressure_bat_excluding_super_overs", float(L.loc[L["phase"].eq("death") & ~so, "pressure_bat"].mean()))
so_cols = ["match_id", "comp_name", "stage", "innings", "n", "striker_name", "bowler_name", "bat_runs", "striker_out", "bowler_wicket",
           "occasion", "competition", "ball_bat", "ball_bowl", "rrr", "situation_bat", "situation_bowl", "shock_bat", "shock_bowl", "delta_bat", "delta_bowl",
           "pressure_bat", "pressure_bowl", "band", "band_bowl", "x_runs", "x_wicket", "e_bat", "e_bowl"]
so_balls = L.loc[so, so_cols].copy()
so_balls["status"] = "COMPUTED"
reg.save(so_balls, "02_pressure/super_over_pressure.csv", "legal frame after fit_elo, innings 3 and 4",
         "every legal super-over ball with its pressure terms and band")
obs = pd.DataFrame(obs)
reg.save(obs, "02_pressure/pressure_observations.csv", "legal frame after fit_elo", "derived shares and correlations")
for _, r in obs.iterrows():
    reg.fact("pro_" + r["observation"], r["value"])

existing_hb = pd.read_csv(ROOT / "exports" / "09_high_band_composition.csv")
mine_hb = L.loc[high].groupby(["phase", "pace_or_spin"]).size().reset_index(name="count")
merged = existing_hb.merge(mine_hb, on=["phase", "pace_or_spin"], suffixes=("_existing", "_recomputed"))
reg.fact("pr_high_band_composition_matches_export", bool((merged["count_existing"] == merged["count_recomputed"]).all()))
reg.close()
print("a done", checks)
