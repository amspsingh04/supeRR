# Key findings

Ordered by importance for the presentation. Every number links to a file in this pack.

1. **Six fixes went in, and the tables moved a lot.** Against the pre-fix model: batters Spearman 0.845, top-20 overlap 9/20; bowlers 0.785, 12/20. *(12_model_fixes)*
2. **The top of each table.** Batters: 1. Tim David, 2. Phil Salt, 3. Rinku Singh, 4. Donovan Ferreira, 5. Jos Buttler. Bowlers: 1. Mitchell Santner, 2. Shaheen Afridi, 3. Bhuvneshwar Kumar, 4. Abrar Ahmed, 5. Jasprit Bumrah. *(07_rankings)*
3. **'High pressure' now mostly means the match situation.** Situation explains 68.7% of batter pressure variance (before 7.1%). Recent wickets still lift the band: 75.6% of batter high-band balls follow one (before 99.9%; base rate 27.5%). Finals are 86.4% high (before 26.1%). *(02_pressure, 06_shock)*
4. **New side effect: the bowler high band leans to the powerplay.** 72.1% of pace high-band balls are in the powerplay and 10.5% at the death (before 35.5% and 28.4%). It comes from the bowler ball-difficulty table, which lowers death difficulty when wickets are down. *(M-17)*
5. **BUG-01 is fixed.** Ball 19 run of play: bowlers 1.000 → 0.251; the runs scale 1.1072 → 0.5928. *(09_limitations BUG-01)*
6. **The wickets-down cell removes most of the tail bias.** Runs above expectation at 8–9 down -0.345 → -0.044 per ball. Discrimination barely improves: xR R² 0.0133 → 0.0159, MAE 1.2986 vs 1.3282 constant, xW AUC 0.5601. *(05_expectation_models)*
7. **No thin pressure samples at the top.** The high-band floor is 60. Top-10 bowlers below 60: 4 → 0; the smallest top-10 bowler sample is 87.0. Ranked pools shrink: 141 batters, 143 bowlers. *(08_validation/ranking_floor_sensitivity.csv)*
8. **Role normalisation is a stated choice.** Top-20 batting mix: role-only 4/12/4, official 50/50 blend 6/10/4, pooled 8/9/3 (before the fixes: 6/7/7 vs 14/6/0). *(M-18, 08_validation/role_ranking_representation.csv)*
9. **Clutch now compares like with like.** On the current spells, 47.0% would beat the bowler's own rate on the old basis, 43.5% on legal balls. *(BUG-03)*
10. **The pressure layer still changes the ranking a lot.** Baseline-only vs full: 10/20 batters, 10/20 bowlers in common. Other pressure weights: batters Spearman 0.903–0.959, bowlers 0.862–0.953. *(08_validation/ablation_summary.csv, pressure_weight_sensitivity.csv)*
11. **Super overs now reach the high band** (90.9% batter, 100.0% bowler; none before) and still barely move the tables (Spearman 0.9999 / 0.9997 vs excluding them). *(02_pressure/super_over_pressure.csv)*
12. **Form removal, isolated on the pre-fix frame, mattered little**: Spearman 0.989 (batters), 0.991 (bowlers). Elo stays inside its bounds, steps not halved. *(08_validation, 04_elo)*