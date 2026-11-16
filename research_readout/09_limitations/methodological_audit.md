# Methodological audit

This audit describes what the code in this repository executes, checked against the data. Where a number is given, it comes from a file in `research_readout/` (see `11_presentation_summary/source_traceability.csv`). The fixes made in November 2026 are listed in section 0 and measured in `12_model_fixes/`.

## 0. Version under audit

- `player_ratings.py`: **seven** weighted terms. Baseline 0.20, zero band 0.10, medium band 0.15, high band 0.20, clutch 0.15, peers 0.10, consistency 0.10. They sum to 1.00.
- Changes in this round, all in `player_ratings.py`:
  - BUG-01: the 18-ball run-of-play window no longer reads the innings total on legal ball 19.
  - Pressure: each term over its own SD, weighted 0.60 situation + 0.25 shock + 0.15 run of play (`PRESSURE_WEIGHTS`). Before, the three terms were added raw.
  - Expectation cells: the full cell adds wickets down (0-1, 2-3, 4-5, 6-7, 8+).
  - Batter z-scores: 0.5 within role + 0.5 against all batters (`ROLE_BLEND`). Before, within role only.
  - Ranking floor: high-band n_eff ≥ 60 (`RANK_HIGH_BALLS`, was 30); n_eff ≥ 120 unchanged.
  - Bowler clutch compares legal-ball spell economy with legal-ball career economy.
- The model before these fixes is kept at `research_readout/_scripts/reference/player_ratings_pre_fix.py` and run in full for every before/after number. The 8-term version with Form (git `29956ed`) is scored on the pre-fix frame, so legacy vs pre-fix isolates the Form change.
- Super overs are included: 38 deliveries, 33 legal balls, 6 matches, each ball a death ball at occasion max(stage, 1.5).
- Reproduction: the in-memory run reproduces the shipped `ratings/batters.csv` ranks: True. Ranked: 141 batters, 143 bowlers.

## 1. Data and cleaning

- 200,999 deliveries; none are deleted in cleaning. Duplicate delivery keys: 0.
- Excluded from ball value: 8,554 illegal deliveries (7,714 wides, 576 no-balls, 264 'other').
- Used: **192,445 legal balls** in 867 matches, 2022-01-22 to 2026-11-01. IPL 83,755 balls in 367 matches; T20I 101,960 in 470; T20 (Emerging/Rising) 6,730 in 30.
- Reduced matches: 34. Reduced chases with no supplied target get no required rate (2 matches). DLS par scores are not in the data (REQUIRES_DATA).

## 2. Pressure as executed

```
pressure = 0.60 x situation / sd(situation) + 0.25 x shock / sd(shock) + 0.15 x run_of_play / sd(run_of_play)
situation = occasion x competition x ball difficulty
```
  Computed separately for the batter and the bowler side; the SDs are population SDs over all legal balls (`02_pressure/pressure_formula_as_executed.csv`).
- Occasion: Final 3.0, Semi 2.0, Qualifier/Eliminator 1.5, Super 4 1.3, League 1.0, other bilateral 0.8, dead rubber 0.4 (40 matches). A super-over ball takes max(stage occasion, 1.5). Competition: 0.7 for Emerging/Rising, otherwise 1.0.
- Ball difficulty (clipped 0..1). Batter: phase term (PP 0.25, middle 0.10, death 0.40) + wickets term (2–4 down 0.15, 5+ down 0.30) + chase-rate term (RRR ≥ 8 adds 0.15, ≥ 12 adds 0.30). Bowler: phase term (PP 0.32, middle 0.24; death 0.32 to a top-7 batter, otherwise 0.14) + wickets term (−0.10 or −0.25) + the same rate term.
- Shock: a count part over the previous six legal balls (batter 0.33 per wicket + 0.05 per dot; bowler 0.33 per six + 0.12 per four) plus an excess part (batter: bowler wickets − xW; bowler: charged − xR), scaled by SDs of 0.5104 and 4.3778, clipped −0.5..1.
- Run of play: last 6 vs last 18 balls (wickets per ball for batters, bat runs per ball for bowlers), scaled by SDs of 0.0733 and 0.5928 (pre-fix, with BUG-01: 0.0830 and 1.1072), clipped −0.5..1.
- Replication: the readout recomputes every term independently; max gap against the pipeline is 6.2e-15.
- Final cut-offs: batter p50 0.820, p80 1.523. Pace p50 1.116, p80 1.688. Spin p50 0.932, p80 1.529.
- Variance shares of batter pressure (now / before): situation 68.7% / 7.1%, shock 20.8% / 51.8%, run of play 10.4% / 41.1%. Bowlers: 71.7% / 3.1%, 18.8% / 59.3%, 9.5% / 37.6%.
- **What the high band captures now.** 75.6% of batter high-band balls follow a wicket within six balls (before 99.9%; base rate 27.5%). 58.9% of death balls and 86.4% of final balls are batter-high. For bowlers the high band leans to the powerplay (M-17).

## 3. Expectation models and ball value

