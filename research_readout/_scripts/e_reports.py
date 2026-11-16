"""09_limitations, 08_validation/sanity_check_interpretations.md, 11_presentation_summary, README.md.

Every number below is read from the facts and CSVs produced by scripts a-d.
"""

from __future__ import annotations

import pandas as pd

from common import CACHE, COMPONENTS, LABEL, OUT, WEIGHTS, Registry, all_facts, load

reg = Registry("e")
f = all_facts()
P = load()


def pct(x, d=1):
    return f"{100 * float(x):.{d}f}%"


def num(x, d=0):
    return f"{float(x):,.{d}f}"


def r3(x):
    return f"{float(x):.3f}"


def g(key, d=3):
    return f"{float(f[key]):.{d}f}"


fb = pd.read_csv(OUT / "07_rankings/final_batter_rankings.csv")
fw = pd.read_csv(OUT / "07_rankings/final_bowler_rankings.csv")
sp = pd.read_csv(OUT / "08_validation/sanity_check_players.csv")
ab = pd.read_csv(OUT / "08_validation/ablation_summary.csv")
infl = pd.read_csv(OUT / "08_validation/component_influence.csv")
cov = pd.read_csv(OUT / "08_validation/role_coverage.csv")
summ = pd.read_csv(OUT / "03_components/component_summary.csv")
bands = pd.read_csv(OUT / "02_pressure/pressure_band_summary.csv")
phase = pd.read_csv(OUT / "02_pressure/phase_bowling_pressure.csv")
met = pd.read_csv(OUT / "05_expectation_models/expectation_model_metrics.csv")
elo_stab = pd.read_csv(OUT / "04_elo/elo_stability.csv")
ev = pd.read_csv(OUT / "06_shock/shock_event_summary.csv")
ev = ev.loc[ev["metric"].isna()]
rw = pd.read_csv(OUT / "05_expectation_models/residual_by_wickets_fallen.csv")
for _, row in rw.loc[rw["phase"].eq("all")].iterrows():
    f[f"wf_{row['wickets_before']}_e_bowl"] = float(row["mean_e_bowl"])
xr_all = pd.read_csv(OUT / "05_expectation_models/xruns_calibration_deciles.csv")
xr_all = xr_all.loc[xr_all["scope"].eq("all") & xr_all["target"].str.startswith("bat_runs")].reset_index(drop=True)


def abl(skill, variant, col):
    return ab.loc[ab["skill"].eq(skill) & ab["variant"].eq(variant), col].iloc[0]


def sanity(name, skill):
    hit = sp.loc[sp["player_name"].eq(name) & sp["skill"].eq(skill)]
    return hit.iloc[0] if len(hit) else None


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

# ---------------------------------------------------------------- limitations register
R = []


def item(iid, cat, title, desc, evidence, sev, affected, status, impact, rec):
    R.append({"id": iid, "category": cat, "title": title, "description": desc, "evidence": evidence, "severity": sev,
              "affected_outputs": affected, "verification_status": status, "quantified_impact": impact, "suggested_follow_up_not_implemented": rec})


item("BUG-01", "BUG", "Run-of-play term reads the whole innings on legal ball 19",
     "In _shock_and_delta the 18-ball window is wicket_sum[end] - wicket_sum[end-18]. At position 18 (legal ball 19) end-18 = -1, and numpy index -1 is the LAST element, so the window subtracts the innings total. Ball 19 therefore uses future balls of the same innings, and the extreme values inflate the SD used to scale every other ball.",
     f"Replicated exactly (max gap 0). Ball 19 mean run of play: batter {g('bug_rop_delta_bat_mean_at_19')} (bug-free {g('bug_rop_delta_bat_mean_at_19_bugfree')}), bowler {g('bug_rop_delta_bowl_mean_at_19')} (bug-free {g('bug_rop_delta_bowl_mean_at_19_bugfree')}). Scale: runs {g('scale_run_of_play_runs', 4)} vs bug-free {g('bug_rop_scale_runs_bugfree', 4)}; wickets {g('scale_run_of_play_wicket', 4)} vs {g('bug_rop_scale_wicket_bugfree', 4)}. Ball 19 bowler high-band share {pct(f['pro_share_of_ball_19_in_bowler_high_band'])} vs 20% design.",
     "High (bowlers), Low (batters)", "pressure_bat, pressure_bowl, band, band_bowl, every band and clutch component", "VERIFIED",
     f"Diagnostic rescoring with the bug removed: batters Spearman {r3(abl('batter', 'diagnostic_runofplay_bugfree', 'spearman_vs_full'))}, top-20 overlap {int(abl('batter', 'diagnostic_runofplay_bugfree', 'top20_overlap'))}/20; bowlers Spearman {r3(abl('bowler', 'diagnostic_runofplay_bugfree', 'spearman_vs_full'))}, top-20 overlap {int(abl('bowler', 'diagnostic_runofplay_bugfree', 'top20_overlap'))}/20. Band agreement batters {pct(f['diag_rop_band_agreement_bat'])}, bowlers {pct(f['diag_rop_band_agreement_bowl'])}.",
     "Guard the 18-ball window for end-18 < 0 (subtract 0), then rebuild ratings.")
item("BUG-02", "BUG", "Deck export 10 labels final shock as 'count_shock'",
     "write_deck_exports writes sample['shock_bat'] and sample['shock_bowl'] into columns named count_shock_bat / count_shock_bowl. After _add_expected_shock those columns hold count + excess shock, not the count part.",
     f"exports/10_sample_innings_timeline.csv count_shock_bat equals final shock: {f['export10_count_shock_bat_equals_final_shock']}; equals count part: {f['export10_count_shock_bat_equals_count_part']}.",
     "Low", "exports/10_sample_innings_timeline.csv and any slide built from it", "VERIFIED",
     "Labels only; values are the shock actually used. 06_shock/shock_innings_timeline.csv splits count, excess and final.", "Rename the columns or write both parts.")
item("BUG-03", "BUG / INCONSISTENCY", "Bowler clutch compares spell economy without extras to career economy with extras",
     "In score_bowlers the high-band spell economy uses charged_runs on legal balls (wides and no-balls are not legal rows), while the career economy it is compared with uses conceded on all deliveries (wides and no-ball runs included). A spell is therefore flattered by the bowler's own wide/no-ball rate.",
     f"Ranked bowlers: career economy with extras minus legal-balls-only economy = {g('clutch_bowl_basis_diff_mean_ranked')} runs/over on average = {g('clutch_bowl_basis_diff_units_mean_ranked')} clutch-scale units (scale {g('clutch_bowl_scale')}). High-band spells counted as beating the bowler's own rate: {pct(f['clutch_bowl_share_spells_beating_own_rate_as_executed'])} as executed vs {pct(f['clutch_bowl_share_spells_beating_own_rate_same_basis'])} on a like-for-like basis.",
     "Medium", "bowler clutch (weight 0.15)", "VERIFIED", "Shifts every bowler's own gap upward by their wide/no-ball rate; ranking effect not re-estimated (would require changing the method).",
     "Use the same delivery basis on both sides of the comparison.")
item("KI-01", "KNOWN ISSUE", "Form term used a full-career bar (look-ahead)",
     "Legacy form_by_season (git 29956ed) compared each of the previous 8 innings with the player's FULL-CAREER strike rate/economy, which includes later matches.",
     f"Source at git {P['head_rev'][:7]}: bar = float(career.loc[player]) with career = strike_rate/economy over all seasons. The current working tree removes Form entirely (7 terms, consistency 0.10).",
     "Resolved in current code", "legacy composite only", "VERIFIED (legacy); NOT_APPLICABLE (current)",
     f"Legacy 8-term vs current 7-term: batters Spearman {r3(abl('batter', 'legacy_8_term_with_form', 'spearman_vs_full'))}, top-20 overlap {int(abl('batter', 'legacy_8_term_with_form', 'top20_overlap'))}; bowlers Spearman {r3(abl('bowler', 'legacy_8_term_with_form', 'spearman_vs_full'))}, top-20 overlap {int(abl('bowler', 'legacy_8_term_with_form', 'top20_overlap'))}.",
     "If Form returns, use a point-in-time bar.")
item("KI-02", "KNOWN ISSUE", "xWicket is trained on bowler wickets but charged against every striker dismissal",
     "Wicket cells learn bowler_wicket (caught, bowled, LBW, stumped, hit wicket). The batter ball value subtracts 4 x (striker_out - xW), and striker_out includes run outs, retired out and obstructing. Non-striker dismissals hit nobody's ball value.",
     f"Legal balls: striker_out {num(f['ds_striker_out_legal'])} vs bowler_wicket {num(f['ds_bowler_wicket_legal'])}; striker run outs {num(f['ds_striker_runouts_legal'])}; non-striker dismissals {num(f['ds_nonstriker_dismissals_legal'])}. Mean xW {pct(f['xw_mean'], 2)} vs striker-out rate {pct(f['striker_out_rate'], 2)} and bowler-wicket rate {pct(f['bowler_wicket_rate'], 2)}. Mean wicket part of ball value: batter {g('e_bat_wicket_part_mean', 4)}, bowler {g('e_bowl_wicket_part_mean', 4)} per ball.",
     "Low-Medium", "e_bat, batter Elo, batter band components", "VERIFIED",
     f"Batter wicket penalty is biased by about {g('e_bat_wicket_part_mean', 4)} runs-equivalent per ball overall; concentrated on batters involved in run outs.",
     "Train a striker-dismissal expectation, or exclude run outs from the batter wicket term.")
