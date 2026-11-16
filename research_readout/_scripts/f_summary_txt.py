"""Write RESEARCH_READOUT_SUMMARY.txt: every readout file, folder by folder, with what each CSV holds."""

from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1]
TARGET = OUT / "RESEARCH_READOUT_SUMMARY.txt"
FULL_ROWS = 70
FULL_BYTES = 16_000
SAMPLE_ROWS = 6

trace = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / "_cache" / "trace_*.csv")))], ignore_index=True)
trace = trace.drop_duplicates("output", keep="last").set_index("output")

FOLDERS = {
    "01_dataset": "Data cleaning and what enters the model: delivery counts, legal-ball rules, dismissal handling, cleaning assumptions, reduced (DLS) matches.",
    "02_pressure": "The pressure index as executed: formula, distribution, band cut-offs (zero/medium/high), phase x pace/spin breakdown, observations, and the super-over balls.",
    "03_components": "The seven composite components: definitions, distributions, every player's component scores and the intermediate values behind them, and weighted contributions.",
    "04_elo": "The ball-by-ball Elo walk that drives expected runs and wickets: bounds, per-ball histories for the named players, stability and step-size sensitivity.",
    "05_expectation_models": "Expected runs (xR) and expected wicket (xW) models: calibration by decile, accuracy metrics, ball-level predictions, and bias by wickets fallen.",
    "06_shock": "The shock term (last six balls) and a worked example: IPL 2025 final, PBKS chase (innings 2), ball by ball.",
    "07_rankings": "Final rankings: full ranked tables for batters and bowlers, top 10 and top 20, and the composite score distribution.",
    "08_validation": "Validation: named-player sanity checks, ablations (re-weighted and alternative rankings), component correlations and influence, role coverage and representation.",
    "09_limitations": "Bugs, known issues and methodological limitations, with evidence and impact; the methodological audit and cricketing interpretations.",
    "11_presentation_summary": "Presentation-ready numbers: slide-by-slide numbers (the main deliverable), key findings, and a traceability table linking each headline number to its source.",
    "12_model_fixes": "The November 2026 model fixes (BUG-01, pressure weighting, wickets-down expectation cell, high-band floor 60, legal-ball clutch basis, role blend): what changed, why, and every before / after number.",
}

