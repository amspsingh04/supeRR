# Research readout: data extraction and validation audit

This folder holds the audit of the SupeRR pressure-rating pipeline: extracted tables, newly computed statistics, charts and written findings. **No repository source file or data file was modified.** Every table here was produced by running the existing code in memory (`player_ratings.py` as it stands in the working tree) and reading its outputs.

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

- **The brief describes eight terms** (Form 0.05, consistency 0.05). That is the version committed at git HEAD `29956ed`. Form was removed in the previous session at the user's request. Form is therefore reported as **NOT_APPLICABLE**.
- **The 8-term model was re-run read-only from git HEAD** on the same data. It appears as `legacy_8_term_with_form` wherever a comparison is useful, for example the 12/5/3 role split, which reproduces only there.
- **The in-memory run reproduces the shipped `ratings/batters.csv` and `ratings/bowlers.csv` exactly**: max composite gap 2e-16, identical ranks, 216 ranked batters and 226 ranked bowlers.

## Status labels

| Label | Meaning |
|---|---|
| COMPUTED | Calculated in this audit from the pipeline's frames |
| EXISTING | Already in the repository (code constant, export, or notebook) and reproduced here |
| REQUIRES_DATA | Cannot be computed from the supplied files (for example DLS par scores, external selections or awards) |
| REQUIRES_IMPLEMENTATION | Needs new modelling that the brief forbids adding (for example bootstrap rank intervals) |
| NOT_APPLICABLE | Not present in the current model (Form) |

Diagnostics that show the size of a documented bug, such as `diagnostic_runofplay_bugfree`, are labelled as diagnostics. They never replace an official number.

## Layout

```
01_dataset/                 cleaning_summary, delivery_classification, dismissal_classification, cleaning_assumptions, dls_summary
02_pressure/                pressure_summary, pressure_percentiles, pressure_band_summary, phase_bowling_pressure, pressure_observations
                            + pressure_formula_as_executed.csv (extra: formula with the executed scales)
03_components/              component_definitions, component_summary, batter_component_scores, bowler_component_scores, component_contributions
04_elo/                     elo_summary, batter_elo_history, bowler_elo_history, elo_stability
05_expectation_models/      xruns_calibration_deciles, xwickets_calibration_deciles, expectation_model_metrics, xruns_predictions, xwickets_predictions
                            + residual_by_wickets_fallen.csv (extra: known issue KI-03)
06_shock/                   shock_parameters, shock_innings_timeline (IPL 2025 final, PBKS chase), shock_event_summary
07_rankings/                final_batter_rankings, final_bowler_rankings, top10_*, top20_*, composite_distribution
08_validation/              sanity_check_players, sanity_check_interpretations.md, ablation_summary, ablation_*_rank_changes, ablation_top_movers,
                            component_correlation_batters/bowlers, component_influence, role_coverage, role_ranking_representation, role_sample_distribution
                            + diagnostic_bowler_clutch_basis.csv (extra: BUG-03)
09_limitations/             limitations_register.csv, methodological_audit.md, cricketing_interpretations.md
10_charts/slide_XX_*/       matplotlib PNGs on a white background, one folder per slide
11_presentation_summary/    slide_by_slide_numbers.md (start here), key_findings.md, source_traceability.csv
_scripts/                   the code that produced everything above
_cache/                     pickled pipeline frames and per-script facts (git-ignored; rebuilt by run_pipeline.py)
```

## Reproduce

Run from `research_readout/_scripts/`:

```
python run_pipeline.py                 # runs player_ratings in memory; also loads the 8-term model from git HEAD
python a_dataset_pressure.py           # 01, 02 (and the replication of the shock / run-of-play terms)
python b_components_elo_models.py      # 03, 04, 05 (includes the Elo step-size diagnostic)
python c_shock_rankings_validation.py  # 06, 07, 08 (includes the ball-19 bug-free diagnostic)
python d_charts.py                     # 10
python e_reports.py                    # 09, 11, the interpretations markdown
```

The whole chain takes about four minutes. The scripts write only inside `research_readout/`. Importing `player_ratings` lets Python refresh its own `__pycache__` bytecode; that is not source or data.

## Bugs found (documented, not fixed)

| ID | Issue | Impact |
|---|---|---|
| BUG-01 | **Run-of-play index bug.** On legal ball 19 the 18-ball window subtracts the innings total (numpy index −1), which also inflates the scale used on every ball. | Diagnostic fix moves bowlers: Spearman 0.958, 14/20 top-20 overlap. Batters barely move: 0.998, 20/20. |
| BUG-02 | **Mislabelled export columns.** `exports/10_sample_innings_timeline.csv` columns `count_shock_*` actually hold the final shock (count plus excess). | Labels only. |
| BUG-03 | **Mismatched clutch basis.** Bowler clutch compares legal-ball spell economy, which has no wide or no-ball runs, with a career economy that includes them. | Average offset 0.369 runs per over (0.107 scale units) for ranked bowlers. |

Known issues KI-01 to KI-04 (Form look-ahead, xWicket and run outs, no wickets-fallen feature, wide and no-ball charging) are verified with numbers in `09_limitations/limitations_register.csv`.