item("KI-03", "KNOWN ISSUE", "No wickets-fallen feature in the expectation model",
     "Expectation cells are ladder x phase x arm (plus the Elo gap). Wickets already down are not a key, although they change scoring and dismissal rates.",
     f"Runs actual minus expected per ball: 0-1 down {g('wf_0-1_runs_resid', 3)}, 2-3 down {g('wf_2-3_runs_resid', 3)}, 4-5 down {g('wf_4-5_runs_resid', 3)}, 6-7 down {g('wf_6-7_runs_resid', 3)}, 8-9 down {g('wf_8-9_runs_resid', 3)}. Mean batter ball value at 8-9 down {g('wf_8-9_e_bat', 3)} on {num(f['wf_8-9_balls'])} balls.",
     "High", "e_bat, e_bowl, Elo, all band components", "VERIFIED",
     "Batters at the top of an innings are credited, tail batters penalised; bowlers who bowl to tails gain. Batters are z-scored within order groups, which absorbs part of this for batters; bowlers are pooled.",
     "Add a wickets-down key (e.g. 0-1, 2-4, 5-7, 8+) to the cells.")
item("KI-04", "KNOWN ISSUE", "Wides and no-balls never enter the ball value or Elo",
     "Charging follows the laws in `conceded` (wide: all runs; no-ball: no-ball run + bat runs). But ball value, Elo, xR, bands and clutch use legal rows only, so wide and no-ball runs and wickets off wides are invisible there. Baseline economy and peers include them.",
     f"{num(f['ds_runs_conceded_on_illegal_deliveries'])} of {num(f['ds_runs_conceded_total'])} conceded runs ({pct(f['ds_runs_conceded_on_illegal_deliveries'] / f['ds_runs_conceded_total'])}) are on illegal deliveries; {f['ds_bowler_wickets_illegal_delivery']} bowler wickets (stumpings off wides) are credited in baseline only.",
     "Medium", "e_bowl, bowler Elo, bowler bands, bowler clutch", "VERIFIED", "A wayward bowler is penalised only in baseline (0.20) and peers (0.10).", "Attach illegal-delivery runs to the next legal ball or model them separately.")
item("M-01", "METHODOLOGICAL", "High pressure is, in practice, the six balls after a wicket (batters) or a boundary (bowlers)",
     "The excess-wicket shock sits at its -0.5 floor whenever no wicket fell in the last six balls and near +1 after one; the base context term is small, so the top-20% cut is crossed almost only after a wicket. For bowlers the analogous trigger is a four/six or runs above expectation.",
     f"{pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'], 2)} of batter high-band balls are within 6 balls after a wicket; {pct(f['se_batter_high_band_share_otherwise'], 3)} of other balls are high. {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'], 2)} of bowler high-band balls follow a four or six in the previous six. Variance share of the occasion x competition x ball term: batters {pct(f['pr_var_share_base_bat'])}, bowlers {pct(f['pr_var_share_base_bowl'])}.",
     "High (interpretation)", "every 'pressure' claim", "VERIFIED", "Occasion (final vs league) moves the high-band share only from 21.3% to 26.1%.", "Present the high band as 'after a wicket / after being hit', or rebalance the terms.")
item("M-02", "METHODOLOGICAL", "The first 18 balls of an innings are almost never high pressure",
     "Shock needs six previous balls and run of play needs eighteen, so the opening three overs rarely reach the cut.",
     f"Batter high-band share on balls 1-18: {pct(f['pro_share_of_balls_1_to_18_in_batter_high_band'], 2)} vs {pct(f['pro_share_of_balls_19_plus_in_batter_high_band'])} from ball 19; bowlers {pct(f['pro_share_of_balls_1_to_18_in_bowler_high_band'])} on balls 1-18.",
     "Medium", "opening batters' and new-ball bowlers' high-band samples", "VERIFIED", "Openers face the high band only after early wickets.", "")
item("M-03", "METHODOLOGICAL", "Median batter pressure is negative",
     "The batter excess-wicket term is negative whenever no wicket fell recently.",
     f"Batter p50 = {g('pr_batter_p50')}; excess term at -0.5 floor on {pct(f['pro_share_balls_excess_wicket_term_at_floor_minus_0_5'])} of balls; final shock negative on {pct(f['pro_share_balls_batter_final_shock_negative'])}.",
     "Low", "interpretation of the pressure scale", "VERIFIED", "", "")
item("M-04", "METHODOLOGICAL", "Normalisation uses the full 2022-2026 sample",
     "Band cut-offs, z-score reference pools, and the shock/run-of-play scales are computed on all seasons, so they are not point-in-time. Per-ball xR/xW and Elo are sequential and do not look ahead.",
     "Code reading: _cut_band quantiles, zscore reference, std scales over full frame.", "Low (retrospective rating)", "bands, all z-scores", "VERIFIED", "Fine for a retrospective ranking; not valid as a live/forecast metric.", "")
item("M-05", "METHODOLOGICAL", "Season decay applies to some components only",
     "0.9^(2026-season) weights the band rates and n_eff. Baseline rates, peers, clutch and consistency are level-weighted only.",
     "Code reading: career_rate/weighted_count vs _weighted_mean and raw totals.", "Low-Medium", "baseline, peers, clutch, consistency", "VERIFIED", "Older seasons count fully in 0.55 of the weight.", "")
item("M-06", "METHODOLOGICAL", "Top bowlers sit close to the sample floor",
     "Eligibility is n_eff >= 120 and high-band n_eff >= 30. Several top bowlers have small high-band samples, and z-scores are capped at +-3 rather than shrunk further.",
     f"Median high-band n_eff: top-20 bowlers {num(samp['bowl_top20_median_high'], 1)} vs all ranked {num(samp['bowl_all_median_high'], 1)}; {samp['bowl_top10_high_lt60']} of the top-10 bowlers have high n_eff < 60. Humphreys high n_eff {num(sanity('Matthew Humphreys', 'bowler')['high_n_eff'], 1)}; Bosch {num(sanity('Corbin Bosch', 'bowler')['legal_balls'])} legal balls.",
     "Medium", "top of the bowling table", "VERIFIED", "", "Report intervals or a stricter floor for headline lists.")
item("M-07", "METHODOLOGICAL", "Expectation models discriminate weakly",
     "xR and xW are cell means with an Elo tilt.",
     f"xR: MAE {g('xm_xR_bat_runs_mae')} vs {g('xm_xR_bat_runs_mae_constant_in_sample_mean')} for a constant; R^2 {g('xm_xR_bat_runs_r_squared', 4)}; calibration slope {g('xm_xR_bat_runs_calibration_slope_ols')}. xW (bowler wicket): AUC {g('xm_xW_bowler_wicket_auc')}, Brier {g('xm_xW_bowler_wicket_brier', 5)} vs {g('xm_xW_bowler_wicket_brier_constant', 5)} constant, logistic slope {g('xm_xW_bowler_wicket_calibration_slope_logistic')}.",
     "Medium", "ball value for every component except baseline", "VERIFIED", "Ball values are close to 'actual minus phase average'.", "")
item("M-08", "METHODOLOGICAL", "Consistency works against the composite for batters",
     "Consistency rewards a low spread of match ball value; explosive batters score low.",
     f"Ranked batters: corr(consistency, composite) {g('corr_batters_consistency_composite')}; corr(peers, consistency) {f['corr_batters_min_pair'][2]:.3f}. Cap share for consistency at +-3: {pct(cap.loc[('batter', 'consistency'), 'share_at_plus3_cap'] + cap.loc[('batter', 'consistency'), 'share_at_minus3_cap'])}.",
     "Low", "batter composite", "VERIFIED", f"Variance share of consistency in the batter composite {pct(infl_get('batter', 'consistency', 'variance_share_of_composite'))}.", "")
item("M-09", "METHODOLOGICAL", "Lower-level events are discounted twice",
     "Emerging/Rising balls count 0.5 (level weight) and also carry a 0.7 competition multiplier in pressure.", f"{num(f['ds_legal_T20'])} legal balls in {f['ds_matches_T20']} matches.", "Low", "players with many A-team matches", "VERIFIED", "", "")
item("M-10", "DATA", "Competition coverage", "IPL 2022-2026, bilateral and tri-series T20Is, two Asia Cups and two A-team events. No T20 World Cup, no other franchise leagues. Tri-series and Asia Cup finals carry the same 3.0 occasion as an IPL final.",
     f"Matches with legal balls: IPL {f['ds_matches_IPL']}, T20I {f['ds_matches_T20I']}, T20 {f['ds_matches_T20']}.", "Medium", "external validity", "VERIFIED", "", "")
item("M-11", "DATA", "DLS detail is limited", "Only revised overs and revised target are supplied; no par scores or resource tables.",
     f"Reduced matches {f['dls_reduced_matches']}; chases with no supplied target (no required rate) {f['dls_excluded_matches']} matches.", "Low", "required-rate term", "VERIFIED", "", "")
item("M-12", "DATA", "Source anomalies kept as supplied", "Deliveries with a player missing from the squad sheet are kept; one over has more than six legal balls; three rows have extras amounts that do not fit the type.",
     f"sheet_gap deliveries {f['ds_deliveries_flagged_sheet_gap']}; overs with >6 legal balls {f['ds_overs_with_more_than_6_legal_balls']}.", "Low", "", "VERIFIED", "", "")
item("M-13", "ASSUMPTION", "'Other' extras are treated as illegal", "Decided in cleaning: counting them legal puts 150 innings past 120 legal balls.", f"{f['ds_other_extras']} 'other' deliveries.", "Low", "", "EXISTING", "", "")
item("M-14", "CODE HYGIENE", "Dead code and stale comments", "expectation_tables() and venue_ratings() are defined but never called; zscore's comment still says 'the other seven terms'; run_elo's `venues` argument is ignored.", "grep over *.py and *.ipynb", "Low", "", "VERIFIED", "", "")
item("M-15", "METHODOLOGICAL", "Elo affects the ranking only through expectations", "The composite is built from ball values; final Elo ratings are not a component.",
     f"Season-end rating stability (Spearman, keys with >=120 balls both seasons): batters {g('elo_yoy_batter_2022', 2)}-{g('elo_yoy_batter_2025', 2)}, bowlers {g('elo_yoy_bowler_2023', 2)}-{g('elo_yoy_bowler_2025', 2)}. Step-size sensitivity: composite Spearman >= {min(f['elo_sens_half_steps_batter_spearman'], f['elo_sens_double_steps_bowler_spearman'], f['elo_sens_half_steps_bowler_spearman'], f['elo_sens_double_steps_batter_spearman']):.3f}.",
     "Low", "", "VERIFIED", "", "")