DESC = {
    "01_dataset/cleaning_summary.csv": "One row per dataset metric (metric, value): raw vs silver delivery counts, super-over deliveries included, illegal deliveries by type, legal balls used, matches, innings, players, venues, balls and matches per ladder (IPL / T20I / T20) and per season and stage, missing-value counts, data anomalies, dead-rubber matches.",
    "01_dataset/delivery_classification.csv": "One row per extras label (ordinary, wide, no-ball, bye, leg-bye, penalty, other): how many deliveries, whether the ball is legal (counts as a ball faced / enters Elo and ball value), runs by type, and the rule for charging runs to the bowler.",
    "01_dataset/dismissal_classification.csv": "One row per dismissal type: counts (all, in super overs, used), on legal vs illegal deliveries, striker vs non-striker, and flags for whether it credits the bowler, penalises the batter, counts in the shock term and in xW training.",
    "01_dataset/cleaning_assumptions.csv": "Each cleaning / modelling assumption as implemented in code (legal ball, super overs, ball order, season, ladders, level weight, season decay, bowler wicket, extras charging, reduced matches, chase target, phases, roles), where it lives, and the evidence.",
    "01_dataset/dls_summary.csv": "Reduced-match (rain / DLS) metrics: reduced matches, with and without a revised target, chases excluded from the required-rate term, second-innings and super-over chase balls with a required rate. DLS par scores are not in the data (REQUIRES_DATA).",
    "02_pressure/pressure_summary.csv": "Distribution of every pressure ingredient (occasion, competition, ball difficulty, situation, count shock, excess shock, run of play, final batter and bowler pressure): mean, SD, percentiles, and each part's share of pressure variance (situation / shock / run of play after weighting).",
    "02_pressure/pressure_formula_as_executed.csv": "The pressure formula term by term, exactly as the code runs it: situation, shock and run of play each divided by its own SD and weighted 0.60 / 0.25 / 0.15, with the fitted scales and the code location.",
    "02_pressure/pressure_percentiles.csv": "Percentiles (p0..p100) of batter pressure, bowler pressure (all), pace-bowler pressure and spin-bowler pressure.",
    "02_pressure/pressure_band_summary.csv": "One row per scope (batter / pace bowler / spin bowler) x band (zero / medium / high): p50 and p80 cut-offs (and the existing export's values), ball counts and shares vs the 50/30/20 design, pressure range, and outcomes in that band (strike rate, dismissal and wicket rates, economy, boundary rate, mean ball value, share in death overs / chases / knockouts).",
    "02_pressure/phase_bowling_pressure.csv": "Phase (powerplay / middle / death) x arm (pace / spin): balls, mean ball difficulty and pressure, share of balls in each bowler band, economy and wicket rate, and each cell's share of that arm's high-band balls.",
    "02_pressure/pressure_observations.csv": "Derived facts about pressure (observation, value, notes): where high-band balls come from (death, chases, finals, super overs) now and before the fixes, cap and clip rates, correlations of pressure with outcomes, ball-19 evidence before and after the BUG-01 fix, super-over pressure vs knockout and death balls, replication checks.",
    "02_pressure/super_over_pressure.csv": "Every legal super-over ball (33): match, stage, innings (3 or 4), batter, bowler, outcome, and every pressure term (occasion, competition, ball difficulty, required rate, shock, run of play), resulting batter and bowler band, xR, xW and ball value.",
    "03_components/component_definitions.csv": "Each composite component: current weight and the 8-term (git 29956ed) weight, raw input, aggregation and weighting, shrinkage, z-score scope, and code location. Form is listed as NOT_APPLICABLE in the current model.",
    "03_components/component_summary.csv": "Distribution of each component z-score (mean, SD, quartiles, share at the +3 / -3 cap) for batters and bowlers, in the reference pool and among ranked players.",
    "03_components/batter_component_scores.csv": "Every batter (one row each): totals, n_eff, the seven component z-scores, composite, rank, plus every intermediate value behind them (expected and shrunk strike rate and average, band rates and balls, peer / clutch / consistency pre-z values and counts) and the 8-term legacy form z.",
    "03_components/bowler_component_scores.csv": "Every bowler: the same as the batter file, using economy, balls per wicket and bowler ball value.",
    "03_components/component_contributions.csv": "For each ranked player: each component's z-score and weighted contribution (weight x z) to the composite, the largest positive and negative component, and the pressure components' share of the positive contribution.",
    "04_elo/elo_summary.csv": "Elo walk metrics: step sizes (k_run, k_wicket, k_team), whether the halving fallback triggered (it did not), min / max / SD of final batter, bowler and team ratings, the acceptance bounds, grounds seen.",
    "04_elo/batter_elo_history.csv": "Ball-by-ball batting Elo history for the eight Elo-check players (Buttler, Kohli, Miller, Rossouw, and the batting records of Bumrah, Rashid, Humphreys and Bosch) in each ladder: ball outcome, xR, xW, ball value, rating before (raw and cold-start shrunk), rating after, and change.",
    "04_elo/bowler_elo_history.csv": "The same ball-by-ball bowling Elo history for those of the eight who bowl: Bumrah, Rashid, Humphreys, Bosch and Kohli.",
    "04_elo/elo_stability.csv": "Three blocks, told apart by which columns are filled: (1) per named player and ladder: final, min, max and range of rating, mean change per ball, biggest match gain and loss, season-end ratings; (2) season-to-season Pearson / Spearman of season-end ratings; (3) step-size sensitivity (half and double steps): Elo spread, whether it stays within bounds, and composite Spearman / top-20 overlap vs official.",
    "05_expectation_models/xruns_calibration_deciles.csv": "xR calibration: balls split into ten deciles of predicted runs; mean predicted vs actual runs per decile, for all balls and by ladder and phase (batter runs and bowler charged runs).",
    "05_expectation_models/xwickets_calibration_deciles.csv": "xW calibration: deciles of predicted wicket probability; mean predicted vs actual wicket rate (bowler wickets and striker dismissals), overall and by ladder and phase.",
    "05_expectation_models/expectation_model_metrics.csv": "Accuracy of xR and xW, overall and by scope, for the current model and the pre-fix model (scope all_pre_fix_model): bias, MAE, RMSE (vs a constant-mean baseline), OLS calibration slope and intercept, R-squared, Spearman, Brier, log loss, AUC, logistic calibration slope and intercept.",
    "05_expectation_models/residual_by_wickets_fallen.csv": "Wickets already down (0..9) x phase, for the current model (with the wickets-down cell) and the pre-fix model (column model; pre_fix rows are phase 'all' only): expected vs actual runs, wicket and dismissal rates, and mean batter and bowler ball value. Shows how far the KI-03 tail bias was removed.",
    "05_expectation_models/xruns_predictions.csv": "Every legal ball (about 192k rows): context, xR for the batter and the bowler, actual bat and charged runs, and ball value.",
    "05_expectation_models/xwickets_predictions.csv": "Every legal ball: context, wickets before, xW, actual bowler wicket and striker dismissal, dismissal type.",
    "06_shock/shock_parameters.csv": "Shock-term constants as executed: window length, count weights (wicket 0.33, dot 0.05, six 0.33, four 0.12), caps and clips, excess-term scales, run-of-play windows and scales.",
    "06_shock/shock_innings_timeline.csv": "IPL 2025 final, PBKS chase (innings 2), one row per legal ball: score, target, required rate, every pressure term (count shock, excess shock, final shock, run of play), pressure and band for batter and bowler, xR, xW, ball value. Wickets fall at legal balls 30, 51, 58, 73, 98, 100, 104.",
    "06_shock/shock_event_summary.csv": "Two blocks: (1) one row per wicket in that chase: who, how, score at fall, shock on the next ball, max shock over the next six, high-band balls in the next six; (2) dataset-wide metrics (metric, value), e.g. the share of high-band balls that fall within six balls of a wicket or follow a boundary.",
    "07_rankings/final_batter_rankings.csv": "All ranked batters (141) in rank order: totals, n_eff, high_n_eff, the seven component z-scores, composite, rank, each weighted contribution, the pre-fix model's rank, composite and high_n_eff with the rank change vs pre-fix, and the 8-term legacy rank, composite and form z.",
    "07_rankings/final_bowler_rankings.csv": "All ranked bowlers (143): the same layout as the batter file.",
    "07_rankings/top10_batters.csv": "The top 10 rows of final_batter_rankings.csv.",
    "07_rankings/top10_bowlers.csv": "The top 10 rows of final_bowler_rankings.csv.",
    "07_rankings/top20_batters.csv": "The top 20 rows of final_batter_rankings.csv.",
    "07_rankings/top20_bowlers.csv": "The top 20 rows of final_bowler_rankings.csv.",
    "07_rankings/composite_distribution.csv": "Composite score distribution (mean, SD, percentiles, skew, gaps between ranks 1-10, 10-11, 20-21) for batters and bowlers, plus histogram bins.",
    "08_validation/sanity_check_players.csv": "The 13 named sanity players (Buttler, Kohli, Miller, Bumrah, Rashid, Rossouw, Humphreys, Bosch, Dhoni, Tim David, Imad Wasim, Sooryavanshi, Gurbaz), 16 rows because some appear as both batter and bowler: ranked or why not, rank and percentile, composite and components, the pre-fix model's rank, pool, composite and high_n_eff, legacy, baseline-only, role-only-z, pooled-z and super-overs-excluded ranks, totals, final Elo per ladder.",
    "08_validation/sanity_check_interpretations.md": "Plain-language reading of each sanity player's result, and what the fixes changed for them (rank and largest component moves vs pre-fix).",
    "08_validation/ablation_summary.csv": "One row per (skill, variant): how far that alternative ranking is from the official one: Spearman, Kendall tau, mean / median / max rank change, top-10 / 20 / 50 overlap and Jaccard, and Sooryavanshi's and Gurbaz's ranks. Variants: baseline_only, pressure_only_bands_clutch, no_pressure_baseline_peers_consistency, equal_weights, drop_<component>, previous_model_before_fixes, exclude_super_overs, legacy_8_term_with_form_pre_fix_frame (vs the pre-fix model, isolates Form), pressure_weights_<w> and pressure_raw_sum_bug_fixed (other pressure weightings), role_blend_1_role_only_z and role_blend_0_pooled_z (batters).",
    "08_validation/pressure_weight_sensitivity.csv": "One row per pressure weighting (official 0.60/0.25/0.15, 40/35/25, 50/30/20, 70/20/10, equal thirds, raw sum with the bug fixed, and the pre-fix model): weights, how much of the high band follows a recent wicket or boundary (with base rates), high-band share of finals / league / death / powerplay / super-over balls, where pace high-band balls fall by phase, band agreement and ranking Spearman / top-20 overlap vs official.",
    "08_validation/ranking_floor_sensitivity.csv": "High-band n_eff floor 30 / 45 / 60 / 90 (60 is official), per skill: ranked count, top-10 players below 60 high n_eff, the smallest top-10 high n_eff, top-20 overlap with official, and the top 10.",
    "08_validation/ablation_batter_rank_changes.csv": "Every ranked batter's rank under each ablation variant (one column per variant; full_current is official).",
    "08_validation/ablation_bowler_rank_changes.csv": "The same for every ranked bowler.",
    "08_validation/ablation_top_movers.csv": "For the key comparisons (baseline only, the model before the fixes, role-only z, pooled z, super overs excluded): the ten biggest risers and fallers in the official model.",
    "08_validation/component_correlation_batters.csv": "Pearson and Spearman correlation matrices of the batter components, composite and legacy form, among ranked batters.",
    "08_validation/component_correlation_bowlers.csv": "The same for bowlers.",
    "08_validation/component_influence.csv": "How much each component actually drives the composite: nominal weight, SD among ranked players, effective weight (weight x SD) and its share, variance share, correlation with the composite, drop-one Spearman / top-20 overlap / rank change, and mean contribution in the top 20.",
    "08_validation/role_coverage.csv": "By role (top / middle / lower order; pace / spin): players, how many pass each floor (reference n_eff >= 30, n_eff >= 120, high n_eff >= 60), ranked counts and shares, and which floor fails.",
    "08_validation/role_ranking_representation.csv": "Role counts in the top 10 / 20 / 50 under each ranking, with names: current official blend 0.5, role-only z (blend 1), pooled z (blend 0), the pre-fix model with and without the role split, the legacy 8-term model with and without it, and bowlers by arm.",
    "08_validation/role_sample_distribution.csv": "Sample sizes by role (balls, n_eff, high n_eff): mean and quartiles, for all players and ranked players.",
    "08_validation/diagnostic_bowler_clutch_basis.csv": "BUG-03 (fixed) evidence, per bowler: career economy over all deliveries vs legal balls only, the economy clutch now compares against, the difference in pre-fix clutch-scale units, and current vs pre-fix clutch and rank.",
    "09_limitations/limitations_register.csv": "One row per issue: BUG-01..03 (bugs), KI-01..04 (known issues from the brief), M-01..19 (methodological, data and code-hygiene limitations; M-17..19 are new with the fixes): category, description, evidence with numbers, severity, affected outputs, status (FIXED / PARTLY FIXED / open), quantified impact, suggested follow-up.",
    "09_limitations/methodological_audit.md": "What the code actually executes, section by section (version, data, pressure, Elo, expectations, components, ablation, issues), with numbers.",
    "09_limitations/cricketing_interpretations.md": "What the results mean in cricket terms (marked as interpretation).",
    "11_presentation_summary/slide_by_slide_numbers.md": "MAIN DELIVERABLE: every number for each slide (1-16) with its status tag, source file and chart.",
    "11_presentation_summary/key_findings.md": "The 12 most important findings, in priority order, with source files.",
    "11_presentation_summary/source_traceability.csv": "Traceability: each headline number (and every output file) with value, source file, column or filter, status, source and method.",
    "12_model_fixes/fix_before_after.csv": "One row per before / after metric for each fix (finding, description, metric, before_fix, after_fix, source): ball-19 run of play, pressure variance shares and recent-event shares, expectation accuracy and the wickets-down residual, small-sample counts and ranked pools, clutch basis, role mix, ranking agreement.",
    "12_model_fixes/model_fixes.md": "What was changed, why, what moved, the rationale for normalising batters partly within roles, and how the pressure weights were chosen.",
}

