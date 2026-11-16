"""09_limitations, 08_validation/sanity_check_interpretations.md, 11_presentation_summary, 12_model_fixes.

Every number below is read from the facts and CSVs produced by scripts a-d.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

from common import CACHE, COMPONENTS, LABEL, OUT, ROOT, WEIGHTS, Registry, all_facts, load

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import player_ratings as pr  # noqa: E402

reg = Registry("e")
f = all_facts()
P = load()
PW = pr.PRESSURE_WEIGHTS
W_TXT = f"{PW['situation']:.2f} situation + {PW['shock']:.2f} shock + {PW['run_of_play']:.2f} run of play"
FLOOR, BALLS = pr.RANK_HIGH_BALLS, pr.RANK_BALLS


def pct(x, d=1):
    return f"{100 * float(x):.{d}f}%"


def num(x, d=0):
    return f"{float(x):,.{d}f}"


def r3(x):
    return f"{float(x):.3f}"


def g(key, d=3):
    return f"{float(f[key]):.{d}f}"


def trio(key):
    v = f[key]
    return f"{v[0]}/{v[1]}/{v[2]}"


fb = pd.read_csv(OUT / "07_rankings/final_batter_rankings.csv")
fw = pd.read_csv(OUT / "07_rankings/final_bowler_rankings.csv")
sp = pd.read_csv(OUT / "08_validation/sanity_check_players.csv")
ab = pd.read_csv(OUT / "08_validation/ablation_summary.csv")
infl = pd.read_csv(OUT / "08_validation/component_influence.csv")
cov = pd.read_csv(OUT / "08_validation/role_coverage.csv")
pws = pd.read_csv(OUT / "08_validation/pressure_weight_sensitivity.csv")
floor_tab = pd.read_csv(OUT / "08_validation/ranking_floor_sensitivity.csv")
summ = pd.read_csv(OUT / "03_components/component_summary.csv")
bands = pd.read_csv(OUT / "02_pressure/pressure_band_summary.csv")
phase = pd.read_csv(OUT / "02_pressure/phase_bowling_pressure.csv")
met = pd.read_csv(OUT / "05_expectation_models/expectation_model_metrics.csv")
elo_stab = pd.read_csv(OUT / "04_elo/elo_stability.csv")
xr_all = pd.read_csv(OUT / "05_expectation_models/xruns_calibration_deciles.csv")
xr_all = xr_all.loc[xr_all["scope"].eq("all") & xr_all["target"].str.startswith("bat_runs")].reset_index(drop=True)
pbat, pbowl = P["prefix_batters"], P["prefix_bowlers"]


def abl(skill, variant, col):
    return ab.loc[ab["skill"].eq(skill) & ab["variant"].eq(variant), col].iloc[0]


def sanity(name, skill):
    hit = sp.loc[sp["player_name"].eq(name) & sp["skill"].eq(skill)]
    return hit.iloc[0] if len(hit) else None


def pw_row(variant):
    return pws.loc[pws["variant"].str.startswith(variant)].iloc[0]


top20b, top20w = fb.head(20), fw.head(20)
samp = {
    "bat_top20_median_neff": top20b["n_eff"].median(), "bat_all_median_neff": fb["n_eff"].median(),
    "bowl_top20_median_neff": top20w["n_eff"].median(), "bowl_all_median_neff": fw["n_eff"].median(),
    "bat_top20_median_high": top20b["high_n_eff"].median(), "bat_all_median_high": fb["high_n_eff"].median(),
    "bowl_top20_median_high": top20w["high_n_eff"].median(), "bowl_all_median_high": fw["high_n_eff"].median(),
    "bowl_top20_high_lt60": int(top20w["high_n_eff"].lt(60).sum()), "bat_top20_high_lt60": int(top20b["high_n_eff"].lt(60).sum()),
    "bowl_top10_high_lt60": int(fw.head(10)["high_n_eff"].lt(60).sum()), "bat_top10_high_lt60": int(fb.head(10)["high_n_eff"].lt(60).sum()),
}
for k, v in samp.items():
    reg.fact("samp_" + k, float(v))
bh = bands.set_index(["scope", "band"])
cap = summ.loc[summ["population"].eq("ranked")].set_index(["skill", "component"])


def infl_get(skill, comp, col):
    return infl.loc[infl["skill"].eq(skill) & infl["component"].eq(comp), col].iloc[0]


top_var_b = infl.loc[infl["skill"].eq("batter")].sort_values("variance_share_of_composite", ascending=False)
top_var_w = infl.loc[infl["skill"].eq("bowler")].sort_values("variance_share_of_composite", ascending=False)
pre_names = ", ".join(f"{n} {h:.1f}" for n, h in f["pre_fix_top10_bowler_high_lt60_names"])
ROLE_WHY = ("Batters are compared partly within their batting role because the roles are different jobs. An opener faces the new ball with no wickets down and is judged on "
            "building an innings; a finisher arrives at the death, often after a collapse, and is judged on scoring fast against set bowlers. A strike rate or average "
            "is not comparable across those jobs without some adjustment. Pooling every batter rewards the role whose numbers are easiest to post. A role-only z-score "
            "assumes each role is equally deep in talent. Neither is a finding about cricket. The 50/50 blend (ROLE_BLEND = 0.5) is a stated compromise between the two.")

# ---------------------------------------------------------------- limitations register
R = []


def item(iid, cat, title, desc, evidence, sev, affected, status, impact, rec):
    R.append({"id": iid, "category": cat, "title": title, "description": desc, "evidence": evidence, "severity": sev,
              "affected_outputs": affected, "verification_status": status, "quantified_impact": impact, "suggested_follow_up_not_implemented": rec})


item("BUG-01", "BUG", "Run-of-play term read the whole innings on legal ball 19 (FIXED)",
     "In the pre-fix _shock_and_delta the 18-ball window was wicket_sum[end] - wicket_sum[end-18]. At position 18 (legal ball 19) end-18 = -1, and numpy index -1 is the LAST element, so the window subtracted the innings total: ball 19 used later balls, and the extreme values inflated the SD that scales every other ball. The window now subtracts 0 when end-18 < 0.",
     f"Pre-fix behaviour rebuilt and checked against the pre-fix model's own columns (max gap {g('bug_rop_replica_vs_pre_fix_model_maxgap', 1)}). Ball 19 mean run of play: batter {g('bug_rop_delta_bat_mean_at_19_pre_fix')} before, {g('bug_rop_delta_bat_mean_at_19')} now; bowler {g('bug_rop_delta_bowl_mean_at_19_pre_fix')} before, {g('bug_rop_delta_bowl_mean_at_19')} now. Scales: runs {g('bug_rop_scale_runs_pre_fix', 4)} before, {g('scale_run_of_play_runs', 4)} now; wickets {g('bug_rop_scale_wicket_pre_fix', 4)} before, {g('scale_run_of_play_wicket', 4)} now. Ball-19 bowler high-band share {pct(f['bug_rop_ball19_bowler_high_share_pre_fix'])} before, {pct(f['pro_share_of_ball_19_in_bowler_high_band'])} now (neighbouring balls 18 and 20 sit at a similar level under the new weights).",
     "High (bowlers), Low (batters)", "pressure, bands, every band and clutch component", "FIXED",
     f"The fix ships together with the other changes, so its ranking effect is not separable from them in the final tables. Whole-model change vs pre-fix: batters Spearman {r3(abl('batter', 'previous_model_before_fixes', 'spearman_vs_full'))}, top-20 overlap {int(abl('batter', 'previous_model_before_fixes', 'top20_overlap'))}/20; bowlers {r3(abl('bowler', 'previous_model_before_fixes', 'spearman_vs_full'))}, {int(abl('bowler', 'previous_model_before_fixes', 'top20_overlap'))}/20.",
     "")
item("BUG-02", "BUG", "Deck export 10 labels final shock as 'count_shock'",
     "write_deck_exports writes sample['shock_bat'] and sample['shock_bowl'] into columns named count_shock_bat / count_shock_bowl. After _add_expected_shock those columns hold count + excess shock, not the count part.",
     f"exports/10_sample_innings_timeline.csv count_shock_bat equals final shock: {f['export10_count_shock_bat_equals_final_shock']}; equals count part: {f['export10_count_shock_bat_equals_count_part']}.",
     "Low", "exports/10_sample_innings_timeline.csv and any slide built from it", "VERIFIED (open)",
     "Labels only; values are the shock actually used. 06_shock/shock_innings_timeline.csv splits count, excess and final.", "Rename the columns or write both parts.")
item("BUG-03", "BUG / INCONSISTENCY", "Bowler clutch compared spell economy without extras to career economy with extras (FIXED)",
     "The high-band spell economy uses charged runs on legal balls (wides and no-balls are not legal rows). The pre-fix career economy it was compared with used every delivery, so a spell was flattered by the bowler's own wide/no-ball rate. The comparison now uses legal-ball career economy (charged runs / legal balls, level-weighted), and the scale is the SD of legal-ball spell economy.",
     f"Ranked bowlers: career economy with extras minus legal-ball economy = {g('clutch_bowl_basis_diff_mean_ranked')} runs/over on average. On the current high-band spells, {pct(f['clutch_bowl_share_spells_beating_own_rate_old_basis_same_spells'])} would beat the bowler's own rate on the old basis against {pct(f['clutch_bowl_share_spells_beating_own_rate_now'])} on the legal-ball basis; mean own gap {g('clutch_bowl_mean_own_gap_old_basis_same_spells')} vs {g('clutch_bowl_mean_own_gap_now')} scale units. Comparison economy equals legal-ball economy to {g('clutch_bowl_comparison_basis_maxgap_vs_legal_economy', 1)}.",
     "Medium", "bowler clutch (weight 0.15)", "FIXED", f"Clutch scale {g('clutch_bowl_scale_pre_fix')} before, {g('clutch_bowl_scale')} now.", "")
item("KI-01", "KNOWN ISSUE", "Form term used a full-career bar (look-ahead)",
     "Legacy form_by_season (git 29956ed) compared each of the previous 8 innings with the player's FULL-CAREER strike rate/economy, which includes later matches.",
     f"Source at git {P['head_rev'][:7]}: bar = float(career.loc[player]). Form was removed earlier (7 terms, consistency 0.10).",
     "Resolved", "legacy composite only", "VERIFIED (legacy); NOT_APPLICABLE (current)",
     f"Form isolated on the pre-fix frame (legacy 8-term vs pre-fix 7-term): batters Spearman {g('form_isolation_batter_spearman')}, top-20 overlap {f['form_isolation_batter_top20_overlap']}/20; bowlers {g('form_isolation_bowler_spearman')}, {f['form_isolation_bowler_top20_overlap']}/20.",
     "If Form returns, use a point-in-time bar.")
item("KI-02", "KNOWN ISSUE", "xWicket is trained on bowler wickets but charged against every striker dismissal",
     "Wicket cells learn bowler_wicket (caught, bowled, LBW, stumped, hit wicket). The batter ball value subtracts 4 x (striker_out - xW), and striker_out includes run outs, retired out and obstructing. Non-striker dismissals hit nobody's ball value.",
     f"Legal balls: striker_out {num(f['ds_striker_out_legal'])} vs bowler_wicket {num(f['ds_bowler_wicket_legal'])}; striker run outs {num(f['ds_striker_runouts_legal'])}; non-striker dismissals {num(f['ds_nonstriker_dismissals_legal'])}. Mean xW {pct(f['xw_mean'], 2)} vs striker-out rate {pct(f['striker_out_rate'], 2)}. Mean wicket part of ball value: batter {g('e_bat_wicket_part_mean', 4)}, bowler {g('e_bowl_wicket_part_mean', 4)} per ball.",
     "Low-Medium", "e_bat, batter Elo, batter band components", "VERIFIED (open)",
     f"Batter wicket penalty biased by about {g('e_bat_wicket_part_mean', 4)} runs-equivalent per ball overall; concentrated on batters involved in run outs.",
     "Train a striker-dismissal expectation, or exclude run outs from the batter wicket term.")
item("KI-03", "KNOWN ISSUE", "No wickets-fallen feature in the expectation model (FIXED)",
     "Expectation cells were ladder x phase x arm. The full cell now adds wickets down (0-1, 2-3, 4-5, 6-7, 8+), shrunk toward ladder x phase x arm with the same 30-ball pull.",
     f"Runs actual minus expected per ball, before -> now: 0-1 down {g('wf_0-1_runs_resid_pre_fix')} -> {g('wf_0-1_runs_resid')}; 2-3 {g('wf_2-3_runs_resid_pre_fix')} -> {g('wf_2-3_runs_resid')}; 4-5 {g('wf_4-5_runs_resid_pre_fix')} -> {g('wf_4-5_runs_resid')}; 6-7 {g('wf_6-7_runs_resid_pre_fix')} -> {g('wf_6-7_runs_resid')}; 8-9 {g('wf_8-9_runs_resid_pre_fix')} -> {g('wf_8-9_runs_resid')}. Mean bowler ball value at 8-9 down {g('wf_8-9_e_bowl_pre_fix')} -> {g('wf_8-9_e_bowl')}.",
     "High", "e_bat, e_bowl, Elo, all band components", "FIXED",
     f"The tail residual shrinks by {100 * (1 - abs(f['wf_8-9_runs_resid']) / abs(f['wf_8-9_runs_resid_pre_fix'])):.0f}%. A residual remains because the cell is pulled toward the coarser level and is learned only from earlier balls.", "")
item("KI-04", "KNOWN ISSUE", "Wides and no-balls never enter the ball value or Elo",
     "Charging follows the laws in `conceded`. But ball value, Elo, xR, bands and clutch use legal rows only, so wide and no-ball runs and wickets off wides are invisible there. Baseline economy and peers include them.",
     f"{num(f['ds_runs_conceded_on_illegal_deliveries'])} of {num(f['ds_runs_conceded_total'])} conceded runs ({pct(f['ds_runs_conceded_on_illegal_deliveries'] / f['ds_runs_conceded_total'])}) are on illegal deliveries; {f['ds_bowler_wickets_illegal_delivery']} bowler wickets (stumpings off wides) are credited in baseline only.",
     "Medium", "e_bowl, bowler Elo, bowler bands, bowler clutch", "VERIFIED (open)", "A wayward bowler is penalised only in baseline (0.20) and peers (0.10).", "Attach illegal-delivery runs to the next legal ball or model them separately.")
item("M-01", "METHODOLOGICAL", "Recent events still lift the high band, but no longer define it (PARTLY FIXED)",
     f"Pressure was the raw sum of situation, shock and run of play. Shock and run of play have much larger spreads, so the high band was almost entirely the six balls after a wicket (batters) or a boundary (bowlers). Each term is now divided by its own SD and weighted: {W_TXT}.",
     f"Batter high-band balls within six balls after a wicket: {pct(f['se_pre_fix_bat_high_after_wicket'])} before, {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'])} now (base rate {pct(f['se_share_of_balls_within_6_after_a_wicket'])}). Bowler high-band balls after a four or six in the last six: {pct(f['se_pre_fix_bowl_high_after_boundary'])} before, {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'])} now (base rate {pct(f['se_share_of_all_balls_with_four_or_six_in_last_6'])}). Situation share of pressure variance: batters {pct(f['pr_var_share_situation_bat_pre_fix'])} -> {pct(f['pr_var_share_situation_bat'])}, bowlers {pct(f['pr_var_share_situation_bowl_pre_fix'])} -> {pct(f['pr_var_share_situation_bowl'])}. Finals in the batter high band: {pct(f['pro_share_of_final_balls_in_batter_high_band_pre_fix'])} -> {pct(f['pro_share_of_final_balls_in_batter_high_band_now'])}.",
     "Medium (interpretation)", "every 'pressure' claim", "PARTLY FIXED",
     f"Recent events are still over-represented by design (shock {PW['shock']:.2f} + run of play {PW['run_of_play']:.2f} of the weight). See 08_validation/pressure_weight_sensitivity.csv.", "")
item("M-02", "METHODOLOGICAL", "The first 18 balls of an innings are rarely high pressure for batters",
     "Shock needs six previous balls and run of play needs eighteen, and the batter powerplay difficulty is moderate.",
     f"Batter high-band share on balls 1-18: {pct(f['pro_share_of_balls_1_to_18_in_batter_high_band'], 1)} vs {pct(f['pro_share_of_balls_19_plus_in_batter_high_band'])} from ball 19. Bowlers {pct(f['pro_share_of_balls_1_to_18_in_bowler_high_band'])} on balls 1-18 (see M-17).",
     "Medium", "opening batters' high-band samples", "VERIFIED", "", "")
item("M-03", "METHODOLOGICAL", "Pressure is a relative index",
     "Each term is divided by its SD and the bands are percentiles, so the absolute value of pressure has no cricket meaning; only the order of balls does.",
     f"Batter p50 = {g('pr_batter_p50')}, p80 = {g('pr_batter_p80')}; the batter excess-wicket term sits at its -0.5 floor on {pct(f['pro_share_balls_excess_wicket_term_at_floor_minus_0_5'])} of balls.",
     "Low", "interpretation of the pressure scale", "VERIFIED", "", "")
item("M-04", "METHODOLOGICAL", "Normalisation uses the full 2022-2026 sample",
     "Band cut-offs, the pressure-term SDs, z-score reference pools, and the shock and run-of-play scales are computed on all seasons, so they are not point-in-time. Per-ball xR/xW and Elo are sequential and do not look ahead.",
     "Code reading: _cut_band quantiles, _combine_pressure SDs, zscore reference.", "Low (retrospective rating)", "bands, all z-scores", "VERIFIED", "Fine for a retrospective ranking; not valid as a live metric.", "")
item("M-05", "METHODOLOGICAL", "Season decay applies to some components only",
     "0.9^(2026-season) weights the band rates and n_eff. Baseline rates, peers, clutch and consistency are level-weighted only.",
     "Code reading: career_rate/weighted_count vs _weighted_mean and raw totals.", "Low-Medium", "baseline, peers, clutch, consistency", "VERIFIED", "", "")
item("M-06", "METHODOLOGICAL", "Small high-pressure samples at the top of the bowling table (FIXED)",
     f"Eligibility was n_eff >= 120 and high-band n_eff >= 30. The high-band floor is now {FLOOR} (RANK_HIGH_BALLS).",
     f"Before the fix, {f['pre_fix_top10_bowler_high_lt60']} of the top-10 bowlers had high n_eff < 60 ({pre_names}). Now {f['top10_bowler_high_lt60']}; the smallest high n_eff in the bowling top 10 is {g('top10_bowler_min_high_n_eff', 1)} and in the top 20 {g('top20_bowler_min_high_n_eff', 1)}. Ranked pools: batters {f['pre_fix_ranked_batters']} -> {f['ranked_batters']}, bowlers {f['pre_fix_ranked_bowlers']} -> {f['ranked_bowlers']}.",
     "Medium", "top of the bowling table", "FIXED",
     f"With the same scores, a floor of 30 would keep {f['floor_bowler_30_top20_overlap']}/20 of the bowling top 20 and {f['floor_batter_30_top20_overlap']}/20 of the batting top 20 (08_validation/ranking_floor_sensitivity.csv). Ranks still carry no intervals.", "Bootstrap over matches for rank intervals.")
item("M-07", "METHODOLOGICAL", "Expectation models discriminate weakly (OPEN)",
     "xR and xW are cell means with an Elo tilt. The wickets-down cell improves calibration by wickets fallen but barely changes ball-level discrimination; single-ball outcomes in T20 are mostly noise.",
     f"xR MAE {g('xm_xR_bat_runs_pre_fix_mae', 4)} -> {g('xm_xR_bat_runs_mae', 4)} against {g('xm_xR_bat_runs_mae_constant_in_sample_mean', 4)} for a constant; R^2 {g('xm_xR_bat_runs_pre_fix_r_squared', 4)} -> {g('xm_xR_bat_runs_r_squared', 4)}. xW AUC {g('xm_xW_bowler_wicket_pre_fix_auc', 4)} -> {g('xm_xW_bowler_wicket_auc', 4)}; calibration slope {g('xm_xR_bat_runs_calibration_slope_ols')} (xR), logistic {g('xm_xW_bowler_wicket_calibration_slope_logistic')} (xW).",
     "Medium", "ball value for every component except baseline", "VERIFIED (open)", "Ball values stay close to 'actual minus context average'. Player ratings average over hundreds of balls, which is where the signal is.", "")
item("M-08", "METHODOLOGICAL", "Consistency works against the composite for batters",
     "Consistency rewards a low spread of match ball value; explosive batters score low.",
     f"Ranked batters: corr(consistency, composite) {g('corr_batters_consistency_composite')}. Variance share of consistency in the batter composite {pct(infl_get('batter', 'consistency', 'variance_share_of_composite'))}.",
     "Low", "batter composite", "VERIFIED", "", "")
item("M-09", "METHODOLOGICAL", "Lower-level events are discounted twice",
     "Emerging/Rising balls count 0.5 (level weight) and also carry a 0.7 competition multiplier in pressure.", f"{num(f['ds_legal_T20'])} legal balls in {f['ds_matches_T20']} matches.", "Low", "players with many A-team matches", "VERIFIED", "", "")
item("M-10", "DATA", "Competition coverage", "IPL 2022-2026, bilateral and tri-series T20Is, two Asia Cups and two A-team events. No T20 World Cup, no other franchise leagues. Tri-series and Asia Cup finals carry the same 3.0 occasion as an IPL final.",
     f"Matches with legal balls: IPL {f['ds_matches_IPL']}, T20I {f['ds_matches_T20I']}, T20 {f['ds_matches_T20']}.", "Medium", "external validity", "VERIFIED", "", "")
item("M-11", "DATA", "DLS detail is limited", "Only revised overs and revised target are supplied; no par scores or resource tables.",
     f"Reduced matches {f['dls_reduced_matches']}; chases with no supplied target {f['dls_excluded_matches']} matches.", "Low", "required-rate term", "VERIFIED", "", "")
item("M-12", "DATA", "Source anomalies kept as supplied", "Deliveries with a player missing from the squad sheet are kept; one over has more than six legal balls; three rows have extras amounts that do not fit the type.",
     f"sheet_gap deliveries {f['ds_deliveries_flagged_sheet_gap']}; overs with >6 legal balls {f['ds_overs_with_more_than_6_legal_balls']}.", "Low", "", "VERIFIED", "", "")
item("M-13", "ASSUMPTION", "'Other' extras are treated as illegal", "Decided in cleaning: counting them legal puts 150 innings past 120 legal balls.", f"{f['ds_other_extras']} 'other' deliveries.", "Low", "", "EXISTING", "", "")
item("M-14", "CODE HYGIENE", "Dead code and stale comments", "expectation_tables() and venue_ratings() are defined but never called; run_elo's `venues` argument is ignored.", "grep over *.py and *.ipynb", "Low", "", "VERIFIED", "", "")
item("M-15", "METHODOLOGICAL", "Elo affects the ranking only through expectations", "The composite is built from ball values; final Elo ratings are not a component.",
     f"Season-end rating stability (Spearman): batters {g('elo_yoy_batter_2022', 2)}-{g('elo_yoy_batter_2025', 2)}, bowlers {g('elo_yoy_bowler_2023', 2)}-{g('elo_yoy_bowler_2025', 2)}. Step-size sensitivity: composite Spearman >= {min(f['elo_sens_half_steps_batter_spearman'], f['elo_sens_double_steps_bowler_spearman'], f['elo_sens_half_steps_bowler_spearman'], f['elo_sens_double_steps_batter_spearman']):.3f}.",
     "Low", "", "VERIFIED", "", "")
item("M-16", "METHODOLOGICAL", "Super overs: knockout occasion now reaches the high band",
     "Super overs are included with occasion max(stage, 1.5), death-phase ball difficulty and a chase rate in innings 4. Shock and run of play start at zero in a new innings; under the raw sum that kept every super-over ball below the high cut, and under the weighted index the situation term carries them.",
     f"{f['pro_super_over_legal_balls']:.0f} legal balls; batter high-band share {pct(f['pro_share_of_super_over_balls_in_batter_high_band_pre_fix'])} before, {pct(f['pro_super_over_share_in_batter_high_band'])} now; bowler {pct(f['pro_super_over_share_in_bowler_high_band'])} now. Ranking effect vs excluding them: Spearman {abl('batter', 'exclude_super_overs', 'spearman_vs_full'):.4f} (batters), {abl('bowler', 'exclude_super_overs', 'spearman_vs_full'):.4f} (bowlers).",
     "Low", "super-over specialists' high band and clutch", "VERIFIED", "", "")
item("M-17", "METHODOLOGICAL", "Bowler high band moved toward the powerplay (NEW, side effect of the pressure fix)",
     "With the situation term now carrying most of the variance, the bowler high band follows the existing bowler ball-difficulty table: powerplay 0.32, middle 0.24, death 0.32 only to a top-7 batter (else 0.14), minus 0.10 at 2-4 down and 0.25 at 5+ down. Death bowling usually comes with wickets down or a lower-order striker, so it scores lower than the new ball.",
     f"Share of pace high-band balls by phase, before -> now: powerplay {pct(f['pr_phase_Pace_powerplay_share_of_arm_high_pre_fix'])} -> {pct(f['pr_phase_Pace_powerplay_share_of_arm_high'])}, middle {pct(f['pr_phase_Pace_middle_share_of_arm_high_pre_fix'])} -> {pct(f['pr_phase_Pace_middle_share_of_arm_high'])}, death {pct(f['pr_phase_Pace_death_share_of_arm_high_pre_fix'])} -> {pct(f['pr_phase_Pace_death_share_of_arm_high'])}. Pace death balls in the high band: {pct(f['pr_phase_Pace_death_share_high_pre_fix'])} -> {pct(f['pr_phase_Pace_death_share_high'])}.",
     "Medium-High (interpretation)", "bowler bands, bowler high band and clutch, the bowling ranking", "VERIFIED (open)",
     "Bowlers who mainly bowl the powerplay gain high-band balls; death specialists lose them. This is a consequence of the ball-difficulty table, which the weighting exposed; it was not tuned in this round.",
     "Revisit the bowler ball-difficulty table (for example, do not lower death difficulty for wickets down) or give bowlers their own situation weight.")
item("M-18", "MODELLING CHOICE", "Batters are z-scored half within role, half against all batters",
     ROLE_WHY,
     f"Top-20 batting role mix (top/middle/lower): role-only z {trio('rolerep_current_role_blend_1_role_only_top20')}, official 50/50 blend {trio('rolerep_current_role_blend_0_5_official_top20')}, pooled z {trio('rolerep_current_role_blend_0_pooled_top20')}. Before the fixes: role-only {trio('rolerep_pre_fix_with_role_split_top20')}, pooled {trio('rolerep_pre_fix_without_role_split_top20')}. Rank agreement with the official blend: role-only Spearman {r3(abl('batter', 'role_blend_1_role_only_z', 'spearman_vs_full'))}, pooled {r3(abl('batter', 'role_blend_0_pooled_z', 'spearman_vs_full'))}.",
     "Medium", "batting ranking and its role mix", "MODELLING CHOICE",
     "The gap between role-only and pooled rankings is much smaller after the wickets-down fix, which suggests part of what role normalisation corrected was the tail-end expectation bias (KI-03).", "")
item("M-19", "MODELLING CHOICE", f"Pressure weights {PW['situation']:.2f}/{PW['shock']:.2f}/{PW['run_of_play']:.2f} are a judgement",
     "The weights were chosen from a tuning table so that situation leads but recent events still count. They are not estimated from outcomes.",
     "; ".join(f"{r['variant']}: batter after-wicket {pct(r['batter_high_band_balls_within_6_after_wicket'])}, finals high {pct(r['batter_high_share_of_final_balls'])}, pace death {pct(r['pace_high_band_share_in_death'])}"
               + (f", Spearman bat {r['batter_spearman_vs_official']:.3f} / bowl {r['bowler_spearman_vs_official']:.3f}" if pd.notna(r.get("batter_spearman_vs_official")) and r["variant"] != "official" else "")
               for _, r in pws.iterrows()),
     "Medium", "bands and every band/clutch component", "MODELLING CHOICE", "", "")
lim = pd.DataFrame(R)
reg.save(lim, "09_limitations/limitations_register.csv", "facts from scripts a-d", "one row per issue")

# ---------------------------------------------------------------- methodological audit
W = []
w = W.append
w("# Methodological audit\n")
w("This audit describes what the code in this repository executes, checked against the data. Where a number is given, it comes from a file in `research_readout/` (see `11_presentation_summary/source_traceability.csv`). The fixes made in November 2026 are listed in section 0 and measured in `12_model_fixes/`.\n")
w("## 0. Version under audit\n")
w(f"- `player_ratings.py`: **seven** weighted terms. Baseline 0.20, zero band 0.10, medium band 0.15, high band 0.20, clutch 0.15, peers 0.10, consistency 0.10. They sum to {f['weights_current_sum']:.2f}.")
w("- Changes in this round, all in `player_ratings.py`:")
w("  - BUG-01: the 18-ball run-of-play window no longer reads the innings total on legal ball 19.")
w(f"  - Pressure: each term over its own SD, weighted {W_TXT} (`PRESSURE_WEIGHTS`). Before, the three terms were added raw.")
w("  - Expectation cells: the full cell adds wickets down (0-1, 2-3, 4-5, 6-7, 8+).")
w(f"  - Batter z-scores: {pr.ROLE_BLEND} within role + {1 - pr.ROLE_BLEND} against all batters (`ROLE_BLEND`). Before, within role only.")
w(f"  - Ranking floor: high-band n_eff ≥ {FLOOR} (`RANK_HIGH_BALLS`, was 30); n_eff ≥ {BALLS} unchanged.")
w("  - Bowler clutch compares legal-ball spell economy with legal-ball career economy.")
w(f"- The model before these fixes is kept at `research_readout/_scripts/reference/player_ratings_pre_fix.py` and run in full for every before/after number. The 8-term version with Form (git `{P['head_rev'][:7]}`) is scored on the pre-fix frame, so legacy vs pre-fix isolates the Form change.")
w(f"- Super overs are included: {f['ds_super_over_deliveries_included']} deliveries, {f['ds_super_over_legal_balls_included']} legal balls, {f['ds_super_over_matches']} matches, each ball a death ball at occasion max(stage, 1.5).")
w(f"- Reproduction: the in-memory run reproduces the shipped `ratings/batters.csv` ranks: {f['rank_reproduces_shipped_batters']}. Ranked: {f['ranked_batters']} batters, {f['ranked_bowlers']} bowlers.\n")
w("## 1. Data and cleaning\n")
w(f"- {num(f['ds_raw_deliveries_source_file'])} deliveries; none are deleted in cleaning. Duplicate delivery keys: {f['ds_duplicate_delivery_keys_match_innings_ballnum']}.")
w(f"- Excluded from ball value: {num(f['ds_illegal_deliveries_wide_noball_other'])} illegal deliveries ({num(f['ds_wides'])} wides, {f['ds_noballs']} no-balls, {f['ds_other_extras']} 'other').")
w(f"- Used: **{num(f['ds_legal_balls_used_in_ratings'])} legal balls** in {f['ds_matches_with_legal_balls']} matches, {f['ds_first_match_date']} to {f['ds_last_match_date']}. IPL {num(f['ds_legal_IPL'])} balls in {f['ds_matches_IPL']} matches; T20I {num(f['ds_legal_T20I'])} in {f['ds_matches_T20I']}; T20 (Emerging/Rising) {num(f['ds_legal_T20'])} in {f['ds_matches_T20']}.")
w(f"- Reduced matches: {f['dls_reduced_matches']}. Reduced chases with no supplied target get no required rate ({f['dls_excluded_matches']} matches). DLS par scores are not in the data (REQUIRES_DATA).\n")
w("## 2. Pressure as executed\n")
w(f"```\npressure = {PW['situation']:.2f} x situation / sd(situation) + {PW['shock']:.2f} x shock / sd(shock) + {PW['run_of_play']:.2f} x run_of_play / sd(run_of_play)\nsituation = occasion x competition x ball difficulty\n```")
w("  Computed separately for the batter and the bowler side; the SDs are population SDs over all legal balls (`02_pressure/pressure_formula_as_executed.csv`).")
w("- Occasion: Final 3.0, Semi 2.0, Qualifier/Eliminator 1.5, Super 4 1.3, League 1.0, other bilateral 0.8, dead rubber 0.4 (" + str(f["ds_dead_rubber_matches_occasion_0_4"]) + " matches). A super-over ball takes max(stage occasion, 1.5). Competition: 0.7 for Emerging/Rising, otherwise 1.0.")
w("- Ball difficulty (clipped 0..1). Batter: phase term (PP 0.25, middle 0.10, death 0.40) + wickets term (2–4 down 0.15, 5+ down 0.30) + chase-rate term (RRR ≥ 8 adds 0.15, ≥ 12 adds 0.30). Bowler: phase term (PP 0.32, middle 0.24; death 0.32 to a top-7 batter, otherwise 0.14) + wickets term (−0.10 or −0.25) + the same rate term.")
w(f"- Shock: a count part over the previous six legal balls (batter 0.33 per wicket + 0.05 per dot; bowler 0.33 per six + 0.12 per four) plus an excess part (batter: bowler wickets − xW; bowler: charged − xR), scaled by SDs of {g('scale_excess_wicket', 4)} and {g('scale_excess_runs', 4)}, clipped −0.5..1.")
w(f"- Run of play: last 6 vs last 18 balls (wickets per ball for batters, bat runs per ball for bowlers), scaled by SDs of {g('scale_run_of_play_wicket', 4)} and {g('scale_run_of_play_runs', 4)} (pre-fix, with BUG-01: {g('bug_rop_scale_wicket_pre_fix', 4)} and {g('bug_rop_scale_runs_pre_fix', 4)}), clipped −0.5..1.")
w(f"- Replication: the readout recomputes every term independently; max gap against the pipeline is {max(v for k, v in f.items() if k.startswith('replication_maxgap_')):.1e}.")
w(f"- Final cut-offs: batter p50 {g('pr_batter_p50')}, p80 {g('pr_batter_p80')}. Pace p50 {g('pr_bowler_pace_p50')}, p80 {g('pr_bowler_pace_p80')}. Spin p50 {g('pr_bowler_spin_p50')}, p80 {g('pr_bowler_spin_p80')}.")
w(f"- Variance shares of batter pressure (now / before): situation {pct(f['pr_var_share_situation_bat'])} / {pct(f['pr_var_share_situation_bat_pre_fix'])}, shock {pct(f['pr_var_share_shock_bat'])} / {pct(f['pr_var_share_shock_bat_pre_fix'])}, run of play {pct(f['pr_var_share_run_of_play_bat'])} / {pct(f['pr_var_share_run_of_play_bat_pre_fix'])}. Bowlers: {pct(f['pr_var_share_situation_bowl'])} / {pct(f['pr_var_share_situation_bowl_pre_fix'])}, {pct(f['pr_var_share_shock_bowl'])} / {pct(f['pr_var_share_shock_bowl_pre_fix'])}, {pct(f['pr_var_share_run_of_play_bowl'])} / {pct(f['pr_var_share_run_of_play_bowl_pre_fix'])}.")
w(f"- **What the high band captures now.** {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'])} of batter high-band balls follow a wicket within six balls (before {pct(f['se_pre_fix_bat_high_after_wicket'])}; base rate {pct(f['se_share_of_balls_within_6_after_a_wicket'])}). {pct(f['pro_share_of_death_balls_in_batter_high_band_now'])} of death balls and {pct(f['pro_share_of_final_balls_in_batter_high_band_now'])} of final balls are batter-high. For bowlers the high band leans to the powerplay (M-17).\n")
w("## 3. Expectation models and ball value\n")
w("- Cells are ladder → phase → phase × arm → phase × arm × wickets down, each pulled toward the coarser level with 30 balls. Priors 1.0 run and 0.05 wickets. Every prediction uses only balls already bowled.")
w("- The Elo gap is 0.15 × (batter − bowler)/400 + 0.05 × (side gap)/400 + 0.10 × (ground − 1500)/400. xR = cell mean × exp(gap), capped 0..6; xW = logistic(logit(cell rate) − gap), capped 0.002..0.40.")
w("- Batter ball value = (bat runs − xR) − 4 × (striker out − xW). Bowler ball value = (xR_bowl − charged) + 4 × (bowler wicket − xW).")
w(f"- xR: MAE {g('xm_xR_bat_runs_mae', 4)} (before {g('xm_xR_bat_runs_pre_fix_mae', 4)}; constant {g('xm_xR_bat_runs_mae_constant_in_sample_mean', 4)}), RMSE {g('xm_xR_bat_runs_rmse', 4)}, OLS slope {g('xm_xR_bat_runs_calibration_slope_ols', 3)}, R² {g('xm_xR_bat_runs_r_squared', 4)} (before {g('xm_xR_bat_runs_pre_fix_r_squared', 4)}).")
w(f"- xW against bowler wickets: AUC {g('xm_xW_bowler_wicket_auc', 4)} (before {g('xm_xW_bowler_wicket_pre_fix_auc', 4)}), Brier {g('xm_xW_bowler_wicket_brier', 5)} vs {g('xm_xW_bowler_wicket_brier_constant', 5)} constant, logistic slope {g('xm_xW_bowler_wicket_calibration_slope_logistic')}. Discrimination stays weak (M-07).")
w(f"- Runs actual minus expected at 8–9 down: {g('wf_8-9_runs_resid')} per ball (before {g('wf_8-9_runs_resid_pre_fix')}); at 0–1 down {g('wf_0-1_runs_resid')} (before {g('wf_0-1_runs_resid_pre_fix')}).\n")
w("## 4. Elo\n")
w(f"- Ratings start at 1500 per (player, ladder). Steps 4 / 16 / 20, not halved. Final raw ratings: batters {g('elo_batter_elo_min', 1)}–{g('elo_batter_elo_max', 1)} (SD {g('elo_batter_elo_sd', 1)}); bowlers {g('elo_bowler_elo_min', 1)}–{g('elo_bowler_elo_max', 1)} (SD {g('elo_bowler_elo_sd', 1)}).")
w(f"- Step-size sensitivity: composite Spearman {g('elo_sens_half_steps_batter_spearman')} / {g('elo_sens_double_steps_batter_spearman')} for batters, {g('elo_sens_half_steps_bowler_spearman')} / {g('elo_sens_double_steps_bowler_spearman')} for bowlers.\n")
w("## 5. Components and composite\n")
for comp in COMPONENTS:
    w(f"- **{LABEL[comp]}** (weight {WEIGHTS[comp]:.2f}). Ranked batters: SD {cap.loc[('batter', comp), 'sd']:.3f}, variance share {pct(infl_get('batter', comp, 'variance_share_of_composite'))}. Ranked bowlers: SD {cap.loc[('bowler', comp), 'sd']:.3f}, variance share {pct(infl_get('bowler', comp, 'variance_share_of_composite'))}.")
w(f"- Batter z-scores: {pr.ROLE_BLEND} × z within top/middle/lower order + {1 - pr.ROLE_BLEND} × z across all batters. Bowlers are z-scored across all bowlers; their bands are cut within pace and within spin.")
w(f"- Why the role blend: {ROLE_WHY}")
w(f"- Eligibility: n_eff ≥ {BALLS} and high-band n_eff ≥ {FLOOR}, both decay- and level-weighted.\n")
w("## 6. Robustness\n")
for skill in ["batter", "bowler"]:
    w(f"- {skill.title()}s, compared with the official ranking:")
    w(f"  - the model before the fixes: Spearman {r3(abl(skill, 'previous_model_before_fixes', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'previous_model_before_fixes', 'top20_overlap'))}")
    w(f"  - baseline only: Spearman {r3(abl(skill, 'baseline_only', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'baseline_only', 'top20_overlap'))}")
    w(f"  - equal weights: Spearman {r3(abl(skill, 'equal_weights', 'spearman_vs_full'))}")
    w(f"  - raw-sum pressure with the bug fixed: Spearman {r3(abl(skill, 'pressure_raw_sum_bug_fixed', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'pressure_raw_sum_bug_fixed', 'top20_overlap'))}")
    for v in ["pressure_weights_40_35_25", "pressure_weights_50_30_20", "pressure_weights_70_20_10", "pressure_weights_equal_thirds"]:
        w(f"  - {v}: Spearman {r3(abl(skill, v, 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, v, 'top20_overlap'))}")
    if skill == "batter":
        w(f"  - role-only z: Spearman {r3(abl(skill, 'role_blend_1_role_only_z', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'role_blend_1_role_only_z', 'top20_overlap'))}; pooled z: {r3(abl(skill, 'role_blend_0_pooled_z', 'spearman_vs_full'))}, {int(abl(skill, 'role_blend_0_pooled_z', 'top20_overlap'))}")
    w(f"  - super overs excluded: Spearman {abl(skill, 'exclude_super_overs', 'spearman_vs_full'):.4f}")
w("\n## 7. Issues\n")
w("See `limitations_register.csv`. Fixed this round: BUG-01, BUG-03, KI-03, M-06; partly fixed: M-01. Open: BUG-02, KI-02, KI-04, M-07. New: M-17 (bowler high band leans to the powerplay). Modelling choices stated as such: M-18 (role blend), M-19 (pressure weights).")
(OUT / "09_limitations").mkdir(exist_ok=True)
(OUT / "09_limitations/methodological_audit.md").write_text("\n".join(W), encoding="utf-8")
reg.note("09_limitations/methodological_audit.md", "facts a-d", "generated text")

# ---------------------------------------------------------------- cricketing interpretations
ci = []
c = ci.append
c("# Cricketing interpretations\n")
c("These readings rest on the computed numbers. Each one says which number it rests on. They describe what the model measures, not claims about players beyond the data.\n")
bz, bhh = bh.loc[("batter_all", "zero")], bh.loc[("batter_all", "high")]
pz, ph_ = bh.loc[("bowler_pace", "zero")], bh.loc[("bowler_pace", "high")]
sz, shh = bh.loc[("bowler_spin", "zero")], bh.loc[("bowler_spin", "high")]
c(f"1. **Batting pressure is now mostly the match situation.** The batter high band covers {pct(f['pro_share_of_death_balls_in_batter_high_band_now'])} of death balls, {pct(f['pro_share_of_final_balls_in_batter_high_band_now'])} of final balls and {pct(f['pro_share_of_powerplay_balls_in_batter_high_band_now'])} of powerplay balls. Recent wickets still matter: {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'])} of high-band balls follow one, against {pct(f['se_share_of_balls_within_6_after_a_wicket'])} of all balls. In the high band, strike rate is {bhh['strike_rate']:.1f} against {bz['strike_rate']:.1f} in the zero band, and the striker-out rate {pct(bhh['striker_out_rate'], 2)} against {pct(bz['striker_out_rate'], 2)}.")
c(f"2. **Bowling pressure now leans to the new ball.** {pct(f['pr_phase_Pace_powerplay_share_of_arm_high'])} of pace high-band balls are in the powerplay and {pct(f['pr_phase_Pace_death_share_of_arm_high'])} at the death (M-17). Economy on legal balls from the zero to the high band: pace {pz['economy_legal_balls']:.2f} → {ph_['economy_legal_balls']:.2f}, spin {sz['economy_legal_balls']:.2f} → {shh['economy_legal_balls']:.2f}. A death specialist's high-band sample is now smaller than an opening bowler's.")
c(f"3. **Spin carries the middle overs.** {pct(f['pr_phase_Spin_middle_share_of_arm_high'])} of spin high-band balls are in the middle overs and {pct(f['pr_phase_Spin_powerplay_share_of_arm_high'])} in the powerplay.")
c(f"4. **The batting top 10 by role** is {trio('rolerep_current_role_blend_0_5_official_top10')} (top/middle/lower). Lower-order ranked batters have {pct(f['role_highshare_batter_lower order'])} of their balls in the high band, against {pct(f['role_highshare_batter_top order'])} for top-order batters: death overs and wickets down are now the main route into the band.")
c(f"5. **The role mix is a modelling choice.** Top 20 (top/middle/lower): role-only {trio('rolerep_current_role_blend_1_role_only_top20')}, 50/50 blend {trio('rolerep_current_role_blend_0_5_official_top20')}, pooled {trio('rolerep_current_role_blend_0_pooled_top20')}. Before the fixes the same switch moved it from {trio('rolerep_pre_fix_with_role_split_top20')} to {trio('rolerep_pre_fix_without_role_split_top20')}. {ROLE_WHY}")
c("6. **Batting ranks rest mostly on** " + ", ".join(f"{r['label'].lower()} {pct(r['variance_share_of_composite'])}" for _, r in top_var_b.head(4).iterrows()) + " (variance shares).")
c("7. **Bowling ranks rest mostly on** " + ", ".join(f"{r['label'].lower()} {pct(r['variance_share_of_composite'])}" for _, r in top_var_w.head(4).iterrows()) + f". Baseline-only and full rankings share {int(abl('bowler', 'baseline_only', 'top20_overlap'))} of the top 20.")
c(f"8. **Tail situations no longer distort ball value much.** At 8–9 down, batters average {g('wf_8-9_e_bat')} runs-equivalent per ball (before {g('wf_8-9_e_bat_pre_fix')}), and bowlers facing them {g('wf_8-9_e_bowl')} (before {g('wf_8-9_e_bowl_pre_fix')}).")
c(f"9. **The 2025 final chase.** PBKS's {len(f['shock_actual_wicket_legal_n'])} wickets fell at legal balls {', '.join(map(str, f['shock_actual_wicket_legal_n']))}. Batter pressure peaks at {g('shock_peak_pressure_bat', 2)} on ball {f['shock_peak_pressure_bat_n']}. {f['shock_high_band_balls_bat']} of the 120 balls are batter-high (a final at occasion 3.0).")
(OUT / "09_limitations/cricketing_interpretations.md").write_text("\n".join(ci), encoding="utf-8")
reg.note("09_limitations/cricketing_interpretations.md", "facts a-d", "generated text")

# ---------------------------------------------------------------- sanity interpretations
S = ["# Sanity-check interpretations\n",
     f"Every number comes from `sanity_check_players.csv`. Ranks are out of the ranked pool: {f['ranked_batters']} batters, {f['ranked_bowlers']} bowlers (before the fixes {f['pre_fix_ranked_batters']} and {f['pre_fix_ranked_bowlers']}). 'Before' means the pre-fix model. Interpretations are marked as such.\n"]


def line(name, skill):
    r = sanity(name, skill)
    if r is None:
        return f"- **{name} ({skill})**: not in the data."
    comps = ", ".join(f"{LABEL[cc].lower()} {r[cc]:+.2f}" for cc in COMPONENTS)
    before = f"before the fixes rank {int(r['pre_fix_rank'])}/{int(r['pre_fix_ranked_pool'])}" if pd.notna(r["pre_fix_rank"]) else "not ranked before the fixes"
    if not r["ranked"]:
        return f"- **{name} ({skill}, {r['role']})**: not ranked ({r['reason_not_ranked']}); {before}. Composite {r['composite']:.3f} on {int(r['legal_balls'])} legal balls. Components: {comps}."
    best = max(COMPONENTS, key=lambda cc: r[cc] * WEIGHTS[cc])
    worst = min(COMPONENTS, key=lambda cc: r[cc] * WEIGHTS[cc])
    extra = f"strike rate {r['strike_rate_level_weighted']:.1f}, average {r['average_level_weighted']:.1f}" if skill == "batter" else f"economy {r['economy_level_weighted']:.2f}, balls per wicket {r['balls_per_wicket_level_weighted']:.1f}"
    return (f"- **{name} ({skill}, {r['role']})**: rank **{int(r['rank'])}** (composite {r['composite']:.3f}); {before}; baseline-only rank {int(r['baseline_only_rank'])}"
            + (f", role-only z rank {int(r['role_only_z_rank'])}, pooled-z rank {int(r['pooled_z_rank'])}" if pd.notna(r.get("pooled_z_rank")) else "")
            + f". {int(r['legal_balls'])} legal balls (n_eff {r['n_eff']:.0f}, high n_eff {r['high_n_eff']:.0f}); {extra}. Components: {comps}. Largest lift: {LABEL[best].lower()}; largest drag: {LABEL[worst].lower()}.")


def moved(name, skill):
    r = sanity(name, skill)
    if r is None:
        return ""
    prev = (pbat if skill == "batter" else pbowl).set_index("player_id").loc[r["player_id"]]
    delta = sorted(COMPONENTS, key=lambda cc: -abs(WEIGHTS[cc] * (r[cc] - prev[cc])))[:2]
    parts = ", ".join(f"{LABEL[cc].lower()} {prev[cc]:+.2f} → {r[cc]:+.2f}" for cc in delta)
    now = f"rank {int(r['rank'])}" if r["ranked"] else f"not ranked ({r['reason_not_ranked']})"
    then = f"rank {int(prev['rank'])}" if pd.notna(prev["rank"]) else "not ranked"
    return f"- **{name} ({skill})**: {then} → {now}; composite {prev['composite']:.3f} → {r['composite']:.3f}. Largest component moves: {parts}."


for name, skill in [("Jos Buttler", "batter"), ("Virat Kohli", "batter"), ("David Miller", "batter"), ("Rilee Rossouw", "batter"),
                    ("Mahendra Singh Dhoni", "batter"), ("Tim David", "batter"), ("Vaibhav Sooryavanshi", "batter"), ("Rahmanullah Gurbaz", "batter"),
                    ("Rashid Khan", "batter"), ("Corbin Bosch", "batter"), ("Imad Wasim", "batter"),
                    ("Jasprit Bumrah", "bowler"), ("Rashid Khan", "bowler"), ("Matthew Humphreys", "bowler"), ("Corbin Bosch", "bowler"), ("Imad Wasim", "bowler")]:
    S.append(line(name, skill))
S.append("\n## What the fixes changed for these players (computed)\n")
for name, skill in [("Rilee Rossouw", "batter"), ("Tim David", "batter"), ("Mahendra Singh Dhoni", "batter"), ("Jos Buttler", "batter"), ("Virat Kohli", "batter"),
                    ("Vaibhav Sooryavanshi", "batter"), ("Rahmanullah Gurbaz", "batter"), ("Corbin Bosch", "bowler"), ("Matthew Humphreys", "bowler"),
                    ("Jasprit Bumrah", "bowler"), ("Rashid Khan", "bowler"), ("Imad Wasim", "bowler")]:
    S.append(moved(name, skill))
S.append("\n## Interpretation (analyst reading of the numbers above)\n")


def rk(value):
    return str(int(value)) if pd.notna(value) else "unranked"


def ranks(value):
    return f"ranks {int(value)}" if pd.notna(value) else "is not ranked"


hu, bo, bu = sanity("Matthew Humphreys", "bowler"), sanity("Corbin Bosch", "bowler"), sanity("Jasprit Bumrah", "bowler")
S.append(f"- **The small-sample bowlers who led the old table.** Humphreys (before {rk(hu['pre_fix_rank'])}) has a high-band n_eff of {hu['high_n_eff']:.1f}"
         + (f" and is not ranked ({hu['reason_not_ranked']})" if not hu["ranked"] else f" and ranks {rk(hu['rank'])}")
         + f"; Bosch (before {rk(bo['pre_fix_rank'])}, high n_eff {bo['high_n_eff']:.1f}) {ranks(bo['rank'])}. Bumrah, on {int(bu['legal_balls'])} legal balls, {ranks(bu['rank'])} (before {rk(bu['pre_fix_rank'])}). The floor of {FLOOR} high-band balls and the new pressure index both work against thin pressure samples.")
so = sanity("Vaibhav Sooryavanshi", "batter")
S.append(f"- **Sooryavanshi** has a high-band n_eff of {so['high_n_eff']:.1f}, " + (f"below the new floor of {FLOOR}, so he is not ranked" if not so["ranked"] else f"and ranks {rk(so['rank'])}") + f" (baseline z {so['baseline']:+.2f}; before the fixes {rk(so['pre_fix_rank'])}).")
kb, bb, ro = sanity("Virat Kohli", "batter"), sanity("Jos Buttler", "batter"), sanity("Rilee Rossouw", "batter")
S.append(f"- **Established top-order batters**: Buttler {rk(bb['rank'])}, Kohli {rk(kb['rank'])} (before {rk(bb['pre_fix_rank'])} and {rk(kb['pre_fix_rank'])}). Rossouw was {rk(ro['pre_fix_rank'])} before the fixes on a high-band n_eff of {ro['pre_fix_high_n_eff']:.1f}; under the new pressure index he has {ro['high_n_eff']:.1f} and {ranks(ro['rank'])}. The pooled half of the z-score and a situation-led high band weigh sustained output more than a short run of post-wicket innings.")
rk_w = sanity("Rashid Khan", "bowler")
S.append(f"- **Rashid Khan (bowler)** ranks {rk(rk_w['rank'])} (before {rk(rk_w['pre_fix_rank'])}); clutch {rk_w['clutch']:+.2f}, high band {rk_w['band_high']:+.2f}. Read his high-band terms with M-17 in mind: the high band now leans to the powerplay, where he rarely bowls.")
(OUT / "08_validation/sanity_check_interpretations.md").write_text("\n".join(S), encoding="utf-8")
reg.note("08_validation/sanity_check_interpretations.md", "08_validation/sanity_check_players.csv; pre-fix model", "generated text")

# ---------------------------------------------------------------- model fixes: before and after
FX = []


def fx(fid, finding, metric, before, after, source):
    FX.append({"finding": fid, "description": finding, "metric": metric, "before_fix": before, "after_fix": after, "source": source})


fx("BUG-01", "ball-19 look-ahead in the run-of-play window", "mean bowler run of play on legal ball 19", f["bug_rop_delta_bowl_mean_at_19_pre_fix"], f["bug_rop_delta_bowl_mean_at_19"], "02_pressure facts")
fx("BUG-01", "", "mean batter run of play on legal ball 19", f["bug_rop_delta_bat_mean_at_19_pre_fix"], f["bug_rop_delta_bat_mean_at_19"], "02_pressure facts")
fx("BUG-01", "", "run-of-play runs scale (SD)", f["bug_rop_scale_runs_pre_fix"], f["scale_run_of_play_runs"], "06_shock/shock_parameters.csv")
fx("BUG-01", "", "run-of-play wickets scale (SD)", f["bug_rop_scale_wicket_pre_fix"], f["scale_run_of_play_wicket"], "06_shock/shock_parameters.csv")
fx("BUG-01", "", "ball-19 share in the bowler high band", f["bug_rop_ball19_bowler_high_share_pre_fix"], f["pro_share_of_ball_19_in_bowler_high_band"], "02_pressure/pressure_observations.csv")
fx("M-01", "pressure dominated by recent events", "batter high-band balls within 6 after a wicket", f["se_pre_fix_bat_high_after_wicket"], f["se_share_of_batter_high_band_balls_within_6_after_wicket"], "06_shock/shock_event_summary.csv")
fx("M-01", "", "  base rate: all balls within 6 after a wicket", f["se_share_of_balls_within_6_after_a_wicket"], f["se_share_of_balls_within_6_after_a_wicket"], "06_shock/shock_event_summary.csv")
fx("M-01", "", "bowler high-band balls after a four/six in the last 6", f["se_pre_fix_bowl_high_after_boundary"], f["se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6"], "06_shock/shock_event_summary.csv")
fx("M-01", "", "  base rate: all balls after a four/six in the last 6", f["se_share_of_all_balls_with_four_or_six_in_last_6"], f["se_share_of_all_balls_with_four_or_six_in_last_6"], "06_shock/shock_event_summary.csv")
fx("M-01", "", "situation share of batter pressure variance", f["pr_var_share_situation_bat_pre_fix"], f["pr_var_share_situation_bat"], "02_pressure/pressure_summary.csv")
fx("M-01", "", "situation share of bowler pressure variance", f["pr_var_share_situation_bowl_pre_fix"], f["pr_var_share_situation_bowl"], "02_pressure/pressure_summary.csv")
fx("M-01", "", "final balls in the batter high band", f["pro_share_of_final_balls_in_batter_high_band_pre_fix"], f["pro_share_of_final_balls_in_batter_high_band_now"], "02_pressure/pressure_observations.csv")
fx("M-01", "", "death balls in the batter high band", f["pro_share_of_death_balls_in_batter_high_band_pre_fix"], f["pro_share_of_death_balls_in_batter_high_band_now"], "02_pressure/pressure_observations.csv")
fx("M-01", "", "super-over balls in the batter high band", f["pro_share_of_super_over_balls_in_batter_high_band_pre_fix"], f["pro_share_of_super_over_balls_in_batter_high_band_now"], "02_pressure/pressure_observations.csv")
fx("M-17", "side effect: bowler high band by phase", "pace high-band balls in the powerplay", f["pr_phase_Pace_powerplay_share_of_arm_high_pre_fix"], f["pr_phase_Pace_powerplay_share_of_arm_high"], "02_pressure/phase_bowling_pressure.csv")
fx("M-17", "", "pace high-band balls at the death", f["pr_phase_Pace_death_share_of_arm_high_pre_fix"], f["pr_phase_Pace_death_share_of_arm_high"], "02_pressure/phase_bowling_pressure.csv")
fx("M-07", "weak expectation discrimination", "xR MAE (constant predictor 1.3282)", f["xm_xR_bat_runs_pre_fix_mae"], f["xm_xR_bat_runs_mae"], "05_expectation_models/expectation_model_metrics.csv")
fx("M-07", "", "xR R-squared", f["xm_xR_bat_runs_pre_fix_r_squared"], f["xm_xR_bat_runs_r_squared"], "05_expectation_models/expectation_model_metrics.csv")
fx("M-07", "", "xW AUC (bowler wicket)", f["xm_xW_bowler_wicket_pre_fix_auc"], f["xm_xW_bowler_wicket_auc"], "05_expectation_models/expectation_model_metrics.csv")
for b in ["0-1", "2-3", "4-5", "6-7", "8-9"]:
    fx("KI-03", "wickets-fallen bias" if b == "0-1" else "", f"bat runs minus xR per ball, {b} down", f[f"wf_{b}_runs_resid_pre_fix"], f[f"wf_{b}_runs_resid"], "05_expectation_models/residual_by_wickets_fallen.csv")
fx("KI-03", "", "bowler ball value per ball, 8-9 down", f["wf_8-9_e_bowl_pre_fix"], f["wf_8-9_e_bowl"], "05_expectation_models/residual_by_wickets_fallen.csv")
fx("M-06", "small high-pressure samples at the top", "top-10 bowlers with high n_eff < 60", f["pre_fix_top10_bowler_high_lt60"], f["top10_bowler_high_lt60"], "07_rankings/final_bowler_rankings.csv")
fx("M-06", "", "top-10 batters with high n_eff < 60", f["pre_fix_top10_batter_high_lt60"], f["top10_batter_high_lt60"], "07_rankings/final_batter_rankings.csv")
fx("M-06", "", "high-band n_eff floor", 30, FLOOR, "player_ratings.RANK_HIGH_BALLS")
fx("M-06", "", "ranked bowlers", f["pre_fix_ranked_bowlers"], f["ranked_bowlers"], "07_rankings")
fx("M-06", "", "ranked batters", f["pre_fix_ranked_batters"], f["ranked_batters"], "07_rankings")
fx("BUG-03", "bowler clutch delivery basis", "current high-band spells beating own rate (old basis -> legal basis)", f["clutch_bowl_share_spells_beating_own_rate_old_basis_same_spells"], f["clutch_bowl_share_spells_beating_own_rate_now"], "08_validation/diagnostic_bowler_clutch_basis.csv")
fx("BUG-03", "", "mean own gap on current spells, scale units (old basis -> legal basis)", f["clutch_bowl_mean_own_gap_old_basis_same_spells"], f["clutch_bowl_mean_own_gap_now"], "08_validation/diagnostic_bowler_clutch_basis.csv")
for k, lab in [("top20", "top 20"), ("top10", "top 10")]:
    fx("M-18", "role normalisation (top/middle/lower)" if k == "top20" else "", f"batting {lab}, role-only z (before -> now)", trio(f"rolerep_pre_fix_with_role_split_{k}"), trio(f"rolerep_current_role_blend_1_role_only_{k}"), "08_validation/role_ranking_representation.csv")
    fx("M-18", "", f"batting {lab}, pooled z (before -> now)", trio(f"rolerep_pre_fix_without_role_split_{k}"), trio(f"rolerep_current_role_blend_0_pooled_{k}"), "08_validation/role_ranking_representation.csv")
    fx("M-18", "", f"batting {lab}, official (role-only before -> 50/50 blend now)", trio(f"rolerep_pre_fix_with_role_split_{k}"), trio(f"rolerep_current_role_blend_0_5_official_{k}"), "08_validation/role_ranking_representation.csv")
fx("ALL", "whole-model change", "batters: Spearman vs pre-fix ranking", 1.0, abl("batter", "previous_model_before_fixes", "spearman_vs_full"), "08_validation/ablation_summary.csv")
fx("ALL", "", "batters: top-20 overlap with pre-fix ranking", 20, abl("batter", "previous_model_before_fixes", "top20_overlap"), "08_validation/ablation_summary.csv")
fx("ALL", "", "bowlers: Spearman vs pre-fix ranking", 1.0, abl("bowler", "previous_model_before_fixes", "spearman_vs_full"), "08_validation/ablation_summary.csv")
fx("ALL", "", "bowlers: top-20 overlap with pre-fix ranking", 20, abl("bowler", "previous_model_before_fixes", "top20_overlap"), "08_validation/ablation_summary.csv")
fix_tab = pd.DataFrame(FX)
fix_tab["status"] = "COMPUTED"
reg.save(fix_tab, "12_model_fixes/fix_before_after.csv", "pre-fix model (reference/player_ratings_pre_fix.py) vs current player_ratings.py; facts from scripts a-c",
         "one row per metric; before = pre-fix model on the same balls")

MF = ["# Model fixes (November 2026)\n",
      "What was changed, why, and what moved. Before = the pre-fix model (`_scripts/reference/player_ratings_pre_fix.py`), run in full on the same balls. Numbers: `fix_before_after.csv`.\n",
      "## Changes\n",
      "| finding | change | constant |", "|---|---|---|",
      "| BUG-01 ball-19 look-ahead | the 18-ball window subtracts 0 before the innings has 18 balls | – |",
      f"| Pressure dominated by recent events | each term over its own SD, then weighted {PW['situation']:.2f} / {PW['shock']:.2f} / {PW['run_of_play']:.2f} | `PRESSURE_WEIGHTS` |",
      "| Wickets-fallen bias | full expectation cell = ladder x phase x arm x wickets down (0-1, 2-3, 4-5, 6-7, 8+) | – |",
      f"| Small high-pressure samples | high-band n_eff floor 30 → {FLOOR} | `RANK_HIGH_BALLS` |",
      "| Bowler clutch delivery basis | career economy on legal balls, same as the spell | – |",
      f"| Role normalisation | batter z = {pr.ROLE_BLEND} within role + {1 - pr.ROLE_BLEND} pooled | `ROLE_BLEND` |",
      "\n## What moved\n",
      f"- **Rankings.** Against the pre-fix model: batters Spearman {r3(abl('batter', 'previous_model_before_fixes', 'spearman_vs_full'))}, top-20 overlap {int(abl('batter', 'previous_model_before_fixes', 'top20_overlap'))}/20; bowlers {r3(abl('bowler', 'previous_model_before_fixes', 'spearman_vs_full'))}, {int(abl('bowler', 'previous_model_before_fixes', 'top20_overlap'))}/20. The pressure weighting alone is a change of that size: keeping every other fix but going back to raw-sum pressure (bug fixed) gives Spearman {r3(abl('batter', 'pressure_raw_sum_bug_fixed', 'spearman_vs_full'))} for batters and {r3(abl('bowler', 'pressure_raw_sum_bug_fixed', 'spearman_vs_full'))} for bowlers against the official ranking.",
      f"- **Pressure.** Batter high-band balls after a recent wicket {pct(f['se_pre_fix_bat_high_after_wicket'])} → {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'])} (base rate {pct(f['se_share_of_balls_within_6_after_a_wicket'])}); bowler high-band balls after a boundary {pct(f['se_pre_fix_bowl_high_after_boundary'])} → {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'])} (base rate {pct(f['se_share_of_all_balls_with_four_or_six_in_last_6'])}). Finals in the batter high band {pct(f['pro_share_of_final_balls_in_batter_high_band_pre_fix'])} → {pct(f['pro_share_of_final_balls_in_batter_high_band_now'])}.",
      f"- **Side effect (M-17).** Pace high-band balls in the powerplay {pct(f['pr_phase_Pace_powerplay_share_of_arm_high_pre_fix'])} → {pct(f['pr_phase_Pace_powerplay_share_of_arm_high'])}, at the death {pct(f['pr_phase_Pace_death_share_of_arm_high_pre_fix'])} → {pct(f['pr_phase_Pace_death_share_of_arm_high'])}. This follows from the existing bowler ball-difficulty table and is not tuned here.",
      f"- **Expectations.** The 8-9 down residual {g('wf_8-9_runs_resid_pre_fix')} → {g('wf_8-9_runs_resid')} runs per ball. Discrimination barely moves: xR MAE {g('xm_xR_bat_runs_pre_fix_mae', 4)} → {g('xm_xR_bat_runs_mae', 4)} (constant {g('xm_xR_bat_runs_mae_constant_in_sample_mean', 4)}), R² {g('xm_xR_bat_runs_pre_fix_r_squared', 4)} → {g('xm_xR_bat_runs_r_squared', 4)}, xW AUC {g('xm_xW_bowler_wicket_pre_fix_auc', 4)} → {g('xm_xW_bowler_wicket_auc', 4)}. Single-ball T20 outcomes are mostly noise; this limitation stays open (M-07).",
      f"- **Samples.** Top-10 bowlers with high n_eff < 60: {f['pre_fix_top10_bowler_high_lt60']} → {f['top10_bowler_high_lt60']}. Ranked pools: batters {f['pre_fix_ranked_batters']} → {f['ranked_batters']}, bowlers {f['pre_fix_ranked_bowlers']} → {f['ranked_bowlers']}.",
      f"- **Clutch.** On the current high-band spells, {pct(f['clutch_bowl_share_spells_beating_own_rate_old_basis_same_spells'])} would beat their own rate on the old mixed basis; {pct(f['clutch_bowl_share_spells_beating_own_rate_now'])} do on the legal-ball basis.",
      f"- **Roles.** Top-20 batting mix (top/middle/lower): role-only {trio('rolerep_current_role_blend_1_role_only_top20')}, official blend {trio('rolerep_current_role_blend_0_5_official_top20')}, pooled {trio('rolerep_current_role_blend_0_pooled_top20')}; before the fixes role-only {trio('rolerep_pre_fix_with_role_split_top20')} and pooled {trio('rolerep_pre_fix_without_role_split_top20')}.",
      "\n## Why batters are normalised within roles (partly)\n", ROLE_WHY,
      f"\nThe evidence that this is a choice and not a discovery: the official ranking agrees with the role-only ranking at Spearman {r3(abl('batter', 'role_blend_1_role_only_z', 'spearman_vs_full'))} and with the pooled ranking at {r3(abl('batter', 'role_blend_0_pooled_z', 'spearman_vs_full'))}, but the top-20 role mix changes visibly between them. After the wickets-down fix the role-only and pooled tables are much closer than before, which suggests part of what role normalisation was compensating for was the tail-end expectation bias.",
      "\n## Pressure weights\n",
      "The weights are a judgement, chosen from the table in `08_validation/pressure_weight_sensitivity.csv`. Lower situation weights keep the high band tied to recent events; higher ones push death bowling further out of the bowler high band. Chart: `10_charts/slide_04_high_pressure_meaning/pressure_weight_sensitivity.png`."]
(OUT / "12_model_fixes/model_fixes.md").write_text("\n".join(MF), encoding="utf-8")
reg.note("12_model_fixes/model_fixes.md", "12_model_fixes/fix_before_after.csv and facts", "generated text")

# ---------------------------------------------------------------- key findings
K = ["# Key findings\n", "Ordered by importance for the presentation. Every number links to a file in this pack.\n"]
K.append(f"1. **Six fixes went in, and the tables moved a lot.** Against the pre-fix model: batters Spearman {r3(abl('batter', 'previous_model_before_fixes', 'spearman_vs_full'))}, top-20 overlap {int(abl('batter', 'previous_model_before_fixes', 'top20_overlap'))}/20; bowlers {r3(abl('bowler', 'previous_model_before_fixes', 'spearman_vs_full'))}, {int(abl('bowler', 'previous_model_before_fixes', 'top20_overlap'))}/20. *(12_model_fixes)*")
K.append(f"2. **The top of each table.** Batters: {', '.join(f'{int(x[0])}. {x[1]}' for x in f['top10_batters'][:5])}. Bowlers: {', '.join(f'{int(x[0])}. {x[1]}' for x in f['top10_bowlers'][:5])}. *(07_rankings)*")
K.append(f"3. **'High pressure' now mostly means the match situation.** Situation explains {pct(f['pr_var_share_situation_bat'])} of batter pressure variance (before {pct(f['pr_var_share_situation_bat_pre_fix'])}). Recent wickets still lift the band: {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'])} of batter high-band balls follow one (before {pct(f['se_pre_fix_bat_high_after_wicket'])}; base rate {pct(f['se_share_of_balls_within_6_after_a_wicket'])}). Finals are {pct(f['pro_share_of_final_balls_in_batter_high_band_now'])} high (before {pct(f['pro_share_of_final_balls_in_batter_high_band_pre_fix'])}). *(02_pressure, 06_shock)*")
K.append(f"4. **New side effect: the bowler high band leans to the powerplay.** {pct(f['pr_phase_Pace_powerplay_share_of_arm_high'])} of pace high-band balls are in the powerplay and {pct(f['pr_phase_Pace_death_share_of_arm_high'])} at the death (before {pct(f['pr_phase_Pace_powerplay_share_of_arm_high_pre_fix'])} and {pct(f['pr_phase_Pace_death_share_of_arm_high_pre_fix'])}). It comes from the bowler ball-difficulty table, which lowers death difficulty when wickets are down. *(M-17)*")
K.append(f"5. **BUG-01 is fixed.** Ball 19 run of play: bowlers {g('bug_rop_delta_bowl_mean_at_19_pre_fix')} → {g('bug_rop_delta_bowl_mean_at_19')}; the runs scale {g('bug_rop_scale_runs_pre_fix', 4)} → {g('scale_run_of_play_runs', 4)}. *(09_limitations BUG-01)*")
K.append(f"6. **The wickets-down cell removes most of the tail bias.** Runs above expectation at 8–9 down {g('wf_8-9_runs_resid_pre_fix')} → {g('wf_8-9_runs_resid')} per ball. Discrimination barely improves: xR R² {g('xm_xR_bat_runs_pre_fix_r_squared', 4)} → {g('xm_xR_bat_runs_r_squared', 4)}, MAE {g('xm_xR_bat_runs_mae', 4)} vs {g('xm_xR_bat_runs_mae_constant_in_sample_mean', 4)} constant, xW AUC {g('xm_xW_bowler_wicket_auc', 4)}. *(05_expectation_models)*")
K.append(f"7. **No thin pressure samples at the top.** The high-band floor is {FLOOR}. Top-10 bowlers below 60: {f['pre_fix_top10_bowler_high_lt60']} → {f['top10_bowler_high_lt60']}; the smallest top-10 bowler sample is {g('top10_bowler_min_high_n_eff', 1)}. Ranked pools shrink: {f['ranked_batters']} batters, {f['ranked_bowlers']} bowlers. *(08_validation/ranking_floor_sensitivity.csv)*")
K.append(f"8. **Role normalisation is a stated choice.** Top-20 batting mix: role-only {trio('rolerep_current_role_blend_1_role_only_top20')}, official 50/50 blend {trio('rolerep_current_role_blend_0_5_official_top20')}, pooled {trio('rolerep_current_role_blend_0_pooled_top20')} (before the fixes: {trio('rolerep_pre_fix_with_role_split_top20')} vs {trio('rolerep_pre_fix_without_role_split_top20')}). *(M-18, 08_validation/role_ranking_representation.csv)*")
K.append(f"9. **Clutch now compares like with like.** On the current spells, {pct(f['clutch_bowl_share_spells_beating_own_rate_old_basis_same_spells'])} would beat the bowler's own rate on the old basis, {pct(f['clutch_bowl_share_spells_beating_own_rate_now'])} on legal balls. *(BUG-03)*")
K.append(f"10. **The pressure layer still changes the ranking a lot.** Baseline-only vs full: {int(abl('batter', 'baseline_only', 'top20_overlap'))}/20 batters, {int(abl('bowler', 'baseline_only', 'top20_overlap'))}/20 bowlers in common. Other pressure weights: batters Spearman {min(abl('batter', v, 'spearman_vs_full') for v in ['pressure_weights_40_35_25', 'pressure_weights_50_30_20', 'pressure_weights_70_20_10']):.3f}–{max(abl('batter', v, 'spearman_vs_full') for v in ['pressure_weights_40_35_25', 'pressure_weights_50_30_20', 'pressure_weights_70_20_10']):.3f}, bowlers {min(abl('bowler', v, 'spearman_vs_full') for v in ['pressure_weights_40_35_25', 'pressure_weights_50_30_20', 'pressure_weights_70_20_10']):.3f}–{max(abl('bowler', v, 'spearman_vs_full') for v in ['pressure_weights_40_35_25', 'pressure_weights_50_30_20', 'pressure_weights_70_20_10']):.3f}. *(08_validation/ablation_summary.csv, pressure_weight_sensitivity.csv)*")
K.append(f"11. **Super overs now reach the high band** ({pct(f['pro_super_over_share_in_batter_high_band'])} batter, {pct(f['pro_super_over_share_in_bowler_high_band'])} bowler; none before) and still barely move the tables (Spearman {abl('batter', 'exclude_super_overs', 'spearman_vs_full'):.4f} / {abl('bowler', 'exclude_super_overs', 'spearman_vs_full'):.4f} vs excluding them). *(02_pressure/super_over_pressure.csv)*")
K.append(f"12. **Form removal, isolated on the pre-fix frame, mattered little**: Spearman {g('form_isolation_batter_spearman')} (batters), {g('form_isolation_bowler_spearman')} (bowlers). Elo stays inside its bounds, steps not halved. *(08_validation, 04_elo)*")
(OUT / "11_presentation_summary").mkdir(exist_ok=True)
(OUT / "11_presentation_summary/key_findings.md").write_text("\n".join(K), encoding="utf-8")
reg.note("11_presentation_summary/key_findings.md", "facts a-d", "generated text")

# ---------------------------------------------------------------- slide by slide
INT_COLS = {"rank", "pre_fix_rank", "legacy_rank", "legacy_rank_8term", "baseline_only_rank", "balls", "legal_balls", "players", "ranked", "top10_overlap", "top20_overlap"}


def tbl(frame, cols, names=None):
    names = names or cols
    out = ["| " + " | ".join(names) + " |", "|" + "---|" * len(cols)]
    for _, r in frame.iterrows():
        cells = []
        for col in cols:
            v = r[col]
            if isinstance(v, float) and pd.isna(v):
                cells.append("–")
            elif isinstance(v, float) and (col in INT_COLS or v.is_integer() and abs(v) >= 10):
                cells.append(f"{v:,.0f}")
            elif isinstance(v, float):
                cells.append(f"{v:.3f}" if abs(v) < 10 else f"{v:,.1f}")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


D = ["# Slide-by-slide numbers\n",
     "One section per slide. Status tags: **[C]** COMPUTED here, **[E]** EXISTING in the repository and reproduced, **[RD]** REQUIRES_DATA, **[RI]** REQUIRES_IMPLEMENTATION, **[NA]** NOT_APPLICABLE. The model is the current **7-term** version after the November fixes; 'before' means the pre-fix model (`12_model_fixes/`).\n"]
D.append("## Slide 1: Objective and scope\n")
D.append(f"- Rank T20 batters and bowlers on how they perform under pressure, using {num(f['ds_legal_balls_used_in_ratings'])} legal balls from {f['ds_first_match_date']} to {f['ds_last_match_date']}. [C]")
D.append(f"- {f['ranked_batters']} batters and {f['ranked_bowlers']} bowlers meet the ranking floor (n_eff ≥ {BALLS} and high-band n_eff ≥ {FLOOR}). Before the fixes: {f['pre_fix_ranked_batters']} and {f['pre_fix_ranked_bowlers']} at a floor of 30. [C]")
D.append("- 7 weighted terms; Form removed [NA].\n")
D.append("## Slide 2: Data and cleaning\n")
D.append(f"- Deliveries: {num(f['ds_raw_deliveries_source_file'])}; none deleted. Super overs included: {f['ds_super_over_deliveries_included']} deliveries, {f['ds_super_over_legal_balls_included']} legal balls, {f['ds_super_over_matches']} matches. [C]")
D.append(f"- Excluded from ball value: {num(f['ds_wides'])} wides, {f['ds_noballs']} no-balls, {f['ds_other_extras']} 'other'. Legal balls used: **{num(f['ds_legal_balls_used_in_ratings'])}** in {f['ds_matches_with_legal_balls']} matches. [C]")
D.append("- Sources: `01_dataset/*.csv`. Charts: `10_charts/slide_02_dataset/`.\n")
D.append("## Slide 3: The pressure index\n")
D.append(f"- pressure = {W_TXT}, each term over its own SD; situation = occasion × competition × ball difficulty (`02_pressure/pressure_formula_as_executed.csv`). Before the fix the three terms were added raw. [E]")
D.append(f"- Band cut-offs (p50 / p80): batters {g('pr_batter_p50')} / {g('pr_batter_p80')}; pace {g('pr_bowler_pace_p50')} / {g('pr_bowler_pace_p80')}; spin {g('pr_bowler_spin_p50')} / {g('pr_bowler_spin_p80')}. [C]")
D.append(f"- Variance of batter pressure: situation {pct(f['pr_var_share_situation_bat'])}, shock {pct(f['pr_var_share_shock_bat'])}, run of play {pct(f['pr_var_share_run_of_play_bat'])} (before {pct(f['pr_var_share_situation_bat_pre_fix'])} / {pct(f['pr_var_share_shock_bat_pre_fix'])} / {pct(f['pr_var_share_run_of_play_bat_pre_fix'])}). [C]")
D.append("- Phase × arm (bowler high-band share):")
D.append(tbl(phase.assign(share_high=lambda d: (d["share_bowler_high"] * 100).map("{:.1f}%".format), share_of_arm_high=lambda d: (d["share_of_arm_high_band"] * 100).map("{:.1f}%".format)),
             ["arm", "phase", "legal_balls", "mean_pressure_bowl", "share_high", "share_of_arm_high", "economy_legal_balls"],
             ["arm", "phase", "legal balls", "mean bowler pressure", "% balls high", "% of arm's high balls", "economy (legal)"]))
D.append(f"- Pace high-band balls by phase before the fix: powerplay {pct(f['pr_phase_Pace_powerplay_share_of_arm_high_pre_fix'])}, middle {pct(f['pr_phase_Pace_middle_share_of_arm_high_pre_fix'])}, death {pct(f['pr_phase_Pace_death_share_of_arm_high_pre_fix'])} (M-17). [C]")
D.append("- Sources: `02_pressure/`. Charts: `10_charts/slide_03_pressure/`.\n")
D.append("## Slide 4: What 'high pressure' captures\n")
D.append(f"- Batter high-band balls within 6 after a wicket: {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'])} (before {pct(f['se_pre_fix_bat_high_after_wicket'])}; base rate {pct(f['se_share_of_balls_within_6_after_a_wicket'])}). [C]")
D.append(f"- Bowler high-band balls after a four or six in the previous 6: {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'])} (before {pct(f['se_pre_fix_bowl_high_after_boundary'])}; base rate {pct(f['se_share_of_all_balls_with_four_or_six_in_last_6'])}). [C]")
D.append(f"- Batter high band by context, now (before): finals {pct(f['pro_share_of_final_balls_in_batter_high_band_now'])} ({pct(f['pro_share_of_final_balls_in_batter_high_band_pre_fix'])}), league {pct(f['pro_share_of_league_balls_in_batter_high_band_now'])} ({pct(f['pro_share_of_league_balls_in_batter_high_band_pre_fix'])}), death {pct(f['pro_share_of_death_balls_in_batter_high_band_now'])} ({pct(f['pro_share_of_death_balls_in_batter_high_band_pre_fix'])}), powerplay {pct(f['pro_share_of_powerplay_balls_in_batter_high_band_now'])} ({pct(f['pro_share_of_powerplay_balls_in_batter_high_band_pre_fix'])}), super overs {pct(f['pro_share_of_super_over_balls_in_batter_high_band_now'])} ({pct(f['pro_share_of_super_over_balls_in_batter_high_band_pre_fix'])}). [C]")
D.append(f"- Strike rate by batter band (zero / medium / high): {f['pr_sr_batter_all_zero']:.1f} / {f['pr_sr_batter_all_medium']:.1f} / {f['pr_sr_batter_all_high']:.1f}. Pace economy: {f['pr_econ_bowler_pace_zero']:.2f} / {f['pr_econ_bowler_pace_medium']:.2f} / {f['pr_econ_bowler_pace_high']:.2f}. Spin: {f['pr_econ_bowler_spin_zero']:.2f} / {f['pr_econ_bowler_spin_medium']:.2f} / {f['pr_econ_bowler_spin_high']:.2f}. [C]")
D.append("- Pressure-weight sensitivity:")
D.append(tbl(pws.assign(**{c: pws[c] * 100 for c in ["batter_high_band_balls_within_6_after_wicket", "bowler_high_band_balls_after_four_or_six_in_last_6", "batter_high_share_of_final_balls", "pace_high_band_share_in_death"]}),
             ["variant", "batter_high_band_balls_within_6_after_wicket", "bowler_high_band_balls_after_four_or_six_in_last_6", "batter_high_share_of_final_balls", "pace_high_band_share_in_death", "batter_spearman_vs_official", "bowler_spearman_vs_official"],
             ["variant", "% batter high after wicket", "% bowler high after boundary", "% final balls high", "% pace high at death", "Spearman bat", "Spearman bowl"]))
D.append("- Charts: `10_charts/slide_04_high_pressure_meaning/`.\n")
D.append("## Slide 5: Expected runs and wickets (ball value)\n")
D.append("- Ball value: batter = (runs − xR) − 4 × (out − xW); bowler = (xR − charged) + 4 × (wicket − xW). Cells now include wickets down. Predictions use only earlier balls. [E]")
mm = met.loc[met["scope"].isin(["all", "all_pre_fix_model"])]
D.append(tbl(mm.loc[mm["model"].isin(["xR", "xW"])], ["scope", "model", "target", "mean_predicted", "mean_actual", "mae", "mae_constant_in_sample_mean", "r_squared", "calibration_slope_ols", "calibration_slope_logistic", "auc", "brier"],
             ["scope", "model", "target", "mean pred", "mean actual", "MAE", "MAE constant", "R²", "OLS slope", "logit slope", "AUC", "Brier"]))
D.append(f"- Runs minus xR per ball by wickets down, before → now: 0–1 {g('wf_0-1_runs_resid_pre_fix')} → {g('wf_0-1_runs_resid')}, 8–9 {g('wf_8-9_runs_resid_pre_fix')} → {g('wf_8-9_runs_resid')}. [C]")
D.append("- Charts: `10_charts/slide_05_expectation_models/`.\n")
D.append("## Slide 6: Elo\n")
D.append(f"- Steps 4 / 16 / 20, not halved. Final raw range: batters {g('elo_batter_elo_min', 1)}–{g('elo_batter_elo_max', 1)} (SD {g('elo_batter_elo_sd', 1)}); bowlers {g('elo_bowler_elo_min', 1)}–{g('elo_bowler_elo_max', 1)} (SD {g('elo_bowler_elo_sd', 1)}). [C]")
st = elo_stab.loc[elo_stab["player_name"].isin(["Jos Buttler", "Virat Kohli", "David Miller", "Rilee Rossouw", "Jasprit Bumrah", "Rashid Khan", "Matthew Humphreys", "Corbin Bosch"]) & elo_stab["balls"].ge(30)]
st = st.loc[(st["skill"].eq("batter") & st["player_name"].isin(["Jos Buttler", "Virat Kohli", "David Miller", "Rilee Rossouw"])) | (st["skill"].eq("bowler") & st["player_name"].isin(["Jasprit Bumrah", "Rashid Khan", "Matthew Humphreys", "Corbin Bosch"]))]
D.append(tbl(st, ["player_name", "skill", "ladder", "balls", "final_raw", "min_raw", "max_raw"], ["player", "skill", "ladder", "balls", "final", "min", "max"]))
D.append("- Charts: `10_charts/slide_06_elo/`.\n")
D.append("## Slide 7: Shock timeline, IPL 2025 final (PBKS chase)\n")
D.append(f"- {f['shock_match']}. Target {num(f['shock_target'])}; PBKS made {num(f['shock_innings_total'])}. Wickets at legal balls {', '.join(map(str, f['shock_actual_wicket_legal_n']))} (**verified**). [C]")
D.append(f"- Batter high-band balls: {f['shock_high_band_balls_bat']}/120; bowler {f['shock_high_band_balls_bowl']}/120. Peak batter pressure {g('shock_peak_pressure_bat', 2)} at ball {f['shock_peak_pressure_bat_n']}. Run of play on ball 19: {g('shock_ball19_delta_bat', 2)} (batter), {g('shock_ball19_delta_bowl', 2)} (bowler). [C]")
D.append("- Chart: `10_charts/slide_07_shock/ipl2025_final_shock_timeline.png`.\n")
D.append("## Slide 8: Components and weights\n")
D.append(tbl(infl.loc[infl["skill"].eq("batter")].merge(infl.loc[infl["skill"].eq("bowler"), ["component", "variance_share_of_composite", "effective_share"]], on="component", suffixes=("_bat", "_bowl")),
             ["label", "nominal_weight", "effective_share_bat", "variance_share_of_composite_bat", "effective_share_bowl", "variance_share_of_composite_bowl"],
             ["component", "weight", "effective share (bat)", "variance share (bat)", "effective share (bowl)", "variance share (bowl)"]))
D.append(f"- Batter z-scores: {pr.ROLE_BLEND} within role + {1 - pr.ROLE_BLEND} pooled (M-18). Charts: `10_charts/slide_08_components/`.\n")
D.append("## Slide 9: Top batters\n")
D.append(tbl(fb.head(20), ["rank", "player_name", "role", "composite", "baseline", "band_high", "clutch", "peers", "pre_fix_rank", "n_eff", "high_n_eff"],
             ["rank", "player", "role", "composite", "baseline z", "high z", "clutch z", "peers z", "rank before fixes", "n_eff", "high n_eff"]))
D.append(f"- Gap between rank 10 and 11: {g('dist_batter_gap_10_11', 4)}. [C]  Chart: `10_charts/slide_09_top_batters/`.\n")
D.append("## Slide 10: Top bowlers\n")
D.append(tbl(fw.head(20), ["rank", "player_name", "role", "composite", "baseline", "band_high", "clutch", "peers", "pre_fix_rank", "n_eff", "high_n_eff"],
             ["rank", "player", "arm", "composite", "baseline z", "high z", "clutch z", "peers z", "rank before fixes", "n_eff", "high n_eff"]))
D.append(f"- Top 20 by arm: {f['rolerep_bowler_top20'][0]} pace, {f['rolerep_bowler_top20'][1]} spin. Smallest high n_eff in the top 20: {g('top20_bowler_min_high_n_eff', 1)}. [C]  Chart: `10_charts/slide_10_top_bowlers/`.\n")
D.append("## Slide 11: Sanity checks on named players\n")
D.append(tbl(sp, ["player_name", "skill", "role", "ranked", "rank", "composite", "pre_fix_rank", "baseline_only_rank", "n_eff", "high_n_eff"],
             ["player", "skill", "role", "ranked", "rank", "composite", "rank before fixes", "baseline-only rank", "n_eff", "high n_eff"]))
D.append("- Interpretations: `08_validation/sanity_check_interpretations.md`. Chart: `10_charts/slide_11_sanity_checks/`.\n")
D.append("## Slide 12: Ablation and robustness\n")
D.append(tbl(ab, ["skill", "variant", "spearman_vs_full", "kendall_tau_vs_full", "top10_overlap", "top20_overlap", "mean_abs_rank_change"],
             ["skill", "variant", "Spearman", "Kendall", "top-10 overlap", "top-20 overlap", "mean abs rank change"]))
D.append(f"- Ranking floor (same scores, other floors): " + "; ".join(f"{r['skill']} floor {int(r['high_n_eff_floor'])}: {int(r['ranked'])} ranked, top-20 overlap {int(r['top20_overlap_with_official'])}" for _, r in floor_tab.iterrows()) + ". [C]")
D.append(f"- Baseline-only and full ranks reproduce `exports/23_ablation_ranks.csv`: {f['export23_reproduced']}. [E]  Charts: `10_charts/slide_12_ablation/`.\n")
D.append("## Slide 13: Component correlations and influence\n")
D.append(f"- Batters: most correlated pair {f['corr_batters_max_pair'][0]}–{f['corr_batters_max_pair'][1]} ({f['corr_batters_max_pair'][2]:.3f}); most negative {f['corr_batters_min_pair'][0]}–{f['corr_batters_min_pair'][1]} ({f['corr_batters_min_pair'][2]:.3f}). [C]")
D.append(f"- Bowlers: most correlated {f['corr_bowlers_max_pair'][0]}–{f['corr_bowlers_max_pair'][1]} ({f['corr_bowlers_max_pair'][2]:.3f}); most negative {f['corr_bowlers_min_pair'][0]}–{f['corr_bowlers_min_pair'][1]} ({f['corr_bowlers_min_pair'][2]:.3f}). [C]")
D.append(f"- Largest variance share: batters {top_var_b.iloc[0]['label']} {pct(top_var_b.iloc[0]['variance_share_of_composite'])}; bowlers {top_var_w.iloc[0]['label']} {pct(top_var_w.iloc[0]['variance_share_of_composite'])}. Charts: `10_charts/slide_13_component_correlations/`.\n")
D.append("## Slide 14: Roles\n")
D.append(tbl(cov, ["skill", "role", "players", "n_eff_ge_30_reference", "ranked", "share_of_ranked_pool", "fail_n_eff_only", "fail_high_n_only"],
             ["skill", "role", "players", "reference (n_eff ≥ 30)", "ranked", "share of ranked pool", "fail n_eff only", "fail high-n only"]))
D.append("- Batting top 20 (top/middle/lower):")
D.append(f"  - now: role-only z {trio('rolerep_current_role_blend_1_role_only_top20')}; **official 50/50 blend {trio('rolerep_current_role_blend_0_5_official_top20')}**; pooled z {trio('rolerep_current_role_blend_0_pooled_top20')}.")
D.append(f"  - before the fixes: role-only {trio('rolerep_pre_fix_with_role_split_top20')}; pooled {trio('rolerep_pre_fix_without_role_split_top20')}. Legacy 8-term: role-only {trio('rolerep_legacy_8term_with_role_split_top20')}, pooled {trio('rolerep_legacy_8term_without_role_split_top20')}. [C]")
D.append(f"- Why roles at all: {ROLE_WHY}")
D.append("- Charts: `10_charts/slide_14_roles/`.\n")
D.append("## Slide 15: Limitations, fixes and bugs\n")
for _, r in lim.iterrows():
    if r["category"].startswith(("BUG", "KNOWN")) or r["id"] in {"M-01", "M-06", "M-07", "M-17", "M-18", "M-19"}:
        D.append(f"- **{r['id']} {r['title']}** [{r['verification_status']}]. {r['evidence']}")
D.append("- Full register: `09_limitations/limitations_register.csv`; before/after: `12_model_fixes/fix_before_after.csv`. Chart: `10_charts/slide_15_limitations/`.\n")
D.append("## Slide 16: Takeaways\n")
D.append("- See `key_findings.md` and `12_model_fixes/model_fixes.md`.")
D.append("- Not computed: DLS par analysis [RD]; uncertainty intervals for ranks [RI] (needs a bootstrap over matches); external validation against selections or awards [RD].")
(OUT / "11_presentation_summary/slide_by_slide_numbers.md").write_text("\n".join(D), encoding="utf-8")
reg.note("11_presentation_summary/slide_by_slide_numbers.md", "all section outputs", "generated text")
reg.close()

# ---------------------------------------------------------------- source traceability (after closing so it includes e)
traces = pd.concat([pd.read_csv(p) for p in sorted(CACHE.glob("trace_*.csv"))], ignore_index=True)
traces.insert(0, "kind", "output file")
head = [
    ("headline", "legal balls used", f["ds_legal_balls_used_in_ratings"], "01_dataset/cleaning_summary.csv", "legal_balls_used_in_ratings", "COMPUTED"),
    ("headline", "ranked batters / bowlers", f"{f['ranked_batters']} / {f['ranked_bowlers']}", "07_rankings/final_*_rankings.csv", "rows", "COMPUTED"),
    ("headline", "pressure weights situation/shock/run of play", f"{PW['situation']}/{PW['shock']}/{PW['run_of_play']}", "02_pressure/pressure_formula_as_executed.csv", "weights", "EXISTING"),
    ("headline", "batter band p80", f["pr_batter_p80"], "02_pressure/pressure_band_summary.csv", "p80_cutoff", "COMPUTED"),
    ("headline", "batter high band within 6 balls of a wicket (now / before)", f"{f['se_share_of_batter_high_band_balls_within_6_after_wicket']:.4f} / {f['se_pre_fix_bat_high_after_wicket']:.4f}", "06_shock/shock_event_summary.csv", "value", "COMPUTED"),
    ("headline", "bowler high band after a four/six (now / before)", f"{f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6']:.4f} / {f['se_pre_fix_bowl_high_after_boundary']:.4f}", "06_shock/shock_event_summary.csv", "value", "COMPUTED"),
    ("headline", "Spearman vs pre-fix model (batters / bowlers)", f"{abl('batter', 'previous_model_before_fixes', 'spearman_vs_full'):.4f} / {abl('bowler', 'previous_model_before_fixes', 'spearman_vs_full'):.4f}", "08_validation/ablation_summary.csv", "variant=previous_model_before_fixes", "COMPUTED"),
    ("headline", "Elo batter min/max/sd", f"{f['elo_batter_elo_min']:.1f}/{f['elo_batter_elo_max']:.1f}/{f['elo_batter_elo_sd']:.1f}", "04_elo/elo_summary.csv", "value", "COMPUTED"),
    ("headline", "xR MAE/R2 (now)", f"{f['xm_xR_bat_runs_mae']:.4f}/{f['xm_xR_bat_runs_r_squared']:.4f}", "05_expectation_models/expectation_model_metrics.csv", "scope=all", "COMPUTED"),
    ("headline", "xW AUC (now / before)", f"{f['xm_xW_bowler_wicket_auc']:.4f} / {f['xm_xW_bowler_wicket_pre_fix_auc']:.4f}", "05_expectation_models/expectation_model_metrics.csv", "scope=all, all_pre_fix_model", "COMPUTED"),
    ("headline", "runs minus xR at 8-9 down (now / before)", f"{f['wf_8-9_runs_resid']:.4f} / {f['wf_8-9_runs_resid_pre_fix']:.4f}", "05_expectation_models/residual_by_wickets_fallen.csv", "phase=all", "COMPUTED"),
    ("headline", "IPL 2025 final wickets (legal ball)", str(f["shock_actual_wicket_legal_n"]), "06_shock/shock_innings_timeline.csv", "is_wicket", "COMPUTED"),
    ("headline", "top-20 roles: role-only / blend / pooled", f"{trio('rolerep_current_role_blend_1_role_only_top20')} | {trio('rolerep_current_role_blend_0_5_official_top20')} | {trio('rolerep_current_role_blend_0_pooled_top20')}", "08_validation/role_ranking_representation.csv", "top_k=20", "COMPUTED"),
    ("headline", "Form weight (current)", "removed", "player_ratings.py", "weights block", "NOT_APPLICABLE"),
    ("headline", "DLS par / resources", "not in data", "01_dataset/dls_summary.csv", "", "REQUIRES_DATA"),
    ("headline", "rank uncertainty intervals", "not computed", "", "", "REQUIRES_IMPLEMENTATION"),
    ("headline", "external validation (selections/awards)", "no data", "", "", "REQUIRES_DATA"),
]
hd = pd.DataFrame(head, columns=["kind", "metric", "value", "output", "column_or_filter", "status"])
trace = pd.concat([hd, traces], ignore_index=True)
trace.to_csv(OUT / "11_presentation_summary/source_traceability.csv", index=False)
print("e done")