item("M-16", "METHODOLOGICAL", "Super overs get knockout occasion but cannot reach the high band",
     "Super overs are included with occasion max(stage, 1.5), death-phase ball difficulty and a chase rate in innings 4. Shock and run of play are computed per innings, so they start at zero for a super over, and the occasion-scaled base alone stays below the high cut.",
     f"{f['pro_super_over_legal_balls']} legal balls; batter high-band share {pct(f['pro_super_over_share_in_batter_high_band'])}, bowler {pct(f['pro_super_over_share_in_bowler_high_band'])}; highest super-over batter pressure is {abs(f['pro_super_over_max_pressure_bat_vs_p80_cutoff']):.3f} below the p80 cut. Ranking effect vs excluding them: Spearman {abl('batter', 'exclude_super_overs', 'spearman_vs_full'):.4f} (batters), {abl('bowler', 'exclude_super_overs', 'spearman_vs_full'):.4f} (bowlers).",
     "Low", "super-over specialists' high band and clutch", "VERIFIED", "", "")
lim = pd.DataFrame(R)
reg.save(lim, "09_limitations/limitations_register.csv", "facts from scripts a-d", "one row per issue")

# ---------------------------------------------------------------- methodological audit
W = []
w = W.append
w("# Methodological audit\n")
w("This audit describes what the code in this repository actually executes, checked against the data. Nothing in the repository was changed. Where a number is given, it comes from a file in `research_readout/` (see `11_presentation_summary/source_traceability.csv`).\n")
w("## 0. Version under audit\n")
w(f"- Working tree `player_ratings.py`: **seven** weighted terms. Baseline 0.20, zero band 0.10, medium band 0.15, high band 0.20, clutch 0.15, peers 0.10, consistency 0.10. They sum to {f['weights_current_sum']:.2f}.")
w(f"- The brief describes **eight** terms, with Form 0.05 and consistency 0.05. That is the version at git `{P['head_rev'][:7]}`. Form was removed at the user's request (committed in 7af5382), and consistency was raised to 0.10.")
w(f"- Super overs are **included** (changed in this session at the user's request; every commit up to 7af5382 drops them). {f['ds_super_over_deliveries_included']} deliveries, {f['ds_super_over_legal_balls_included']} legal balls, {f['ds_super_over_matches']} matches. Every super-over ball is a death ball, its occasion is max(stage occasion, 1.5) so it is never below a knockout, and the second super over chases the first super over's total + 1.")
w("- All official numbers in this pack come from the working tree. The 8-term version's scoring functions were re-run read-only from git 29956ed on the same legal frame (super overs included), so the comparison isolates the Form change. It is reported as `legacy_8_term_with_form` wherever a comparison helps. Form is marked NOT_APPLICABLE for the current model.")
w(f"- Reproduction: the in-memory run reproduces the shipped `ratings/batters.csv` and `ratings/bowlers.csv` exactly (max composite gap 2e-16, identical ranks). Ranked: {f['ranked_batters']} batters, {f['ranked_bowlers']} bowlers.\n")
w("## 1. Data and cleaning\n")
w(f"- {num(f['ds_raw_deliveries_source_file'])} deliveries; none are deleted in cleaning. Duplicate delivery keys: {f['ds_duplicate_delivery_keys_match_innings_ballnum']}.")
w(f"- Super overs are kept: {f['ds_super_over_deliveries_included']} deliveries ({f['ds_super_over_legal_balls_included']} legal balls) in {f['ds_super_over_matches']} matches.")
w(f"- Excluded from ball value: {num(f['ds_illegal_deliveries_wide_noball_other'])} illegal deliveries ({num(f['ds_wides'])} wides, {f['ds_noballs']} no-balls, {f['ds_other_extras']} 'other').")
w(f"- Used: **{num(f['ds_legal_balls_used_in_ratings'])} legal balls** in {f['ds_matches_with_legal_balls']} matches, {f['ds_first_match_date']} to {f['ds_last_match_date']}. Ladders: IPL {num(f['ds_legal_IPL'])} balls in {f['ds_matches_IPL']} matches; T20I {num(f['ds_legal_T20I'])} in {f['ds_matches_T20I']}; T20 (Emerging/Rising) {num(f['ds_legal_T20'])} in {f['ds_matches_T20']}.")
w(f"- Dismissals: bowler wickets are caught, bowled, LBW, stumped and hit wicket. Run outs ({f['ds_runouts_used']} used), retired out and obstructing do not credit the bowler.")
w(f"- Reduced matches: {f['dls_reduced_matches']}. Reduced chases with no supplied target get no required rate ({f['dls_excluded_matches']} matches). DLS par scores are not in the data (REQUIRES_DATA).\n")
w("## 2. Pressure as executed\n")
w("```\npressure_bat  = occasion x competition x ball_bat  + shock_bat  + run_of_play_bat\npressure_bowl = occasion x competition x ball_bowl + shock_bowl + run_of_play_bowl\n```")
w("- Occasion: Final 3.0, Semi 2.0, Qualifier/Eliminator 1.5, Super 4 1.3, League 1.0, other bilateral 0.8, dead rubber 0.4 (" + str(f["ds_dead_rubber_matches_occasion_0_4"]) + " matches). A super-over ball takes max(stage occasion, 1.5), even in a dead rubber. Competition: 0.7 for Emerging/Rising, otherwise 1.0.")
w("- Ball difficulty (clipped 0..1). Batter: phase term (PP 0.25, middle 0.10, death 0.40), plus a wickets term (2–4 down 0.15, 5+ down 0.30), plus a chase-rate term (RRR ≥ 8 adds 0.15, RRR ≥ 12 adds 0.30). Bowler: phase term (PP 0.32, middle 0.24; death 0.32 to a recognised batter, otherwise 0.14), plus a wickets term (−0.10 or −0.25), plus the same rate term.")
w(f"- Shock has two parts, added together and clipped to −0.5..1.")
w(f"  - A count part over the previous six legal balls. Batter: 0.33 per wicket plus 0.05 per dot. Bowler: 0.33 per six plus 0.12 per four.")
w(f"  - An excess part, scaled by SDs of {g('scale_excess_wicket', 4)} (wickets) and {g('scale_excess_runs', 4)} (runs). Batter: the sum of (bowler wicket − xW). Bowler: the sum of (charged − xR).")
w(f"- Run of play compares the last 6 balls with the last 18: wickets per ball for batters, bat runs per ball for bowlers. It is scaled by SDs of {g('scale_run_of_play_wicket', 4)} and {g('scale_run_of_play_runs', 4)}, and clipped to −0.5..1. **The executed scale includes the ball-19 bug (BUG-01).**")
w(f"- Bands are recut after the Elo walk, once the excess shock is added. They agree with the pre-Elo bands on {pct(f['pr_band_agreement_pre_vs_final'])} of balls.")
w(f"- Final cut-offs: batter p50 {g('pr_batter_p50')}, p80 {g('pr_batter_p80')}. Pace bowlers p50 {g('pr_bowler_pace_p50')}, p80 {g('pr_bowler_pace_p80')}. Spin bowlers p50 {g('pr_bowler_spin_p50')}, p80 {g('pr_bowler_spin_p80')}. These match `exports/08_band_cutoffs.csv`.")
w(f"- Variance decomposition of batter pressure: base term {pct(f['pr_var_share_base_bat'])}, shock {pct(f['pr_var_share_shock_bat'])}, run of play {pct(f['pr_var_share_delta_bat'])}. For bowlers: {pct(f['pr_var_share_base_bowl'])}, {pct(f['pr_var_share_shock_bowl'])}, {pct(f['pr_var_share_delta_bowl'])}.")
w(f"- **What the high band captures.** {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'], 2)} of batter high-band balls lie within six balls after a wicket. {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'], 2)} of bowler high-band balls follow a four or six in the previous six balls (M-01). Balls 1–18 are high for batters only {pct(f['pro_share_of_balls_1_to_18_in_batter_high_band'], 2)} of the time (M-02).\n")
w("## 3. Expectation models and ball value\n")
w("- Cells are ladder → phase → phase × arm, each pulled toward the coarser level with 30 balls. The priors are 1.0 run and 0.05 wickets. Every prediction uses only balls already bowled, in date, match, innings and ball order, so there is no look-ahead in xR or xW.")
w("- The Elo gap is 0.15 × (batter − bowler)/400 + 0.05 × (side gap)/400 + 0.10 × (ground − 1500)/400. It gives xR = cell mean × exp(gap), capped 0..6, and xW = logistic(logit(cell rate) − gap), capped 0.002..0.40.")
w("- Batter ball value = (bat runs − xR) − 4 × (striker out − xW). Bowler ball value = (xR_bowl − charged) + 4 × (bowler wicket − xW).")
w(f"- xR: mean predicted {g('xm_xR_bat_runs_mean_predicted', 4)} against mean actual {g('xm_xR_bat_runs_mean_actual', 4)}. MAE {g('xm_xR_bat_runs_mae', 4)}, RMSE {g('xm_xR_bat_runs_rmse', 4)}, OLS calibration slope {g('xm_xR_bat_runs_calibration_slope_ols', 3)}, intercept {g('xm_xR_bat_runs_calibration_intercept_ols', 3)}, R² {g('xm_xR_bat_runs_r_squared', 4)}.")
w(f"- xW against bowler wickets: mean {pct(f['xm_xW_bowler_wicket_mean_predicted'], 2)} predicted, {pct(f['xm_xW_bowler_wicket_mean_actual'], 2)} actual. AUC {g('xm_xW_bowler_wicket_auc')}, Brier {g('xm_xW_bowler_wicket_brier', 5)}, logistic slope {g('xm_xW_bowler_wicket_calibration_slope_logistic')}, intercept {g('xm_xW_bowler_wicket_calibration_intercept_logistic')}.")
w(f"- xW against striker out: actual {pct(f['xm_xW_striker_out_mean_actual'], 2)}, AUC {g('xm_xW_striker_out_auc')} (KI-02).")
w(f"- Wickets down are not a feature (KI-03). Runs actual minus expected falls from {g('wf_0-1_runs_resid')} per ball at 0–1 down to {g('wf_8-9_runs_resid')} at 8–9 down.\n")
w("## 4. Elo\n")
w(f"- Ratings start at 1500 and are kept per (player, ladder). Steps used: runs 4, wicket 16, team 20. The fallback that halves them to 2/8/10 was **not** triggered: final spreads are inside the 600–2800 / SD 250 acceptance window.")
w(f"- Final raw ratings: batters {g('elo_batter_elo_min', 1)}–{g('elo_batter_elo_max', 1)} (SD {g('elo_batter_elo_sd', 1)}); bowlers {g('elo_bowler_elo_min', 1)}–{g('elo_bowler_elo_max', 1)} (SD {g('elo_bowler_elo_sd', 1)}); teams {g('elo_team_elo_min', 1)}–{g('elo_team_elo_max', 1)}.")
w(f"- A new player's rating is pulled toward 1500 until they have about 30 balls. Ground ratings are shrunk with 2,400 balls; {f['elo_grounds']} grounds are seen.")
w(f"- Diagnostic step-size sensitivity, re-running with half and with double steps: composite Spearman is {g('elo_sens_half_steps_batter_spearman')} and {g('elo_sens_double_steps_batter_spearman')} for batters, {g('elo_sens_half_steps_bowler_spearman')} and {g('elo_sens_double_steps_bowler_spearman')} for bowlers.\n")
w("## 5. Components and composite\n")
for comp in COMPONENTS:
    w(f"- **{LABEL[comp]}** (weight {WEIGHTS[comp]:.2f}). Ranked batters: SD {cap.loc[('batter', comp), 'sd']:.3f}, at the ±3 cap {pct(cap.loc[('batter', comp), 'share_at_plus3_cap'] + cap.loc[('batter', comp), 'share_at_minus3_cap'])}, variance share {pct(infl_get('batter', comp, 'variance_share_of_composite'))}. Ranked bowlers: SD {cap.loc[('bowler', comp), 'sd']:.3f}, at the cap {pct(cap.loc[('bowler', comp), 'share_at_plus3_cap'] + cap.loc[('bowler', comp), 'share_at_minus3_cap'])}, variance share {pct(infl_get('bowler', comp, 'variance_share_of_composite'))}.")