GLOSSARY = """\
GLOSSARY OF COMMON COLUMNS AND TERMS
- ladder: IPL, T20I, or T20 (Emerging Teams / Rising Stars, weighted 0.5). Elo and expectations never mix ladders.
- legal ball: not a wide, no-ball or 'other' extra. Super overs ARE included (innings 3 and 4).
- n / legal_ball_n: legal-ball number within the innings. innings_ball_num: delivery number including illegal balls.
- phase: powerplay (first 30% of the innings), middle, death (last 20%). Every super-over ball is death.
- occasion: Final 3.0, Semi Final 2.0, Qualifier / Eliminator 1.5, Super 4 1.3, League 1.0, other bilateral 0.8, dead rubber 0.4. Super-over balls: max(stage, 1.5).
- competition: 0.7 for Emerging / Rising / Other T20, else 1.0.
- ball_bat / ball_bowl: ball difficulty (0..1) from phase, wickets down and required rate (rrr).
- shock_bat / shock_bowl: previous six balls (batter: wickets and dots; bowler: sixes and fours) plus the excess of wickets over xW (batter) or charged runs over xR (bowler); clipped to -0.5..1.
- delta / run_of_play: last 6 vs last 18 balls (batter: wickets; bowler: runs), scaled, clipped to -0.5..1. The ball-19 look-ahead bug (BUG-01) is fixed: before 18 balls the long window subtracts nothing.
- situation_bat / situation_bowl = occasion x competition x ball difficulty.
- pressure_bat / pressure_bowl = 0.60 x situation / SD(situation) + 0.25 x shock / SD(shock) + 0.15 x run of play / SD(run of play)  (PRESSURE_WEIGHTS in player_ratings.py; before the fixes it was the plain sum).
- band / band_bowl: zero (< p50), medium (p50..p80), high (>= p80). Batters are cut on all balls; bowlers separately within pace and within spin.
- x_runs (xR), x_runs_bowl, x_wicket (xW): expected bat runs, expected charged runs, expected wicket probability, using only earlier balls. The finest cell is ladder x phase x arm x wickets down (0-1, 2-3, 4-5, 6-7, 8+).
- e_bat = (runs - xR) - 4 x (out - xW); e_bowl = (xR_bowl - charged) + 4 x (wicket - xW). The ball value.
- n_eff: season-decayed (0.9 per year back from 2026), level-weighted legal balls. high_n_eff: the same in the high band.
- ranked: n_eff >= 120 (RANK_BALLS) and high_n_eff >= 60 (RANK_HIGH_BALLS; 30 before the fixes). rank: 1 = best, among ranked players only.
- components (z-scores capped at +/-3; bowlers pooled; a batter's z = 0.5 x z within top / middle / lower order + 0.5 x z across all batters, ROLE_BLEND): baseline 0.20, band_zero 0.10, band_medium 0.15, band_high 0.20, clutch 0.15, peers 0.10 (the same innings vs teammates and opposition), consistency 0.10. composite = the weighted sum. Bowler clutch compares high-band spell economy with career economy, both on legal balls.
- pre_fix_*: the model before the November 2026 fixes (research_readout/_scripts/reference/player_ratings_pre_fix.py), run in full on the same balls.
- legacy_*: the earlier 8-term model with Form 0.05 and consistency 0.05 (git 29956ed), scored on the pre-fix frame, so legacy vs pre-fix isolates the removal of Form.
- role: batters top / middle / lower order (modal batting position 1-3 / 4-6 / 7+); bowlers Pace / Spin.
- status: COMPUTED (calculated in this audit), EXISTING (already in the repository and reproduced), REQUIRES_DATA, REQUIRES_IMPLEMENTATION, NOT_APPLICABLE (Form).
"""