- Cells are ladder → phase → phase × arm → phase × arm × wickets down, each pulled toward the coarser level with 30 balls. Priors 1.0 run and 0.05 wickets. Every prediction uses only balls already bowled.
- The Elo gap is 0.15 × (batter − bowler)/400 + 0.05 × (side gap)/400 + 0.10 × (ground − 1500)/400. xR = cell mean × exp(gap), capped 0..6; xW = logistic(logit(cell rate) − gap), capped 0.002..0.40.
- Batter ball value = (bat runs − xR) − 4 × (striker out − xW). Bowler ball value = (xR_bowl − charged) + 4 × (bowler wicket − xW).
- xR: MAE 1.2986 (before 1.3043; constant 1.3282), RMSE 1.7284, OLS slope 0.922, R² 0.0159 (before 0.0133).
- xW against bowler wickets: AUC 0.5601 (before 0.5597), Brier 0.05026 vs 0.05041 constant, logistic slope 0.729. Discrimination stays weak (M-07).
- Runs actual minus expected at 8–9 down: -0.044 per ball (before -0.345); at 0–1 down 0.048 (before 0.084).

## 4. Elo

- Ratings start at 1500 per (player, ladder). Steps 4 / 16 / 20, not halved. Final raw ratings: batters 1043.2–2500.4 (SD 124.8); bowlers 1062.5–2082.6 (SD 113.2).
- Step-size sensitivity: composite Spearman 0.996 / 0.994 for batters, 0.994 / 0.990 for bowlers.

## 5. Components and composite

- **Baseline** (weight 0.20). Ranked batters: SD 0.901, variance share 29.1%. Ranked bowlers: SD 0.690, variance share 19.9%.
- **Zero pressure** (weight 0.10). Ranked batters: SD 0.928, variance share 4.3%. Ranked bowlers: SD 0.729, variance share 3.9%.
- **Medium pressure** (weight 0.15). Ranked batters: SD 0.950, variance share 10.2%. Ranked bowlers: SD 0.782, variance share 8.0%.
- **High pressure** (weight 0.20). Ranked batters: SD 0.952, variance share 27.2%. Ranked bowlers: SD 0.868, variance share 25.9%.
- **Clutch** (weight 0.15). Ranked batters: SD 1.213, variance share 21.2%. Ranked bowlers: SD 1.186, variance share 20.9%.
- **Peers** (weight 0.10). Ranked batters: SD 0.914, variance share 11.5%. Ranked bowlers: SD 0.981, variance share 13.5%.
- **Consistency** (weight 0.10). Ranked batters: SD 1.002, variance share -3.5%. Ranked bowlers: SD 0.900, variance share 8.0%.
- Batter z-scores: 0.5 × z within top/middle/lower order + 0.5 × z across all batters. Bowlers are z-scored across all bowlers; their bands are cut within pace and within spin.
- Why the role blend: Batters are compared partly within their batting role because the roles are different jobs. An opener faces the new ball with no wickets down and is judged on building an innings; a finisher arrives at the death, often after a collapse, and is judged on scoring fast against set bowlers. A strike rate or average is not comparable across those jobs without some adjustment. Pooling every batter rewards the role whose numbers are easiest to post. A role-only z-score assumes each role is equally deep in talent. Neither is a finding about cricket. The 50/50 blend (ROLE_BLEND = 0.5) is a stated compromise between the two.
- Eligibility: n_eff ≥ 120 and high-band n_eff ≥ 60, both decay- and level-weighted.

## 6. Robustness

- Batters, compared with the official ranking:
  - the model before the fixes: Spearman 0.845, top-20 overlap 9
  - baseline only: Spearman 0.782, top-20 overlap 10
  - equal weights: Spearman 0.979
  - raw-sum pressure with the bug fixed: Spearman 0.836, top-20 overlap 9
  - pressure_weights_40_35_25: Spearman 0.903, top-20 overlap 11
  - pressure_weights_50_30_20: Spearman 0.959, top-20 overlap 14
  - pressure_weights_70_20_10: Spearman 0.947, top-20 overlap 17
  - pressure_weights_equal_thirds: Spearman 0.861, top-20 overlap 8
  - role-only z: Spearman 0.991, top-20 overlap 18; pooled z: 0.990, 17
  - super overs excluded: Spearman 0.9999
- Bowlers, compared with the official ranking:
  - the model before the fixes: Spearman 0.785, top-20 overlap 12
  - baseline only: Spearman 0.662, top-20 overlap 10
  - equal weights: Spearman 0.981
  - raw-sum pressure with the bug fixed: Spearman 0.722, top-20 overlap 12
  - pressure_weights_40_35_25: Spearman 0.862, top-20 overlap 13
  - pressure_weights_50_30_20: Spearman 0.947, top-20 overlap 16
  - pressure_weights_70_20_10: Spearman 0.953, top-20 overlap 18
  - pressure_weights_equal_thirds: Spearman 0.838, top-20 overlap 14
  - super overs excluded: Spearman 0.9997

## 7. Issues

See `limitations_register.csv`. Fixed this round: BUG-01, BUG-03, KI-03, M-06; partly fixed: M-01. Open: BUG-02, KI-02, KI-04, M-07. New: M-17 (bowler high band leans to the powerplay). Modelling choices stated as such: M-18 (role blend), M-19 (pressure weights).