w("- Batters are z-scored within top, middle and lower order. Bowlers are z-scored across all bowlers, even though their bands are cut within pace and within spin.")
w("- Eligibility: n_eff ≥ 120 and high-band n_eff ≥ 30, both decay- and level-weighted.\n")
w("## 6. Robustness\n")
for skill in ["batter", "bowler"]:
    w(f"- {skill.title()}s, compared with the official ranking:")
    w(f"  - baseline only: Spearman {r3(abl(skill, 'baseline_only', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'baseline_only', 'top20_overlap'))}")
    w(f"  - pressure only: Spearman {r3(abl(skill, 'pressure_only_bands_clutch', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'pressure_only_bands_clutch', 'top20_overlap'))}")
    w(f"  - equal weights: Spearman {r3(abl(skill, 'equal_weights', 'spearman_vs_full'))}")
    w(f"  - legacy 8-term model: Spearman {r3(abl(skill, 'legacy_8_term_with_form', 'spearman_vs_full'))}")
    w(f"  - ball-19 bug removed (diagnostic): Spearman {r3(abl(skill, 'diagnostic_runofplay_bugfree', 'spearman_vs_full'))}, top-20 overlap {int(abl(skill, 'diagnostic_runofplay_bugfree', 'top20_overlap'))}")
    w(f"  - super overs excluded (the earlier pipeline): Spearman {abl(skill, 'exclude_super_overs', 'spearman_vs_full'):.4f}, top-20 overlap {int(abl(skill, 'exclude_super_overs', 'top20_overlap'))}")
w("\n## 7. Issues\n")
w("See `limitations_register.csv`. Bugs: BUG-01 (the ball-19 run-of-play index), BUG-02 (an export label), and BUG-03 (the delivery basis of bowler clutch). Known issues: KI-01 (resolved by removing Form), KI-02, KI-03 and KI-04, all verified with numbers.")
(OUT / "09_limitations").mkdir(exist_ok=True)
(OUT / "09_limitations/methodological_audit.md").write_text("\n".join(W), encoding="utf-8")
reg.note("09_limitations/methodological_audit.md", "facts a-d", "generated text")

# ---------------------------------------------------------------- cricketing interpretations
ci = []
c = ci.append
c("# Cricketing interpretations\n")
c("These readings rest on the computed numbers. Each one says which number it rests on. They describe what the model measures, and they are not claims about players beyond the data.\n")
bz, bm_, bhh = bh.loc[("batter_all", "zero")], bh.loc[("batter_all", "medium")], bh.loc[("batter_all", "high")]
c(f"1. **Batting 'pressure' here means batting just after a wicket.** In the high band, strike rate is {bhh['strike_rate']:.1f} against {bz['strike_rate']:.1f} in the zero band, and the striker-out rate is {pct(bhh['striker_out_rate'], 2)} against {pct(bz['striker_out_rate'], 2)}. Across all innings, strike rate is {f['se_strike_rate_within_6_after_wicket']:.1f} within six balls of a wicket and {f['se_strike_rate_otherwise']:.1f} otherwise. A high-band score therefore rewards a batter who keeps scoring while the innings is being rebuilt.")
pz, ph_ = bh.loc[("bowler_pace", "zero")], bh.loc[("bowler_pace", "high")]
sz, shh = bh.loc[("bowler_spin", "zero")], bh.loc[("bowler_spin", "high")]
c(f"2. **Bowling 'pressure' here means bowling just after being hit.** Economy on legal balls rises from {pz['economy_legal_balls']:.2f} to {ph_['economy_legal_balls']:.2f} for pace and from {sz['economy_legal_balls']:.2f} to {shh['economy_legal_balls']:.2f} for spin, from the zero band to the high band. A bowler who scores well in the high band is one who stops the bleeding after a boundary.")
c(f"3. **Spin carries most of the middle-overs pressure; pace spreads across phases.** {pct(f['pr_phase_Spin_middle_share_of_arm_high'])} of spin high-band balls are in the middle overs. Pace splits {pct(f['pr_phase_Pace_powerplay_share_of_arm_high'])} powerplay, {pct(f['pr_phase_Pace_middle_share_of_arm_high'])} middle and {pct(f['pr_phase_Pace_death_share_of_arm_high'])} death.")
c(f"4. **Finishers dominate the batting top 10.** The role split is {f['rolerep_current_with_role_split_top10'][0]} top, {f['rolerep_current_with_role_split_top10'][1]} middle and {f['rolerep_current_with_role_split_top10'][2]} lower order. Lower-order ranked batters average {pct(f['role_highshare_batter_lower order'])} of their balls in the high band, against {pct(f['role_highshare_batter_top order'])} for top-order batters. They walk in after wickets, so more of their batting is 'pressure' by construction.")
c(f"5. **The role split decides how many finishers appear.** With role-split z-scores the top 20 is {f['rolerep_current_with_role_split_top20']} (top/middle/lower). With pooled z-scores it is {f['rolerep_current_without_role_split_top20']}. That flip is a modelling choice, not a cricket finding.")
c("6. **Batting ranks rest mostly on baseline output and the high band.** Variance shares in the batter composite: "
  + ", ".join(f"{r['label'].lower()} {pct(r['variance_share_of_composite'])}" for _, r in top_var_b.iterrows())
  + ". Consistency's share is negative, so it pulls against the other terms.")
c(f"7. **Bowling ranks lean more on pressure terms.** For bowlers the high band takes {pct(infl_get('bowler', 'band_high', 'variance_share_of_composite'))} of variance and clutch takes {pct(infl_get('bowler', 'clutch', 'variance_share_of_composite'))}. Baseline-only and full rankings share just {int(abl('bowler', 'baseline_only', 'top20_overlap'))} of the top 20.")
c(f"8. **Tail situations distort ball value.** Batters at 8–9 down average {g('wf_8-9_e_bat')} runs-equivalent per ball and the bowlers facing them average {g('wf_8-9_e_bowl') if 'wf_8-9_e_bowl' in f else 'n/a'}. Because the model does not know wickets are down, death-over bowlers who often bowl at tails look better.")
c(f"9. **The shock timeline follows the 2025 final chase.** RCB won by 6 runs. PBKS's {len(f['shock_actual_wicket_legal_n'])} wickets fell at legal balls {', '.join(map(str, f['shock_actual_wicket_legal_n']))}. Batter pressure first reaches its peak of {g('shock_peak_pressure_bat', 2)} on ball {f['shock_peak_pressure_bat_n']}, straight after the wicket at ball 98 (over 17.2), with the next wicket at ball 100. {f['shock_high_band_balls_bat']} of the 120 balls are batter-high.")
(OUT / "09_limitations/cricketing_interpretations.md").write_text("\n".join(ci), encoding="utf-8")
reg.note("09_limitations/cricketing_interpretations.md", "facts a-d", "generated text")

# ---------------------------------------------------------------- sanity interpretations
S = ["# Sanity-check interpretations\n",
     "Every number comes from `sanity_check_players.csv`. Ranks are out of the ranked pool: 216 batters, 226 bowlers. 'Legacy' means the 8-term model with Form, re-run from git 29956ed. 'Baseline-only' ranks on the baseline z alone. Interpretations are marked as such.\n"]