def table_text(frame: pd.DataFrame) -> str:
    return frame.round(4).to_csv(index=False).strip()


def describe_csv(rel: str) -> list[str]:
    path = OUT / rel
    frame = pd.read_csv(path, low_memory=False)
    lines = [f"--- {rel}", f"WHAT IT HAS: {DESC.get(rel, '(no description)')}"]
    lines.append(f"SHAPE: {len(frame):,} rows x {frame.shape[1]} columns; {path.stat().st_size / 1024:,.0f} KB")
    if rel in trace.index:
        t = trace.loc[rel]
        lines.append(f"SOURCE: {t['source']} | METHOD: {t['method']} | STATUS: {t['status']}")
    lines.append("COLUMNS: " + ", ".join(frame.columns))
    if len(frame) <= FULL_ROWS and path.stat().st_size <= FULL_BYTES:
        lines.append("FULL CONTENT:")
        lines.append(table_text(frame))
    else:
        lines.append(f"SAMPLE (first {SAMPLE_ROWS} of {len(frame):,} rows; open the file for the rest):")
        lines.append(table_text(frame.head(SAMPLE_ROWS)))
    return lines + [""]


def describe_md(rel: str) -> list[str]:
    path = OUT / rel
    return [f"--- {rel}", f"WHAT IT HAS: {DESC.get(rel, '(markdown report)')}", "FULL TEXT:", path.read_text(encoding="utf-8").strip(), ""]


