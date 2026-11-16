# Methodological audit

This audit describes what the code in this repository actually executes, checked against the data. Nothing in the repository was changed. Where a number is given, it comes from a file in `research_readout/` (see `11_presentation_summary/source_traceability.csv`).

## 0. Version under audit

- Working tree `player_ratings.py`: **seven** weighted terms. Baseline 0.20, zero band 0.10, medium band 0.15, high band 0.20, clutch 0.15, peers 0.10, consistency 0.10. They sum to 1.00.
- The brief describes **eight** terms, with Form 0.05 and consistency 0.05. That is the version at git `29956ed`. Form was removed at the user's request (committed in 7af5382), and consistency was raised to 0.10.
- Super overs are **included** (changed in this session at the user's request; every commit up to 7af5382 drops them). 38 deliveries, 33 legal balls, 6 matches. Every super-over ball is a death ball, its occasion is max(stage occasion, 1.5) so it is never below a knockout, and the second super over chases the first super over's total + 1.
- All official numbers in this pack come from the working tree. The 8-term version's scoring functions were re-run read-only from git 29956ed on the same legal frame (super overs included), so the comparison isolates the Form change. It is reported as `legacy_8_term_with_form` wherever a comparison helps. Form is marked NOT_APPLICABLE for the current model.
- Reproduction: the in-memory run reproduces the shipped `ratings/batters.csv` and `ratings/bowlers.csv` exactly (max composite gap 2e-16, identical ranks). Ranked: 216 batters, 226 bowlers.

## 1. Data and cleaning

- 200,999 deliveries; none are deleted in cleaning. Duplicate delivery keys: 0.
- Super overs are kept: 38 deliveries (33 legal balls) in 6 matches.
- Excluded from ball value: 8,554 illegal deliveries (7,714 wides, 576 no-balls, 264 'other').
- Used: **192,445 legal balls** in 867 matches, 2022-01-22 to 2026-11-01. Ladders: IPL 83,755 balls in 367 matches; T20I 101,960 in 470; T20 (Emerging/Rising) 6,730 in 30.
- Dismissals: bowler wickets are caught, bowled, LBW, stumped and hit wicket. Run outs (600 used), retired out and obstructing do not credit the bowler.
- Reduced matches: 34. Reduced chases with no supplied target get no required rate (2 matches). DLS par scores are not in the data (REQUIRES_DATA).

## 2. Pressure as executed

```
pressure_bat  = occasion x competition x ball_bat  + shock_bat  + run_of_play_bat
pressure_bowl = occasion x competition x ball_bowl + shock_bowl + run_of_play_bowl
```
- Occasion: Final 3.0, Semi 2.0, Qualifier/Eliminator 1.5, Super 4 1.3, League 1.0, other bilateral 0.8, dead rubber 0.4 (40 matches). A super-over ball takes max(stage occasion, 1.5), even in a dead rubber. Competition: 0.7 for Emerging/Rising, otherwise 1.0.
- Ball difficulty (clipped 0..1). Batter: phase term (PP 0.25, middle 0.10, death 0.40), plus a wickets term (2–4 down 0.15, 5+ down 0.30), plus a chase-rate term (RRR ≥ 8 adds 0.15, RRR ≥ 12 adds 0.30). Bowler: phase term (PP 0.32, middle 0.24; death 0.32 to a recognised batter, otherwise 0.14), plus a wickets term (−0.10 or −0.25), plus the same rate term.
- Shock has two parts, added together and clipped to −0.5..1.
  - A count part over the previous six legal balls. Batter: 0.33 per wicket plus 0.05 per dot. Bowler: 0.33 per six plus 0.12 per four.
  - An excess part, scaled by SDs of 0.5111 (wickets) and 4.4173 (runs). Batter: the sum of (bowler wicket − xW). Bowler: the sum of (charged − xR).
- Run of play compares the last 6 balls with the last 18: wickets per ball for batters, bat runs per ball for bowlers. It is scaled by SDs of 0.0830 and 1.1072, and clipped to −0.5..1. **The executed scale includes the ball-19 bug (BUG-01).**
- Bands are recut after the Elo walk, once the excess shock is added. They agree with the pre-Elo bands on 88.5% of balls.
- Final cut-offs: batter p50 -0.050, p80 1.919. Pace bowlers p50 0.320, p80 1.446. Spin bowlers p50 0.241, p80 1.459. These match `exports/08_band_cutoffs.csv`.
- Variance decomposition of batter pressure: base term 7.1%, shock 51.8%, run of play 41.1%. For bowlers: 3.1%, 59.3%, 37.6%.
- **What the high band captures.** 99.94% of batter high-band balls lie within six balls after a wicket. 99.98% of bowler high-band balls follow a four or six in the previous six balls (M-01). Balls 1–18 are high for batters only 0.04% of the time (M-02).

## 3. Expectation models and ball value

- Cells are ladder → phase → phase × arm, each pulled toward the coarser level with 30 balls. The priors are 1.0 run and 0.05 wickets. Every prediction uses only balls already bowled, in date, match, innings and ball order, so there is no look-ahead in xR or xW.
- The Elo gap is 0.15 × (batter − bowler)/400 + 0.05 × (side gap)/400 + 0.10 × (ground − 1500)/400. It gives xR = cell mean × exp(gap), capped 0..6, and xW = logistic(logit(cell rate) − gap), capped 0.002..0.40.
- Batter ball value = (bat runs − xR) − 4 × (striker out − xW). Bowler ball value = (xR_bowl − charged) + 4 × (bowler wicket − xW).
- xR: mean predicted 1.3805 against mean actual 1.3941. MAE 1.3043, RMSE 1.7305, OLS calibration slope 0.985, intercept 0.035, R² 0.0133.
- xW against bowler wickets: mean 5.13% predicted, 5.32% actual. AUC 0.560, Brier 0.05025, logistic slope 0.811, intercept -0.506.
- xW against striker out: actual 5.49%, AUC 0.566 (KI-02).
- Wickets down are not a feature (KI-03). Runs actual minus expected falls from 0.084 per ball at 0–1 down to -0.345 at 8–9 down.

## 4. Elo

- Ratings start at 1500 and are kept per (player, ladder). Steps used: runs 4, wicket 16, team 20. The fallback that halves them to 2/8/10 was **not** triggered: final spreads are inside the 600–2800 / SD 250 acceptance window.
- Final raw ratings: batters 931.5–2571.6 (SD 141.8); bowlers 1059.8–2136.6 (SD 118.0); teams 1361.5–1647.1.
- A new player's rating is pulled toward 1500 until they have about 30 balls. Ground ratings are shrunk with 2,400 balls; 97 grounds are seen.
- Diagnostic step-size sensitivity, re-running with half and with double steps: composite Spearman is 0.996 and 0.994 for batters, 0.991 and 0.984 for bowlers.

## 5. Components and composite

- **Baseline** (weight 0.20). Ranked batters: SD 0.905, at the ±3 cap 0.0%, variance share 30.0%. Ranked bowlers: SD 0.720, at the cap 0.0%, variance share 20.4%.
- **Zero pressure** (weight 0.10). Ranked batters: SD 0.926, at the ±3 cap 0.5%, variance share 7.3%. Ranked bowlers: SD 0.827, at the cap 0.0%, variance share 5.1%.
- **Medium pressure** (weight 0.15). Ranked batters: SD 1.004, at the ±3 cap 0.9%, variance share 18.4%. Ranked bowlers: SD 0.868, at the cap 0.4%, variance share 7.8%.
- **High pressure** (weight 0.20). Ranked batters: SD 0.935, at the ±3 cap 0.5%, variance share 23.7%. Ranked bowlers: SD 0.978, at the cap 0.4%, variance share 27.7%.
- **Clutch** (weight 0.15). Ranked batters: SD 1.092, at the ±3 cap 3.7%, variance share 10.9%. Ranked bowlers: SD 1.225, at the cap 2.7%, variance share 19.4%.
- **Peers** (weight 0.10). Ranked batters: SD 0.959, at the ±3 cap 1.4%, variance share 13.7%. Ranked bowlers: SD 0.989, at the cap 0.9%, variance share 11.6%.
- **Consistency** (weight 0.10). Ranked batters: SD 1.019, at the ±3 cap 1.4%, variance share -4.1%. Ranked bowlers: SD 0.963, at the cap 0.9%, variance share 8.0%.
- Batters are z-scored within top, middle and lower order. Bowlers are z-scored across all bowlers, even though their bands are cut within pace and within spin.
- Eligibility: n_eff ≥ 120 and high-band n_eff ≥ 30, both decay- and level-weighted.

## 6. Robustness

- Batters, compared with the official ranking:
  - baseline only: Spearman 0.806, top-20 overlap 7
  - pressure only: Spearman 0.910, top-20 overlap 14
  - equal weights: Spearman 0.980
  - legacy 8-term model: Spearman 0.989
  - ball-19 bug removed (diagnostic): Spearman 0.998, top-20 overlap 20
  - super overs excluded (the earlier pipeline): Spearman 0.9998, top-20 overlap 20
- Bowlers, compared with the official ranking:
  - baseline only: Spearman 0.698, top-20 overlap 11
  - pressure only: Spearman 0.897, top-20 overlap 12
  - equal weights: Spearman 0.982
  - legacy 8-term model: Spearman 0.991
  - ball-19 bug removed (diagnostic): Spearman 0.958, top-20 overlap 14
  - super overs excluded (the earlier pipeline): Spearman 0.9998, top-20 overlap 19

## 7. Issues

See `limitations_register.csv`. Bugs: BUG-01 (the ball-19 run-of-play index), BUG-02 (an export label), and BUG-03 (the delivery basis of bowler clutch). Known issues: KI-01 (resolved by removing Form), KI-02, KI-03 and KI-04, all verified with numbers.