def line(name, skill):
    r = sanity(name, skill)
    if r is None:
        return f"- **{name} ({skill})**: not in the data."
    comps = ", ".join(f"{LABEL[cc].lower()} {r[cc]:+.2f}" for cc in COMPONENTS)
    if not r["ranked"]:
        return (f"- **{name} ({skill}, {r['role']})**: not ranked ({r['reason_not_ranked']}); composite {r['composite']:.3f} on {int(r['legal_balls'])} legal balls. Components: {comps}.")
    best = max(COMPONENTS, key=lambda cc: r[cc] * WEIGHTS[cc])
    worst = min(COMPONENTS, key=lambda cc: r[cc] * WEIGHTS[cc])
    extra = f"strike rate {r['strike_rate_level_weighted']:.1f}, average {r['average_level_weighted']:.1f}" if skill == "batter" else f"economy {r['economy_level_weighted']:.2f}, balls per wicket {r['balls_per_wicket_level_weighted']:.1f}"
    elo = "; ".join(f"{lad} Elo {r[f'elo_final_{lad}']:.0f}" for lad in ["IPL", "T20I", "T20"] if pd.notna(r[f"elo_final_{lad}"]))
    return (f"- **{name} ({skill}, {r['role']})**: rank **{int(r['rank'])}** (composite {r['composite']:.3f}); legacy rank {int(r['legacy_rank_8term'])}, baseline-only rank {int(r['baseline_only_rank'])}"
            + (f", pooled-z rank {int(r['no_role_split_rank'])}" if pd.notna(r.get("no_role_split_rank")) else "")
            + f". {int(r['legal_balls'])} legal balls (n_eff {r['n_eff']:.0f}, high n_eff {r['high_n_eff']:.0f}); {extra}. {elo}. Components: {comps}. "
            + f"Largest lift: {LABEL[best].lower()}; largest drag: {LABEL[worst].lower()}.")


for name, skill in [("Jos Buttler", "batter"), ("Virat Kohli", "batter"), ("David Miller", "batter"), ("Rilee Rossouw", "batter"),
                    ("Mahendra Singh Dhoni", "batter"), ("Tim David", "batter"), ("Vaibhav Sooryavanshi", "batter"), ("Rahmanullah Gurbaz", "batter"),
                    ("Rashid Khan", "batter"), ("Corbin Bosch", "batter"), ("Imad Wasim", "batter"),
                    ("Jasprit Bumrah", "bowler"), ("Rashid Khan", "bowler"), ("Matthew Humphreys", "bowler"), ("Corbin Bosch", "bowler"), ("Imad Wasim", "bowler")]:
    S.append(line(name, skill))
S.append("\n## Interpretation (analyst reading of the numbers above)\n")
kb, bb, mb = sanity("Virat Kohli", "batter"), sanity("Jos Buttler", "batter"), sanity("David Miller", "batter")
S.append(f"- **The established elite batters sit in the 30s and 40s, not the top 10.** Kohli is {int(kb['rank'])}, Buttler {int(bb['rank'])}, Miller {int(mb['rank'])}. On baseline alone they would be {int(kb['baseline_only_rank'])}, {int(bb['baseline_only_rank'])} and {int(mb['baseline_only_rank'])}. Their high-band and clutch terms are modest, so the pressure layer pulls them down relative to finishers. Whether that is right depends on accepting that 'pressure' means 'after a wicket' (M-01).")
so, gu = sanity("Vaibhav Sooryavanshi", "batter"), sanity("Rahmanullah Gurbaz", "batter")
S.append(f"- **Sooryavanshi is the baseline leader (1st), but the full composite holds him at {int(so['rank'])}.** His clutch ({so['clutch']:+.2f}) and consistency ({so['consistency']:+.2f}, at the cap) offset a near-maximal baseline ({so['baseline']:+.2f}) and peers ({so['peers']:+.2f}). His high-band sample is {so['high_n_eff']:.1f} weighted balls, close to the floor of 30.")
S.append(f"- **Gurbaz rises from {int(gu['baseline_only_rank'])} on baseline to {int(gu['rank'])}.** Almost all of the rise is clutch ({gu['clutch']:+.2f}, at the cap) and the high band ({gu['band_high']:+.2f}). It is the largest single example of the pressure layer overriding raw output, and it rests on a high-band n_eff of {gu['high_n_eff']:.1f}.")
bo, hu, bu = sanity("Corbin Bosch", "bowler"), sanity("Matthew Humphreys", "bowler"), sanity("Jasprit Bumrah", "bowler")
S.append(f"- **The two top bowlers are small-sample, pressure-driven ranks.** Bosch (1st, {int(bo['legal_balls'])} balls, clutch {bo['clutch']:+.2f}, high band {bo['band_high']:+.2f}) and Humphreys (2nd, {int(hu['legal_balls'])} balls, high n_eff {hu['high_n_eff']:.1f}) both lead on pressure terms. Bumrah is {int(bu['rank'])}th on a much larger sample ({int(bu['legal_balls'])} balls), with the top IPL bowler Elo ({bu['elo_final_IPL']:.0f}). Read the top two with caution (M-06).")
rk_b, rk_w = sanity("Rashid Khan", "batter"), sanity("Rashid Khan", "bowler")
S.append(f"- **Rashid Khan ranks {int(rk_b['rank'])}th as a batter and {int(rk_w['rank'])}th as a bowler.** His bowling clutch is {rk_w['clutch']:+.2f} and his high band {rk_w['band_high']:+.2f}, yet his baseline-only bowling rank is {int(rk_w['baseline_only_rank'])} and his T20I Elo is {rk_w['elo_final_T20I']:.0f}. BUG-03 can only raise a bowler's clutch, so the negative value is not caused by it. As executed, his high-band spells, which are overs bowled just after a boundary (M-01), cost more on average than his career rate. A spell below his own rate counts in full, whatever his team-mates did. This is the most counter-intuitive result in the sanity set.")
dh, td = sanity("Mahendra Singh Dhoni", "batter"), sanity("Tim David", "batter")
S.append(f"- **Dhoni (3rd) and Tim David (2nd) fit the finisher pattern.** Both score heavily on medium, high and clutch terms. Dhoni's consistency is {dh['consistency']:+.2f}; David's peers term is {td['peers']:+.2f} (at the cap).")
im = sanity("Imad Wasim", "batter")
S.append(f"- **Imad Wasim's batting misses the floor by {120 - im['n_eff']:.1f} weighted balls** (n_eff {im['n_eff']:.1f}). His bowling ranks {int(sanity('Imad Wasim', 'bowler')['rank'])}th.")
(OUT / "08_validation/sanity_check_interpretations.md").write_text("\n".join(S), encoding="utf-8")
reg.note("08_validation/sanity_check_interpretations.md", "08_validation/sanity_check_players.csv", "generated text")