out = ["SUPERR RESEARCH READOUT: SUMMARY OF EVERY FILE, FOLDER BY FOLDER",
       "=" * 70,
       "This file describes every output in research_readout/. For each CSV it gives what the file holds, its shape, its source, its columns, and the data itself: all of it for small tables, the first rows for large ones. Markdown reports are included in full.",
       "Project: a pressure-adjusted T20 rating of batters and bowlers (IPL 2022-2026, T20Is, Emerging / Rising Stars) from ball-by-ball data. Current model: 7 weighted components (Form removed), super overs included at knockout-level occasion, with the November 2026 fixes (ball-19 bug, weighted pressure index, wickets-down expectation cell, high-band floor 60, legal-ball clutch basis, 50/50 role blend for batters; see 12_model_fixes).",
       "", GLOSSARY, "README.md (full text):", (OUT / "README.md").read_text(encoding="utf-8").strip(), ""]

for folder, purpose in FOLDERS.items():
    out += ["", "=" * 70, f"FOLDER {folder}/", f"PURPOSE: {purpose}", "=" * 70, ""]
    for path in sorted((OUT / folder).iterdir()):
        rel = f"{folder}/{path.name}"
        if path.suffix == ".csv":
            out += describe_csv(rel)
        elif path.suffix == ".md":
            out += describe_md(rel)

out += ["", "=" * 70, "FOLDER 10_charts/", "PURPOSE: matplotlib PNG charts on a white background, one subfolder per slide. Images are not included in this text; file names below.", "=" * 70]
for path in sorted((OUT / "10_charts").rglob("*.png")):
    out.append(f"- {path.relative_to(OUT / '10_charts').as_posix()}")
out += ["", "Scripts that produced everything: research_readout/_scripts/ (run_pipeline.py, then a_ to e_; f_summary_txt.py writes this file)."]

TARGET.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote", TARGET, f"{TARGET.stat().st_size / 1024:,.0f} KB", len(out), "lines")
