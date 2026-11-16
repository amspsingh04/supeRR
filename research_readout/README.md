# Research readout: data extraction and validation audit

This folder holds the audit of the SupeRR pressure-rating pipeline: extracted tables, newly computed statistics, charts and written findings. The readout scripts never write outside this folder. Every table here was produced by running `player_ratings.py`, as it stands in the working tree, in memory and reading its outputs.

**The model was fixed in November 2026.** The audit's findings were acted on at the user's request. `12_model_fixes/model_fixes.md` explains each change and `12_model_fixes/fix_before_after.csv` gives every before / after number.

| Finding | Change | Constant in `player_ratings.py` |
|---|---|---|
| BUG-01 ball-19 look-ahead | the 18-ball run-of-play window subtracts nothing before the innings has 18 balls | – |
| Pressure dominated by recent events | situation, shock and run of play are each divided by their own SD, then weighted 0.60 / 0.25 / 0.15 | `PRESSURE_WEIGHTS` |
| Wickets-fallen bias | the finest expectation cell adds wickets down (0-1, 2-3, 4-5, 6-7, 8+) | – |
| Small high-pressure samples | ranking floor on high-band n_eff raised from 30 to 60 | `RANK_HIGH_BALLS` |
| Bowler clutch delivery basis | career economy on legal balls, the same basis as the spell | – |
| Role normalisation | a batter's z-score is 0.5 within role + 0.5 across all batters | `ROLE_BLEND` |

"Before" or `pre_fix_*` everywhere in this folder means the model before these fixes. It is kept as `_scripts/reference/player_ratings_pre_fix.py` and run in full on the same balls.

**Super overs are included.** The data has 38 super-over deliveries (33 legal balls) in 6 matches, stored as innings 3 and 4.

- **Phase:** every super-over ball is a death ball.
- **Occasion:** max(stage occasion, 1.5), so a super over is never below knockout level, even in a dead rubber. A semi-final or final super over keeps 2.0 or 3.0.
- **Chase:** the second super over chases the first super over's total plus one.

`08_validation/ablation_summary.csv` compares the official run with the same pipeline run without super overs (`exclude_super_overs`).

## Version under audit

- **Official numbers use the current working tree.** It has seven weighted terms:

  | Term | Weight |
  |---|---|
  | Baseline | 0.20 |
  | Zero-pressure band | 0.10 |
  | Medium-pressure band | 0.15 |
  | High-pressure band | 0.20 |
  | Clutch | 0.15 |
  | Peers | 0.10 |
  | Consistency | 0.10 |

- **The brief describes eight terms** (Form 0.05, consistency 0.05). That is the version at git `29956ed`. Form was removed at the user's request, committed in `7af5382`, and is reported as **NOT_APPLICABLE**.
- **The 8-term scoring functions were re-run read-only from `29956ed`** on the pre-fix model's legal frame, so legacy vs pre-fix isolates the removal of Form. The commit is pinned in `run_pipeline.py`. It appears as `legacy_8_term_with_form_pre_fix_frame` and `legacy_*` columns.
- **The in-memory run reproduces the shipped `ratings/batters.csv` and `ratings/bowlers.csv` exactly**: max composite gap 0, identical ranks, 141 ranked batters and 143 ranked bowlers (216 and 226 before the fixes).

## Status labels

| Label | Meaning |
|---|---|
| COMPUTED | Calculated in this audit from the pipeline's frames |
| EXISTING | Already in the repository (code constant, export, or notebook) and reproduced here |
| REQUIRES_DATA | Cannot be computed from the supplied files (for example DLS par scores, external selections or awards) |
| REQUIRES_IMPLEMENTATION | Needs new modelling not done here (for example bootstrap rank intervals) |
| NOT_APPLICABLE | Not present in the current model (Form) |

Comparison runs (the pre-fix model, other pressure weights, other role blends, other floors) are alternatives. They never replace an official number.

## Layout