# ---------------------------------------------------------------- key findings
K = ["# Key findings\n", "Ordered by importance for the presentation. Every number links to a file in this pack.\n"]
K.append(f"1. **'High pressure' is operationally the six balls after a wicket (batting) or after a boundary (bowling).** For batters the figure is {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'], 2)} of high-band balls; for bowlers, {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'], 2)} follow a four or six in the previous six. Occasion, phase, wickets and required rate together explain only {pct(f['pr_var_share_base_bat'])} of batter pressure variance. *(06_shock/shock_event_summary.csv, 02_pressure/pressure_summary.csv)*")
K.append(f"2. **A ball-19 indexing bug affects every pressure value through the scale.** Run of play on ball 19 is pinned near 1, and the bowler run-of-play scale is inflated ({g('scale_run_of_play_runs')} against {g('bug_rop_scale_runs_bugfree')}). With the bug removed (a diagnostic, not official), the bowler ranking moves: Spearman {r3(abl('bowler', 'diagnostic_runofplay_bugfree', 'spearman_vs_full'))}, top-20 overlap {int(abl('bowler', 'diagnostic_runofplay_bugfree', 'top20_overlap'))}/20. Batters barely move ({r3(abl('batter', 'diagnostic_runofplay_bugfree', 'spearman_vs_full'))}, {int(abl('batter', 'diagnostic_runofplay_bugfree', 'top20_overlap'))}/20). *(09_limitations BUG-01, 08_validation/ablation_summary.csv)*")
K.append(f"3. **The pressure layer changes the ranking a lot, the exact weights much less.** Baseline-only against the full model shares {int(abl('batter', 'baseline_only', 'top20_overlap'))}/20 of the batting top 20 and {int(abl('bowler', 'baseline_only', 'top20_overlap'))}/20 of the bowling top 20. Equal weights still give Spearman {r3(abl('batter', 'equal_weights', 'spearman_vs_full'))} for batters and {r3(abl('bowler', 'equal_weights', 'spearman_vs_full'))} for bowlers. *(08_validation/ablation_summary.csv)*")
K.append(f"4. **The top of each table.** Batters: {', '.join(f'{int(x[0])}. {x[1]}' for x in f['top10_batters'][:5])}. Bowlers: {', '.join(f'{int(x[0])}. {x[1]}' for x in f['top10_bowlers'][:5])}. *(07_rankings)*")
K.append(f"5. **Small samples sit at the top of the bowling table.** {samp['bowl_top10_high_lt60']} of the top-10 bowlers have a high-band n_eff below 60. The median high-band n_eff is {num(samp['bowl_top20_median_high'], 1)} for the top 20 against {num(samp['bowl_all_median_high'], 1)} for all ranked bowlers. *(07_rankings/final_bowler_rankings.csv)*")
K.append(f"6. **The role split creates the batting role mix.** The top 20 is {f['rolerep_current_with_role_split_top20']} (top/middle/lower) with role-split z-scores and {f['rolerep_current_without_role_split_top20']} pooled. Your 12/5/3 reproduces only in the legacy 8-term model ({f['rolerep_legacy_8term_without_role_split_top20']}). *(08_validation/role_ranking_representation.csv)*")
K.append(f"7. **Expectation models are well calibrated on average but barely discriminate.** xR: slope {g('xm_xR_bat_runs_calibration_slope_ols')}, R² {g('xm_xR_bat_runs_r_squared', 4)}, MAE {g('xm_xR_bat_runs_mae')} against {g('xm_xR_bat_runs_mae_constant_in_sample_mean')} for a constant. xW: AUC {g('xm_xW_bowler_wicket_auc')}. *(05_expectation_models/expectation_model_metrics.csv)*")
K.append(f"8. **The missing wickets-fallen feature biases ball value.** At 8–9 down, batters average {g('wf_8-9_e_bat')} per ball and their bowlers {g('wf_8-9_e_bowl') if 'wf_8-9_e_bowl' in f else 'see file'}. *(05_expectation_models/residual_by_wickets_fallen.csv)*")
K.append(f"9. **Elo is stable and well inside its bounds.** Steps were not halved. Batters range {g('elo_batter_elo_min', 0)}–{g('elo_batter_elo_max', 0)}, bowlers {g('elo_bowler_elo_min', 0)}–{g('elo_bowler_elo_max', 0)}. Half or double steps leave the composite at Spearman ≥ {min(f['elo_sens_half_steps_bowler_spearman'], f['elo_sens_double_steps_bowler_spearman']):.3f}. *(04_elo)*")
K.append(f"10. **Form has been removed (seven terms, consistency 0.10).** The old 8-term ranking differs only slightly: Spearman {r3(abl('batter', 'legacy_8_term_with_form', 'spearman_vs_full'))} for batters and {r3(abl('bowler', 'legacy_8_term_with_form', 'spearman_vs_full'))} for bowlers. Its look-ahead (KI-01) no longer applies. *(08_validation/ablation_summary.csv)*")
K.append(f"11. **The 2025 final's wicket timeline is verified.** PBKS lost wickets at legal balls {', '.join(map(str, f['shock_actual_wicket_legal_n']))}, matching the brief. As delivery numbers, including wides and no-balls, they are {', '.join(map(str, f['shock_actual_wicket_innings_ball_num']))}. *(06_shock/shock_innings_timeline.csv)*")
(OUT / "11_presentation_summary").mkdir(exist_ok=True)
K.append(f"12. **Super overs are now included, at knockout occasion, and barely move the tables.** {f['ds_super_over_legal_balls_included']} legal balls in {f['ds_super_over_matches']} matches. Against the same pipeline without them: batters Spearman {abl('batter', 'exclude_super_overs', 'spearman_vs_full'):.4f}, top-20 overlap {int(abl('batter', 'exclude_super_overs', 'top20_overlap'))}/20; bowlers {abl('bowler', 'exclude_super_overs', 'spearman_vs_full'):.4f}, {int(abl('bowler', 'exclude_super_overs', 'top20_overlap'))}/20. None of the super-over balls reaches the high band ({pct(f['pro_super_over_share_in_batter_high_band'])} batter, {pct(f['pro_super_over_share_in_bowler_high_band'])} bowler), because shock and run of play start at zero in a new innings. *(02_pressure/super_over_pressure.csv, 08_validation/ablation_summary.csv)*")
(OUT / "11_presentation_summary/key_findings.md").write_text("\n".join(K), encoding="utf-8")
reg.note("11_presentation_summary/key_findings.md", "facts a-d", "generated text")

# ---------------------------------------------------------------- slide by slide
INT_COLS = {"rank", "legacy_rank", "legacy_rank_8term", "baseline_only_rank", "balls", "legal_balls", "players", "ranked", "top10_overlap", "top20_overlap"}


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
     "One section per slide. Status tags: **[C]** COMPUTED here, **[E]** EXISTING in the repository and reproduced, **[RD]** REQUIRES_DATA, **[RI]** REQUIRES_IMPLEMENTATION, **[NA]** NOT_APPLICABLE. Each section names its source files and charts. The model under audit is the current **7-term** version (Form removed, consistency 0.10). The 8-term version is shown only for comparison.\n"]
D.append("## Slide 1: Objective and scope\n")
D.append(f"- Rank T20 batters and bowlers on how they perform under pressure, using {num(f['ds_legal_balls_used_in_ratings'])} legal balls from {f['ds_first_match_date']} to {f['ds_last_match_date']}. [C]")
D.append(f"- {f['ranked_batters']} batters and {f['ranked_bowlers']} bowlers meet the ranking floor (n_eff ≥ 120 and high-band n_eff ≥ 30). [C]")
D.append("- The brief lists 8 weighted terms. The code has 7: Form was removed and consistency raised to 0.10. Form is [NA].\n")
D.append("## Slide 2: Data and cleaning\n")
D.append(f"- Deliveries: {num(f['ds_raw_deliveries_source_file'])}; none deleted; duplicate delivery keys {f['ds_duplicate_delivery_keys_match_innings_ballnum']}. [C]")
D.append(f"- Super overs included: {f['ds_super_over_deliveries_included']} deliveries, {f['ds_super_over_legal_balls_included']} legal balls, {f['ds_super_over_matches']} matches. [C]")
D.append(f"- Excluded from ball value: {num(f['ds_wides'])} wides, {f['ds_noballs']} no-balls, {f['ds_other_extras']} 'other' extras (treated as illegal). [C]")
D.append(f"- Legal balls used: **{num(f['ds_legal_balls_used_in_ratings'])}** in {f['ds_matches_with_legal_balls']} matches. IPL {num(f['ds_legal_IPL'])} ({f['ds_matches_IPL']} matches), T20I {num(f['ds_legal_T20I'])} ({f['ds_matches_T20I']}), Emerging/Rising {num(f['ds_legal_T20'])} ({f['ds_matches_T20']}, counted at weight 0.5). [C/E: matches exports/01_cleaning_funnel.csv]")
D.append(f"- Players who faced or bowled a legal ball: {f['ds_unique_batters_faced_legal_ball']} batters, {f['ds_unique_bowlers_bowled_legal_ball']} bowlers. [C]")
D.append(f"- Reduced matches: {f['dls_reduced_matches']}. Reduced chases with no supplied target: {f['dls_excluded_matches']}. DLS par: [RD].")
D.append("- Sources: `01_dataset/*.csv`. Charts: `10_charts/slide_02_dataset/`.\n")
D.append("## Slide 3: The pressure index\n")
D.append("- pressure = occasion × competition × ball difficulty + shock + run of play (see `02_pressure/pressure_formula_as_executed.csv`). [E]")
D.append(f"- Band cut-offs (p50 / p80): batters {g('pr_batter_p50')} / {g('pr_batter_p80')}; pace {g('pr_bowler_pace_p50')} / {g('pr_bowler_pace_p80')}; spin {g('pr_bowler_spin_p50')} / {g('pr_bowler_spin_p80')}. [C/E: match exports/08]")
D.append(f"- Actual batter band shares (zero / medium / high): {pct(f['pr_share_batter_all_zero'])} / {pct(f['pr_share_batter_all_medium'])} / {pct(f['pr_share_batter_all_high'])}, against a 50/30/20 design. [C]")
D.append("- Phase × arm (bowler high-band share):")
D.append(tbl(phase.assign(share_high=lambda d: (d["share_bowler_high"] * 100).map("{:.1f}%".format), share_of_arm_high=lambda d: (d["share_of_arm_high_band"] * 100).map("{:.1f}%".format)),
             ["arm", "phase", "legal_balls", "mean_pressure_bowl", "share_high", "share_of_arm_high", "economy_legal_balls"],
             ["arm", "phase", "legal balls", "mean bowler pressure", "% balls high", "% of arm's high balls", "economy (legal)"]))
D.append(f"- Variance of batter pressure: base {pct(f['pr_var_share_base_bat'])}, shock {pct(f['pr_var_share_shock_bat'])}, run of play {pct(f['pr_var_share_delta_bat'])}. [C]")
D.append("- Sources: `02_pressure/`. Charts: `10_charts/slide_03_pressure/`.\n")
D.append("## Slide 4: What 'high pressure' actually captures\n")
D.append(f"- {pct(f['se_share_of_batter_high_band_balls_within_6_after_wicket'], 2)} of batter high-band balls fall within 6 balls after a wicket. Away from those windows, the high band takes only {pct(f['se_batter_high_band_share_otherwise'], 3)} of balls. [C]")
D.append(f"- {pct(f['se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6'], 2)} of bowler high-band balls follow a four or six in the previous 6 (zero band: {pct(f['se_share_of_bowler_zero_band_balls_with_four_or_six_in_last_6'])}). [C]")
D.append(f"- Strike rate by batter band (zero / medium / high): {f['pr_sr_batter_all_zero']:.1f} / {f['pr_sr_batter_all_medium']:.1f} / {f['pr_sr_batter_all_high']:.1f}. Pace economy: {f['pr_econ_bowler_pace_zero']:.2f} / {f['pr_econ_bowler_pace_medium']:.2f} / {f['pr_econ_bowler_pace_high']:.2f}. Spin economy: {f['pr_econ_bowler_spin_zero']:.2f} / {f['pr_econ_bowler_spin_medium']:.2f} / {f['pr_econ_bowler_spin_high']:.2f} (legal balls). [C]")
D.append(f"- High-band share in balls 1–18: {pct(f['pro_share_of_balls_1_to_18_in_batter_high_band'], 2)}. In finals: {pct(f['pro_share_of_final_balls_in_batter_high_band'])}; in league games: {pct(f['pro_share_of_league_balls_in_batter_high_band'])}. [C]")
D.append(f"- Super overs ({f['pro_super_over_legal_balls']} legal balls) carry knockout occasion (mean {f['pro_super_over_mean_occasion']:.2f}) and mean batter pressure {f['pro_super_over_mean_pressure_bat']:.3f}, against {f['pro_knockout_match_mean_pressure_bat_excluding_super_overs']:.3f} for other knockout-match balls and {f['pro_death_overs_mean_pressure_bat_excluding_super_overs']:.3f} for other death balls. Yet {pct(f['pro_super_over_share_in_batter_high_band'])} of them reach the batter high band and {pct(f['pro_super_over_share_in_bowler_high_band'])} the bowler high band: shock and run of play start at zero in a new innings, and the highest super-over ball is {abs(f['pro_super_over_max_pressure_bat_vs_p80_cutoff']):.3f} below the high cut. [C] (`02_pressure/super_over_pressure.csv`, chart `slide_03_pressure/super_over_pressure.png`)")
D.append("- Charts: `10_charts/slide_04_high_pressure_meaning/`.\n")
D.append("## Slide 5: Expected runs and wickets (ball value)\n")
D.append("- Ball value: batter = (runs − xR) − 4 × (out − xW); bowler = (xR − charged) + 4 × (wicket − xW). Predictions use only earlier balls. [E]")
mm = met.loc[met["scope"].eq("all")].set_index(["model", "target"])
D.append(tbl(mm.reset_index().loc[lambda d: d["model"].isin(["xR", "xW"])], ["model", "target", "mean_predicted", "mean_actual", "mae", "rmse", "calibration_slope_ols", "calibration_intercept_ols", "calibration_slope_logistic", "calibration_intercept_logistic", "auc", "brier"],
             ["model", "target", "mean pred", "mean actual", "MAE", "RMSE", "OLS slope", "OLS intercept", "logit slope", "logit intercept", "AUC", "Brier"]))
D.append(f"- xR deciles: predicted {xr_all.loc[0, 'mean_predicted']:.3f} → {xr_all.loc[9, 'mean_predicted']:.3f}, actual {xr_all.loc[0, 'mean_actual']:.3f} → {xr_all.loc[9, 'mean_actual']:.3f}; the largest decile gap is {xr_all['actual_minus_predicted'].abs().max():.3f} runs per ball. [C/E: matches exports/14]")
D.append(f"- Wickets fallen, runs actual minus expected per ball: 0–1 down {g('wf_0-1_runs_resid')}, 8–9 down {g('wf_8-9_runs_resid')} (KI-03). [C]")
D.append("- Charts: `10_charts/slide_05_expectation_models/`.\n")
D.append("## Slide 6: Elo\n")
D.append(f"- Steps: 4 (runs), 16 (wicket), 20 (team), not halved. Final raw range: batters {g('elo_batter_elo_min', 1)}–{g('elo_batter_elo_max', 1)} (SD {g('elo_batter_elo_sd', 1)}); bowlers {g('elo_bowler_elo_min', 1)}–{g('elo_bowler_elo_max', 1)} (SD {g('elo_bowler_elo_sd', 1)}). Acceptance limits are 600–2800 and SD 250. [C/E: matches exports/12]")
st = elo_stab.loc[elo_stab["player_name"].isin(["Jos Buttler", "Virat Kohli", "David Miller", "Rilee Rossouw", "Jasprit Bumrah", "Rashid Khan", "Matthew Humphreys", "Corbin Bosch"]) & elo_stab["balls"].ge(30)]
st = st.loc[(st["skill"].eq("batter") & st["player_name"].isin(["Jos Buttler", "Virat Kohli", "David Miller", "Rilee Rossouw"])) | (st["skill"].eq("bowler") & st["player_name"].isin(["Jasprit Bumrah", "Rashid Khan", "Matthew Humphreys", "Corbin Bosch"]))]
D.append(tbl(st, ["player_name", "skill", "ladder", "balls", "final_raw", "min_raw", "max_raw", "largest_match_gain", "largest_match_loss"],
             ["player", "skill", "ladder", "balls", "final", "min", "max", "best match", "worst match"]))
D.append(f"- Year-over-year Spearman of season-end ratings (≥ 120 balls in both seasons): batters {g('elo_yoy_batter_2022', 2)}, {g('elo_yoy_batter_2023', 2)}, {g('elo_yoy_batter_2024', 2)}, {g('elo_yoy_batter_2025', 2)}; bowlers {g('elo_yoy_bowler_2022', 2)}, {g('elo_yoy_bowler_2023', 2)}, {g('elo_yoy_bowler_2024', 2)}, {g('elo_yoy_bowler_2025', 2)}. [C]")
D.append("- Elo shapes xR and xW. It is not a composite component. Charts: `10_charts/slide_06_elo/`.\n")
D.append("## Slide 7: Shock timeline, IPL 2025 final (PBKS chase)\n")
D.append(f"- {f['shock_match']}. Target {num(f['shock_target'])}; PBKS made {num(f['shock_innings_total'])}. Occasion multiplier {g('shock_occasion', 1)}. [C]")
D.append(f"- Wickets at legal balls {', '.join(map(str, f['shock_actual_wicket_legal_n']))}: **verified** against the brief. As delivery numbers including extras: {', '.join(map(str, f['shock_actual_wicket_innings_ball_num']))}. [C]")
D.append(f"- Batter high-band balls: {f['shock_high_band_balls_bat']}/120. Bowler high-band balls: {f['shock_high_band_balls_bowl']}/120. Peak batter pressure {g('shock_peak_pressure_bat', 2)} at ball {f['shock_peak_pressure_bat_n']}. Run of play on ball 19 = {g('shock_ball19_delta_bat', 2)} (batter) and {g('shock_ball19_delta_bowl', 2)} (bowler), pinned by BUG-01. [C]")
D.append("- Sources: `06_shock/`. Chart: `10_charts/slide_07_shock/ipl2025_final_shock_timeline.png`.\n")
D.append("## Slide 8: Components and weights\n")
D.append(tbl(infl.loc[infl["skill"].eq("batter")].merge(infl.loc[infl["skill"].eq("bowler"), ["component", "variance_share_of_composite", "effective_share"]], on="component", suffixes=("_bat", "_bowl")),
             ["label", "nominal_weight", "effective_share_bat", "variance_share_of_composite_bat", "effective_share_bowl", "variance_share_of_composite_bowl"],
             ["component", "weight", "effective share (bat)", "variance share (bat)", "effective share (bowl)", "variance share (bowl)"]))
D.append(f"- Form: [NA] in the current model (legacy weight 0.05). Composite among ranked players: batters mean {g('dist_batter_ranked_mean')}, SD {g('dist_batter_ranked_sd')}; bowlers mean {g('dist_bowler_ranked_mean')}, SD {g('dist_bowler_ranked_sd')}. [C]")
D.append("- Sources: `03_components/`, `08_validation/component_influence.csv`. Charts: `10_charts/slide_08_components/`.\n")
D.append("## Slide 9: Top batters\n")
D.append(tbl(fb.head(20), ["rank", "player_name", "role", "composite", "baseline", "band_high", "clutch", "peers", "legacy_rank", "n_eff", "high_n_eff"],
             ["rank", "player", "role", "composite", "baseline z", "high z", "clutch z", "peers z", "legacy rank", "n_eff", "high n_eff"]))
D.append(f"- Gap between rank 10 and 11: {g('dist_batter_gap_10_11', 4)}. [C]  Chart: `10_charts/slide_09_top_batters/`.\n")
D.append("## Slide 10: Top bowlers\n")
D.append(tbl(fw.head(20), ["rank", "player_name", "role", "composite", "baseline", "band_high", "clutch", "peers", "legacy_rank", "n_eff", "high_n_eff"],
             ["rank", "player", "arm", "composite", "baseline z", "high z", "clutch z", "peers z", "legacy rank", "n_eff", "high n_eff"]))
D.append(f"- Top 20 by arm: {f['rolerep_bowler_top20'][0]} pace, {f['rolerep_bowler_top20'][1]} spin. The ranked pool is {pct(f['role_bowler_Pace_share_pool'])} pace. [C]  Chart: `10_charts/slide_10_top_bowlers/`.\n")
D.append("## Slide 11: Sanity checks on named players\n")
D.append(tbl(sp, ["player_name", "skill", "role", "ranked", "rank", "composite", "legacy_rank_8term", "baseline_only_rank", "n_eff", "high_n_eff"],
             ["player", "skill", "role", "ranked", "rank", "composite", "legacy rank", "baseline-only rank", "n_eff", "high n_eff"]))
D.append("- Interpretations: `08_validation/sanity_check_interpretations.md`. Chart: `10_charts/slide_11_sanity_checks/`.\n")
D.append("## Slide 12: Ablation and robustness\n")
D.append(tbl(ab, ["skill", "variant", "spearman_vs_full", "kendall_tau_vs_full", "top10_overlap", "top20_overlap", "top10_jaccard", "top20_jaccard", "mean_abs_rank_change"],
             ["skill", "variant", "Spearman", "Kendall", "top-10 overlap", "top-20 overlap", "top-10 Jaccard", "top-20 Jaccard", "mean abs rank change"]))