```
01_dataset/                 cleaning_summary, delivery_classification, dismissal_classification, cleaning_assumptions, dls_summary
02_pressure/                pressure_summary, pressure_percentiles, pressure_band_summary, phase_bowling_pressure, pressure_observations
                            + pressure_formula_as_executed.csv (formula with the executed scales and weights)
                            + super_over_pressure.csv (every legal super-over ball with its pressure terms)
03_components/              component_definitions, component_summary, batter_component_scores, bowler_component_scores, component_contributions
04_elo/                     elo_summary, batter_elo_history, bowler_elo_history, elo_stability
05_expectation_models/      xruns_calibration_deciles, xwickets_calibration_deciles, expectation_model_metrics, xruns_predictions, xwickets_predictions
                            + residual_by_wickets_fallen.csv (KI-03, current vs pre-fix)
06_shock/                   shock_parameters, shock_innings_timeline (IPL 2025 final, PBKS chase), shock_event_summary
07_rankings/                final_batter_rankings, final_bowler_rankings, top10_*, top20_*, composite_distribution
08_validation/              sanity_check_players, sanity_check_interpretations.md, ablation_summary, ablation_*_rank_changes, ablation_top_movers,
                            component_correlation_batters/bowlers, component_influence, role_coverage, role_ranking_representation, role_sample_distribution
                            + diagnostic_bowler_clutch_basis.csv (BUG-03)
                            + pressure_weight_sensitivity.csv, ranking_floor_sensitivity.csv
09_limitations/             limitations_register.csv, methodological_audit.md, cricketing_interpretations.md
10_charts/slide_XX_*/       matplotlib PNGs on a white background, one folder per slide
11_presentation_summary/    slide_by_slide_numbers.md (start here), key_findings.md, source_traceability.csv
12_model_fixes/             model_fixes.md, fix_before_after.csv
_scripts/                   the code that produced everything above (reference/ holds the pre-fix model)
_cache/                     pickled pipeline frames and per-script facts (git-ignored; rebuilt by run_pipeline.py)
```

## Reproduce

Run from `research_readout/_scripts/`:

```
python run_pipeline.py                 # player_ratings in memory, a no-super-over run, the pre-fix model, and the 8-term model from git 29956ed
python a_dataset_pressure.py           # 01, 02 (and the replication of the shock / run-of-play / pressure terms)
python b_components_elo_models.py      # 03, 04, 05 (includes the Elo step-size diagnostic)
python c_shock_rankings_validation.py  # 06, 07, 08 (pressure weight, floor and role-blend alternatives)
python d_charts.py                     # 10
python e_reports.py                    # 09, 11, 12, the interpretations markdown
python f_summary_txt.py                # RESEARCH_READOUT_SUMMARY.txt
```

The whole chain takes several minutes. The scripts write only inside `research_readout/`. Importing `player_ratings` lets Python refresh its own `__pycache__` bytecode; that is not source or data.

## Bugs and known issues

| ID | Issue | Status |
|---|---|---|
| BUG-01 | **Run-of-play look-ahead.** On legal ball 19 the 18-ball window subtracted the innings total (numpy index −1), which also inflated the scale used on every ball. | FIXED. Mean bowler run of play on ball 19 went from 1.000 to 0.251; the runs scale from 1.1072 to 0.5928. |
| BUG-02 | **Mislabelled export columns.** `exports/10_sample_innings_timeline.csv` columns `count_shock_*` hold the final shock (count plus excess). | Open; labels only. |
| BUG-03 | **Mismatched clutch basis.** Bowler clutch compared legal-ball spell economy with a career economy that included wide and no-ball runs. | FIXED. Both sides now use legal balls. |

Known issues KI-01 to KI-04 and methodological limitations M-01 to M-19 are in `09_limitations/limitations_register.csv`. KI-03 (no wickets-fallen feature) is fixed. Three limitations are new with the fixes: M-17 (the bowler high band now leans to the powerplay), M-18 (role blend is a modelling choice) and M-19 (pressure weights are a judgement). The expectation models still discriminate weakly between single balls (M-07, open).