D.append(f"- Sooryavanshi: official {f['abl_rank_Vaibhav Sooryavanshi_full_current']}, baseline only {f['abl_rank_Vaibhav Sooryavanshi_baseline_only']}, legacy {f['abl_rank_Vaibhav Sooryavanshi_legacy_8_term_with_form']}, pooled z {f['abl_rank_Vaibhav Sooryavanshi_no_role_split_pooled_z']}, without clutch {f['abl_rank_Vaibhav Sooryavanshi_drop_clutch']}. [C]")
D.append(f"- Gurbaz: official {f['abl_rank_Rahmanullah Gurbaz_full_current']}, baseline only {f['abl_rank_Rahmanullah Gurbaz_baseline_only']}, legacy {f['abl_rank_Rahmanullah Gurbaz_legacy_8_term_with_form']}, pooled z {f['abl_rank_Rahmanullah Gurbaz_no_role_split_pooled_z']}, without clutch {f['abl_rank_Rahmanullah Gurbaz_drop_clutch']}. [C]")
D.append(f"- Super overs: including them (the official run) against excluding them gives batters Spearman {abl('batter', 'exclude_super_overs', 'spearman_vs_full'):.4f} ({int(abl('batter', 'exclude_super_overs', 'top20_overlap'))}/20 top-20 overlap) and bowlers {abl('bowler', 'exclude_super_overs', 'spearman_vs_full'):.4f} ({int(abl('bowler', 'exclude_super_overs', 'top20_overlap'))}/20). Largest composite change: batters {f['noso_max_abs_composite_change_batter']:.3f}, bowlers {f['noso_max_abs_composite_change_bowler']:.3f}. Same ranked pool: {f['noso_same_ranked_set_batter'] and f['noso_same_ranked_set_bowler']}. Movers: `ablation_top_movers.csv` ('super overs included vs excluded'). [C]")
D.append(f"- The baseline-only and full ranks reproduce `exports/23_ablation_ranks.csv`: {f['export23_reproduced']}. [E]  Charts: `10_charts/slide_12_ablation/`.\n")
D.append("## Slide 13: Component correlations and influence\n")
D.append(f"- Batters: the most correlated pair is {f['corr_batters_max_pair'][0]}–{f['corr_batters_max_pair'][1]} ({f['corr_batters_max_pair'][2]:.3f}); the most negative is {f['corr_batters_min_pair'][0]}–{f['corr_batters_min_pair'][1]} ({f['corr_batters_min_pair'][2]:.3f}). High vs medium band {g('corr_batters_band_high_band_medium')}. [C]")
D.append(f"- Bowlers: most correlated {f['corr_bowlers_max_pair'][0]}–{f['corr_bowlers_max_pair'][1]} ({f['corr_bowlers_max_pair'][2]:.3f}); most negative {f['corr_bowlers_min_pair'][0]}–{f['corr_bowlers_min_pair'][1]} ({f['corr_bowlers_min_pair'][2]:.3f}). High band vs clutch {g('corr_bowlers_band_high_clutch')}. [C]")
D.append(f"- Largest variance share: batters {top_var_b.iloc[0]['label']} {pct(top_var_b.iloc[0]['variance_share_of_composite'])}; bowlers {top_var_w.iloc[0]['label']} {pct(top_var_w.iloc[0]['variance_share_of_composite'])}. Dropping the high band leaves {int(infl_get('batter', 'band_high', 'drop_one_top20_overlap'))}/20 batters and {int(infl_get('bowler', 'band_high', 'drop_one_top20_overlap'))}/20 bowlers in the top 20. [C]")
D.append("- Sources: `08_validation/component_correlation_*.csv`, `component_influence.csv`. Charts: `10_charts/slide_13_component_correlations/`.\n")
D.append("## Slide 14: Roles\n")
D.append(tbl(cov, ["skill", "role", "players", "n_eff_ge_30_reference", "ranked", "share_of_ranked_pool", "fail_n_eff_only", "fail_high_n_only"],
             ["skill", "role", "players", "reference (n_eff ≥ 30)", "ranked", "share of ranked pool", "fail n_eff only", "fail high-n only"]))
D.append(f"- Batting top 20 (top/middle/lower):")
D.append(f"  - current, role-split z: {f['rolerep_current_with_role_split_top20']}. **Verified 6/7/7.**")
D.append(f"  - current, pooled z: {f['rolerep_current_without_role_split_top20']}. **The brief's 12/5/3 does not reproduce for the current model.**")
D.append(f"  - legacy 8-term, role-split z: {f['rolerep_legacy_8term_with_role_split_top20']}.")
D.append(f"  - legacy 8-term, pooled z: {f['rolerep_legacy_8term_without_role_split_top20']}. **12/5/3 reproduces here.** [C]")
D.append(f"- Share of balls in the high band, ranked batters: top order {pct(f['role_highshare_batter_top order'])}, middle {pct(f['role_highshare_batter_middle order'])}, lower {pct(f['role_highshare_batter_lower order'])}. [C]  Charts: `10_charts/slide_14_roles/`.\n")
D.append("## Slide 15: Limitations and bugs\n")
for _, r in lim.iterrows():
    if r["category"].startswith(("BUG", "KNOWN")) or r["id"] in {"M-01", "M-02", "M-06", "M-07"}:
        D.append(f"- **{r['id']} {r['title']}** ({r['severity']}). {r['evidence']}")
D.append("- Full register: `09_limitations/limitations_register.csv`. Chart: `10_charts/slide_15_limitations/`.\n")
D.append("## Slide 16: Takeaways\n")
D.append("- See `key_findings.md`.")
D.append("- Not computed:")
D.append("  - DLS par analysis [RD].")
D.append("  - Uncertainty intervals for ranks [RI]. These need a bootstrap over matches, which is not in the pipeline.")
D.append("  - External validation against selections or awards [RD].")
(OUT / "11_presentation_summary/slide_by_slide_numbers.md").write_text("\n".join(D), encoding="utf-8")
reg.note("11_presentation_summary/slide_by_slide_numbers.md", "all section outputs", "generated text")
reg.close()

# ---------------------------------------------------------------- source traceability (after closing so it includes e)
traces = pd.concat([pd.read_csv(p) for p in sorted(CACHE.glob("trace_*.csv"))], ignore_index=True)
traces.insert(0, "kind", "output file")
head = [
    ("headline", "legal balls used", f["ds_legal_balls_used_in_ratings"], "01_dataset/cleaning_summary.csv", "legal_balls_used_in_ratings", "COMPUTED"),
    ("headline", "ranked batters / bowlers", f"{f['ranked_batters']} / {f['ranked_bowlers']}", "07_rankings/final_*_rankings.csv", "rows", "COMPUTED"),
    ("headline", "batter band p80", f["pr_batter_p80"], "02_pressure/pressure_band_summary.csv", "p80_cutoff", "COMPUTED"),
    ("headline", "pace band p80", f["pr_bowler_pace_p80"], "02_pressure/pressure_band_summary.csv", "p80_cutoff", "COMPUTED"),
    ("headline", "spin band p80", f["pr_bowler_spin_p80"], "02_pressure/pressure_band_summary.csv", "p80_cutoff", "COMPUTED"),
    ("headline", "batter high band within 6 balls of a wicket", f["se_share_of_batter_high_band_balls_within_6_after_wicket"], "06_shock/shock_event_summary.csv", "value", "COMPUTED"),
    ("headline", "bowler high band after a four/six", f["se_share_of_bowler_high_band_balls_with_four_or_six_in_last_6"], "06_shock/shock_event_summary.csv", "value", "COMPUTED"),
    ("headline", "Elo steps used", "4/16/20 (not halved)", "04_elo/elo_summary.csv", "step_sizes", "COMPUTED"),
    ("headline", "Elo batter min/max/sd", f"{f['elo_batter_elo_min']:.1f}/{f['elo_batter_elo_max']:.1f}/{f['elo_batter_elo_sd']:.1f}", "04_elo/elo_summary.csv", "value", "COMPUTED"),
    ("headline", "Elo bowler min/max/sd", f"{f['elo_bowler_elo_min']:.1f}/{f['elo_bowler_elo_max']:.1f}/{f['elo_bowler_elo_sd']:.1f}", "04_elo/elo_summary.csv", "value", "COMPUTED"),
    ("headline", "xR MAE/RMSE/slope/intercept", f"{f['xm_xR_bat_runs_mae']:.4f}/{f['xm_xR_bat_runs_rmse']:.4f}/{f['xm_xR_bat_runs_calibration_slope_ols']:.4f}/{f['xm_xR_bat_runs_calibration_intercept_ols']:.4f}", "05_expectation_models/expectation_model_metrics.csv", "scope=all", "COMPUTED"),
    ("headline", "xW AUC/Brier/logit slope/intercept", f"{f['xm_xW_bowler_wicket_auc']:.4f}/{f['xm_xW_bowler_wicket_brier']:.5f}/{f['xm_xW_bowler_wicket_calibration_slope_logistic']:.4f}/{f['xm_xW_bowler_wicket_calibration_intercept_logistic']:.4f}", "05_expectation_models/expectation_model_metrics.csv", "scope=all", "COMPUTED"),
    ("headline", "IPL 2025 final wickets (legal ball)", str(f["shock_actual_wicket_legal_n"]), "06_shock/shock_innings_timeline.csv", "is_wicket", "COMPUTED"),
    ("headline", "top-20 roles with split (current)", str(f["rolerep_current_with_role_split_top20"]), "08_validation/role_ranking_representation.csv", "top_k=20", "COMPUTED"),
    ("headline", "top-20 roles pooled (current)", str(f["rolerep_current_without_role_split_top20"]), "08_validation/role_ranking_representation.csv", "top_k=20", "COMPUTED"),
    ("headline", "top-20 roles pooled (legacy 8-term)", str(f["rolerep_legacy_8term_without_role_split_top20"]), "08_validation/role_ranking_representation.csv", "top_k=20", "COMPUTED"),
    ("headline", "Form weight (current)", "removed", "player_ratings.py", "weights block", "NOT_APPLICABLE"),
    ("headline", "DLS par / resources", "not in data", "01_dataset/dls_summary.csv", "", "REQUIRES_DATA"),
    ("headline", "rank uncertainty intervals", "not computed", "", "", "REQUIRES_IMPLEMENTATION"),
    ("headline", "external validation (selections/awards)", "no data", "", "", "REQUIRES_DATA"),
]
hd = pd.DataFrame(head, columns=["kind", "metric", "value", "output", "column_or_filter", "status"])
trace = pd.concat([hd, traces], ignore_index=True)
trace.to_csv(OUT / "11_presentation_summary/source_traceability.csv", index=False)
print("e done")
