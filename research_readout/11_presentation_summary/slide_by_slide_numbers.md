# Slide-by-slide numbers

One section per slide. Status tags: **[C]** COMPUTED here, **[E]** EXISTING in the repository and reproduced, **[RD]** REQUIRES_DATA, **[RI]** REQUIRES_IMPLEMENTATION, **[NA]** NOT_APPLICABLE. The model is the current **7-term** version after the November fixes; 'before' means the pre-fix model (`12_model_fixes/`).

## Slide 1: Objective and scope

- Rank T20 batters and bowlers on how they perform under pressure, using 192,445 legal balls from 2022-01-22 to 2026-11-01. [C]
- 141 batters and 143 bowlers meet the ranking floor (n_eff ≥ 120 and high-band n_eff ≥ 60). Before the fixes: 216 and 226 at a floor of 30. [C]
- 7 weighted terms; Form removed [NA].

## Slide 2: Data and cleaning

- Deliveries: 200,999; none deleted. Super overs included: 38 deliveries, 33 legal balls, 6 matches. [C]
- Excluded from ball value: 7,714 wides, 576 no-balls, 264 'other'. Legal balls used: **192,445** in 867 matches. [C]
- Sources: `01_dataset/*.csv`. Charts: `10_charts/slide_02_dataset/`.

## Slide 3: The pressure index

- pressure = 0.60 situation + 0.25 shock + 0.15 run of play, each term over its own SD; situation = occasion × competition × ball difficulty (`02_pressure/pressure_formula_as_executed.csv`). Before the fix the three terms were added raw. [E]
- Band cut-offs (p50 / p80): batters 0.820 / 1.523; pace 1.116 / 1.688; spin 0.932 / 1.529. [C]
- Variance of batter pressure: situation 68.7%, shock 20.8%, run of play 10.4% (before 7.1% / 51.8% / 41.1%). [C]
- Phase × arm (bowler high-band share):
| arm | phase | legal balls | mean bowler pressure | % balls high | % of arm's high balls | economy (legal) |
|---|---|---|---|---|---|---|
| Pace | powerplay | 48503 | 1.488 | 34.9% | 72.1% | 8.171 |
| Pace | middle | 40885 | 0.883 | 10.0% | 17.4% | 8.528 |
| Pace | death | 27836 | 0.786 | 8.8% | 10.5% | 9.896 |
| Spin | powerplay | 12336 | 1.458 | 43.3% | 35.5% | 7.965 |
| Spin | middle | 57896 | 0.881 | 15.6% | 60.1% | 7.683 |
| Spin | death | 4989 | 0.766 | 13.3% | 4.4% | 9.258 |
- Pace high-band balls by phase before the fix: powerplay 35.5%, middle 36.2%, death 28.4% (M-17). [C]
- Sources: `02_pressure/`. Charts: `10_charts/slide_03_pressure/`.

## Slide 4: What 'high pressure' captures

- Batter high-band balls within 6 after a wicket: 75.6% (before 99.9%; base rate 27.5%). [C]
- Bowler high-band balls after a four or six in the previous 6: 86.7% (before 100.0%; base rate 63.6%). [C]
- Batter high band by context, now (before): finals 86.4% (26.1%), league 20.3% (21.3%), death 58.9% (33.6%), powerplay 10.9% (11.6%), super overs 90.9% (0.0%). [C]
- Strike rate by batter band (zero / medium / high): 142.6 / 138.7 / 132.8. Pace economy: 8.46 / 8.75 / 9.25. Spin: 7.26 / 8.23 / 8.68. [C]
- Pressure-weight sensitivity:
| variant | % batter high after wicket | % bowler high after boundary | % final balls high | % pace high at death | Spearman bat | Spearman bowl |
|---|---|---|---|---|---|---|
| pre_fix_model (raw sum, ball-19 bug) | 99.9 | 100.0 | 26.1 | 28.4 | 0.845 | 0.785 |
| official | 75.6 | 86.7 | 86.4 | 10.5 | – | – |
| pressure_weights_40_35_25 | 96.3 | 97.5 | 54.0 | 18.3 | 0.903 | 0.862 |
| pressure_weights_50_30_20 | 88.3 | 89.9 | 63.5 | 14.3 | 0.959 | 0.947 |
| pressure_weights_70_20_10 | 63.1 | 79.1 | 86.4 | 10.8 | 0.947 | 0.953 |
| pressure_weights_equal_thirds | 98.4 | 98.0 | 47.2 | 20.1 | 0.861 | 0.838 |
| pressure_raw_sum_bug_fixed | 99.9 | 100.0 | 26.0 | 29.9 | 0.836 | 0.722 |
- Charts: `10_charts/slide_04_high_pressure_meaning/`.

## Slide 5: Expected runs and wickets (ball value)

- Ball value: batter = (runs − xR) − 4 × (out − xW); bowler = (xR − charged) + 4 × (wicket − xW). Cells now include wickets down. Predictions use only earlier balls. [E]
| scope | model | target | mean pred | mean actual | MAE | MAE constant | R² | OLS slope | logit slope | AUC | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | xR | bat_runs | 1.375 | 1.394 | 1.299 | 1.328 | 0.016 | 0.922 | – | – | – |
| all | xW | bowler_wicket | 0.051 | 0.053 | 0.099 | 0.101 | – | – | 0.729 | 0.560 | 0.050 |
| all | xW | striker_out | 0.051 | 0.055 | 0.100 | 0.104 | – | – | 0.798 | 0.566 | 0.052 |
| all_pre_fix_model | xR | bat_runs | 1.381 | 1.394 | 1.304 | 1.328 | 0.013 | 0.985 | – | – | – |
| all_pre_fix_model | xW | bowler_wicket | 0.051 | 0.053 | 0.099 | 0.101 | – | – | 0.811 | 0.560 | 0.050 |
| all_pre_fix_model | xW | striker_out | 0.051 | 0.055 | 0.100 | 0.104 | – | – | 0.891 | 0.566 | 0.052 |
- Runs minus xR per ball by wickets down, before → now: 0–1 0.084 → 0.048, 8–9 -0.345 → -0.044. [C]
- Charts: `10_charts/slide_05_expectation_models/`.

## Slide 6: Elo

- Steps 4 / 16 / 20, not halved. Final raw range: batters 1043.2–2500.4 (SD 124.8); bowlers 1062.5–2082.6 (SD 113.2). [C]
| player | skill | ladder | balls | final | min | max |
|---|---|---|---|---|---|---|
| David Miller | batter | IPL | 908 | 1,500.7 | 1,437.9 | 1,674.7 |
| David Miller | batter | T20I | 365 | 1,826.2 | 1,495.2 | 1,874.7 |
| Jos Buttler | batter | IPL | 1,784 | 1,639.1 | 1,467.3 | 1,961.1 |
| Jos Buttler | batter | T20I | 1,036 | 2,134.7 | 1,460.2 | 2,136.2 |
| Rilee Rossouw | batter | IPL | 255 | 1,705.3 | 1,464.5 | 1,736.7 |
| Rilee Rossouw | batter | T20I | 160 | 1,749.9 | 1,468.0 | 1,774.1 |
| Virat Kohli | batter | IPL | 2,090 | 1,820.0 | 1,327.0 | 1,872.6 |
| Virat Kohli | batter | T20I | 364 | 1,635.4 | 1,488.8 | 1,722.1 |
| Corbin Bosch | bowler | IPL | 163 | 1,551.5 | 1,421.2 | 1,608.9 |
| Corbin Bosch | bowler | T20I | 204 | 1,749.3 | 1,408.1 | 1,801.0 |
| Jasprit Bumrah | bowler | IPL | 1,209 | 2,082.6 | 1,420.3 | 2,386.8 |
| Jasprit Bumrah | bowler | T20I | 499 | 1,720.8 | 1,452.3 | 1,841.9 |
| Matthew Humphreys | bowler | T20I | 305 | 1,678.1 | 1,516.5 | 1,738.2 |
| Rashid Khan | bowler | IPL | 1,718 | 1,412.3 | 1,324.8 | 1,828.0 |
| Rashid Khan | bowler | T20I | 1,029 | 2,052.3 | 1,480.8 | 2,147.7 |
- Charts: `10_charts/slide_06_elo/`.

## Slide 7: Shock timeline, IPL 2025 final (PBKS chase)

- Royal Challengers Bengaluru v Punjab Kings, IPL 2025 Final, 2025-06-03, result: Royal Challengers Bengaluru Won by 6 runs. Target 191; PBKS made 184. Wickets at legal balls 30, 51, 58, 73, 98, 100, 104 (**verified**). [C]
- Batter high-band balls: 120/120; bowler 120/120. Peak batter pressure 8.35 at ball 99. Run of play on ball 19: 0.00 (batter), -0.50 (bowler). [C]
- Chart: `10_charts/slide_07_shock/ipl2025_final_shock_timeline.png`.

## Slide 8: Components and weights

| component | weight | effective share (bat) | variance share (bat) | effective share (bowl) | variance share (bowl) |
|---|---|---|---|---|---|
| Baseline | 0.200 | 0.184 | 0.291 | 0.159 | 0.199 |
| Zero pressure | 0.100 | 0.095 | 0.043 | 0.084 | 0.039 |
| Medium pressure | 0.150 | 0.145 | 0.102 | 0.135 | 0.080 |
| High pressure | 0.200 | 0.194 | 0.272 | 0.200 | 0.259 |
| Clutch | 0.150 | 0.186 | 0.212 | 0.205 | 0.209 |
| Peers | 0.100 | 0.093 | 0.115 | 0.113 | 0.135 |
| Consistency | 0.100 | 0.102 | -0.035 | 0.104 | 0.080 |
- Batter z-scores: 0.5 within role + 0.5 pooled (M-18). Charts: `10_charts/slide_08_components/`.

## Slide 9: Top batters

| rank | player | role | composite | baseline z | high z | clutch z | peers z | rank before fixes | n_eff | high n_eff |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Tim David | middle order | 1.577 | 2.284 | 0.978 | 1.935 | 2.920 | 2 | 998.3 | 338.5 |
| 2 | Phil Salt | top order | 1.283 | 1.960 | 1.271 | 2.978 | 0.968 | 43 | 1,357.1 | 61.6 |
| 3 | Rinku Singh | middle order | 1.164 | 1.700 | 2.139 | 3.000 | 0.693 | 57 | 1,045.7 | 306.3 |
| 4 | Donovan Ferreira | middle order | 1.162 | 0.956 | 1.995 | 3.000 | 1.015 | 8 | 316.7 | 127.0 |
| 5 | Jos Buttler | top order | 1.065 | 1.899 | 1.240 | 2.362 | 0.798 | 34 | 2,303.8 | 221.2 |
| 6 | Reeza Hendricks | top order | 0.981 | 1.093 | 1.474 | 2.556 | -0.148 | 64 | 631.0 | 83.1 |
| 7 | Glenn Phillips | middle order | 0.921 | 1.298 | 0.102 | 3.000 | 0.514 | 23 | 885.6 | 128.2 |
| 8 | David Miller | middle order | 0.913 | 1.589 | 1.100 | 2.482 | -0.336 | 44 | 975.1 | 308.7 |
| 9 | George Linde | lower order | 0.910 | 0.750 | 1.969 | 1.111 | 1.754 | 4 | 130.7 | 62.9 |
| 10 | Sai Sudharsan | top order | 0.848 | 2.021 | 0.772 | 0.745 | -0.374 | 31 | 1,448.1 | 142.2 |
| 11 | Ashutosh Sharma | lower order | 0.839 | 1.650 | 1.607 | 0.871 | 0.972 | 5 | 300.4 | 182.1 |
| 12 | Dinesh Karthik | middle order | 0.822 | 1.511 | 0.847 | 0.690 | 1.760 | 11 | 451.5 | 239.1 |
| 13 | Asif Khan | middle order | 0.817 | 0.714 | 1.190 | 0.994 | 1.243 | 38 | 170.8 | 86.3 |
| 14 | Romario Shepherd | lower order | 0.805 | 1.185 | 0.869 | 1.034 | 0.783 | 53 | 561.3 | 254.5 |
| 15 | Rishabh Pant | middle order | 0.777 | 0.802 | 1.810 | 3.000 | -0.299 | 80 | 989.1 | 140.1 |
| 16 | Suryakumar Yadav | middle order | 0.744 | 2.392 | 0.490 | -0.798 | 1.939 | 29 | 2,165.8 | 302.6 |
| 17 | Nicholas Pooran | top order | 0.737 | 1.330 | 0.580 | 2.714 | 0.976 | 22 | 1,518.9 | 256.5 |
| 18 | Naman Dhir | top order | 0.731 | 1.263 | 1.132 | 0.062 | 1.957 | 25 | 518.7 | 140.7 |
| 19 | Andre Russell | lower order | 0.716 | 1.932 | 0.670 | -1.271 | 1.265 | 12 | 552.3 | 217.4 |
| 20 | Namboori Tilak Varma | middle order | 0.697 | 1.669 | 0.694 | 1.101 | -0.039 | 62 | 2,081.8 | 422.4 |
- Gap between rank 10 and 11: 0.0084. [C]  Chart: `10_charts/slide_09_top_batters/`.

## Slide 10: Top bowlers

| rank | player | arm | composite | baseline z | high z | clutch z | peers z | rank before fixes | n_eff | high n_eff |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Mitchell Santner | Spin | 1.055 | 0.549 | 1.101 | 3.000 | 1.912 | 26 | 1,425.6 | 268.6 |
| 2 | Shaheen Afridi | Pace | 0.837 | 1.255 | 1.313 | 0.991 | 0.694 | 22 | 840.4 | 202.2 |
| 3 | Bhuvneshwar Kumar | Pace | 0.780 | 0.647 | 0.454 | 1.554 | 1.734 | 83 | 1,771.2 | 612.9 |
| 4 | Abrar Ahmed | Spin | 0.769 | 1.391 | 1.015 | 0.261 | 1.879 | 17 | 689.2 | 137.3 |
| 5 | Jasprit Bumrah | Pace | 0.759 | 1.285 | -0.149 | -0.513 | 2.940 | 8 | 1,454.2 | 320.1 |
| 6 | Mohammad Nawaz | Spin | 0.758 | 1.284 | 1.527 | 0.771 | 1.129 | 18 | 812.2 | 149.4 |
| 7 | Mark Adair | Pace | 0.737 | 0.794 | 0.413 | 2.134 | -0.487 | 92 | 645.5 | 102.5 |
| 8 | Sunil Narine | Spin | 0.729 | 0.565 | 0.621 | -0.560 | 3.000 | 7 | 1,249.7 | 300.7 |
| 9 | Mujeeb Ur Rahman | Spin | 0.712 | 1.253 | 0.571 | 0.455 | 1.691 | 4 | 676.0 | 175.1 |
| 10 | Nathan Ellis | Pace | 0.705 | 1.041 | 0.497 | 0.129 | 1.187 | 31 | 735.3 | 87.0 |
| 11 | Rasikh Salam | Pace | 0.686 | 0.115 | 1.684 | 2.037 | 0.197 | 42 | 455.8 | 124.5 |
| 12 | Liam Dawson | Spin | 0.668 | 0.579 | 0.836 | 0.713 | 1.631 | 27 | 370.4 | 90.1 |
| 13 | David Willey | Pace | 0.572 | 0.423 | 0.384 | 0.755 | 1.367 | 12 | 255.9 | 92.2 |
| 14 | Mohit Sharma | Pace | 0.560 | 0.157 | 2.163 | 3.000 | -0.254 | 93 | 517.7 | 83.8 |
| 15 | Lockie Ferguson | Pace | 0.553 | 0.297 | 1.196 | 1.297 | 0.242 | 71 | 834.0 | 160.7 |
| 16 | Saim Ayub | Spin | 0.527 | 0.744 | 0.023 | -0.333 | 1.488 | 32 | 462.9 | 141.1 |
| 17 | Matheesha Pathirana | Pace | 0.521 | 0.905 | 0.604 | 0.529 | 0.277 | 72 | 932.7 | 127.5 |
| 18 | Trent Boult | Pace | 0.510 | 0.283 | 0.210 | 1.549 | 0.828 | 90 | 1,201.5 | 403.3 |
| 19 | Lungi Ngidi | Pace | 0.510 | 0.459 | 0.736 | 0.761 | 0.708 | 15 | 685.8 | 121.6 |
| 20 | Taskin Ahmed | Pace | 0.506 | 1.247 | 0.165 | 1.247 | 0.034 | 102 | 842.7 | 78.7 |
- Top 20 by arm: 13 pace, 7 spin. Smallest high n_eff in the top 20: 78.7. [C]  Chart: `10_charts/slide_10_top_bowlers/`.

## Slide 11: Sanity checks on named players

| player | skill | role | ranked | rank | composite | rank before fixes | baseline-only rank | n_eff | high n_eff |
|---|---|---|---|---|---|---|---|---|---|
| Jos Buttler | batter | top order | True | 5 | 1.065 | 34 | 9 | 2,303.8 | 221.2 |
| Virat Kohli | batter | top order | True | 28 | 0.596 | 30 | 10 | 1,970.1 | 180.4 |
| David Miller | batter | middle order | True | 8 | 0.913 | 44 | 19 | 975.1 | 308.7 |
| Jasprit Bumrah | bowler | Pace | True | 5 | 0.759 | 8 | 2 | 1,454.2 | 320.1 |
| Rashid Khan | batter | lower order | True | 38 | 0.533 | 16 | 68 | 411.6 | 283.8 |
| Rashid Khan | bowler | Spin | True | 39 | 0.268 | 117 | 18 | 2,235.6 | 456.7 |
| Rilee Rossouw | batter | top order | False | – | 0.791 | 1 | – | 302.5 | 22.9 |
| Matthew Humphreys | bowler | Spin | False | – | 0.621 | 2 | – | 277.0 | 43.0 |
| Corbin Bosch | batter | lower order | True | 68 | 0.207 | 99 | 101 | 128.4 | 72.7 |
| Corbin Bosch | bowler | Pace | False | – | 1.050 | 1 | – | 346 | 44.4 |
| Mahendra Singh Dhoni | batter | lower order | True | 34 | 0.554 | 3 | 27 | 350.2 | 251.6 |
| Tim David | batter | middle order | True | 1 | 1.577 | 2 | 3 | 998.3 | 338.5 |
| Imad Wasim | batter | middle order | False | – | 0.458 | – | – | 118.9 | 47.1 |
| Imad Wasim | bowler | Spin | False | – | 1.042 | 5 | – | 188.6 | 43.5 |
| Vaibhav Sooryavanshi | batter | top order | False | – | 0.832 | 7 | – | 607 | 33.6 |
| Rahmanullah Gurbaz | batter | top order | True | 105 | -0.117 | 40 | 121 | 902.9 | 60.8 |
- Interpretations: `08_validation/sanity_check_interpretations.md`. Chart: `10_charts/slide_11_sanity_checks/`.

## Slide 12: Ablation and robustness

| skill | variant | Spearman | Kendall | top-10 overlap | top-20 overlap | mean abs rank change |
|---|---|---|---|---|---|---|
| batter | baseline_only | 0.782 | 0.590 | 4 | 10 | 20.3 |
| batter | pressure_only_bands_clutch | 0.877 | 0.710 | 8 | 15 | 14.1 |
| batter | no_pressure_baseline_peers_consistency | 0.772 | 0.579 | 3 | 7 | 21.0 |
| batter | equal_weights | 0.979 | 0.881 | 10 | 17 | 6.028 |
| batter | drop_baseline | 0.942 | 0.798 | 8 | 14 | 10.3 |
| batter | drop_band_zero | 0.982 | 0.889 | 9 | 18 | 5.702 |
| batter | drop_band_medium | 0.946 | 0.810 | 9 | 15 | 9.461 |
| batter | drop_band_high | 0.927 | 0.768 | 9 | 15 | 11.6 |
| batter | drop_clutch | 0.924 | 0.776 | 4 | 14 | 11.3 |
| batter | drop_peers | 0.987 | 0.903 | 9 | 17 | 5.277 |
| batter | drop_consistency | 0.977 | 0.872 | 6 | 17 | 6.596 |
| batter | previous_model_before_fixes | 0.845 | 0.657 | 3 | 9 | 16.6 |
| batter | role_blend_1_role_only_z | 0.991 | 0.928 | 9 | 18 | 3.986 |
| batter | exclude_super_overs | 1.000 | 0.996 | 9 | 20 | 0.284 |
| batter | legacy_8_term_with_form_pre_fix_frame | 0.832 | 0.641 | 3 | 8 | 17.5 |
| batter | pressure_weights_40_35_25 | 0.903 | 0.735 | 4 | 11 | 13.1 |
| batter | pressure_weights_50_30_20 | 0.959 | 0.832 | 6 | 14 | 8.397 |
| batter | pressure_weights_70_20_10 | 0.947 | 0.824 | 8 | 17 | 8.851 |
| batter | pressure_weights_equal_thirds | 0.861 | 0.673 | 1 | 8 | 16.3 |
| batter | pressure_raw_sum_bug_fixed | 0.836 | 0.644 | 3 | 9 | 17.5 |
| batter | role_blend_0_pooled_z | 0.990 | 0.920 | 9 | 17 | 4.113 |
| bowler | baseline_only | 0.662 | 0.486 | 5 | 10 | 26.3 |
| bowler | pressure_only_bands_clutch | 0.890 | 0.721 | 5 | 16 | 14.1 |
| bowler | no_pressure_baseline_peers_consistency | 0.786 | 0.605 | 7 | 12 | 19.3 |
| bowler | equal_weights | 0.981 | 0.887 | 10 | 18 | 5.874 |
| bowler | drop_baseline | 0.965 | 0.843 | 6 | 17 | 7.958 |
| bowler | drop_band_zero | 0.986 | 0.902 | 9 | 18 | 5.245 |
| bowler | drop_band_medium | 0.963 | 0.840 | 8 | 17 | 8.154 |
| bowler | drop_band_high | 0.932 | 0.787 | 9 | 15 | 10.6 |
| bowler | drop_clutch | 0.928 | 0.774 | 8 | 16 | 11.7 |
| bowler | drop_peers | 0.980 | 0.885 | 8 | 19 | 6.168 |
| bowler | drop_consistency | 0.981 | 0.889 | 8 | 18 | 5.762 |
| bowler | previous_model_before_fixes | 0.785 | 0.594 | 6 | 12 | 20.4 |
| bowler | exclude_super_overs | 1.000 | 0.992 | 9 | 20 | 0.517 |
| bowler | legacy_8_term_with_form_pre_fix_frame | 0.772 | 0.581 | 6 | 11 | 21.4 |
| bowler | pressure_weights_40_35_25 | 0.862 | 0.680 | 7 | 13 | 16.1 |
| bowler | pressure_weights_50_30_20 | 0.947 | 0.810 | 8 | 16 | 9.636 |
| bowler | pressure_weights_70_20_10 | 0.953 | 0.825 | 8 | 18 | 8.853 |
| bowler | pressure_weights_equal_thirds | 0.838 | 0.654 | 7 | 14 | 17.2 |
| bowler | pressure_raw_sum_bug_fixed | 0.722 | 0.542 | 7 | 12 | 22.9 |
- Ranking floor (same scores, other floors): batter floor 30: 194 ranked, top-20 overlap 16; batter floor 45: 170 ranked, top-20 overlap 18; batter floor 60: 141 ranked, top-20 overlap 20; batter floor 90: 95 ranked, top-20 overlap 16; bowler floor 30: 204 ranked, top-20 overlap 13; bowler floor 45: 167 ranked, top-20 overlap 17; bowler floor 60: 143 ranked, top-20 overlap 20; bowler floor 90: 107 ranked, top-20 overlap 17. [C]
- Baseline-only and full ranks reproduce `exports/23_ablation_ranks.csv`: True. [E]  Charts: `10_charts/slide_12_ablation/`.

## Slide 13: Component correlations and influence

- Batters: most correlated pair baseline–peers (0.520); most negative peers–consistency (-0.401). [C]
- Bowlers: most correlated band_high–clutch (0.617); most negative band_medium–clutch (-0.204). [C]
- Largest variance share: batters Baseline 29.1%; bowlers High pressure 25.9%. Charts: `10_charts/slide_13_component_correlations/`.

## Slide 14: Roles

| skill | role | players | reference (n_eff ≥ 30) | ranked | share of ranked pool | fail n_eff only | fail high-n only |
|---|---|---|---|---|---|---|---|
| batter | lower order | 429 | 141 | 35 | 0.248 | 14 | 2 |
| batter | middle order | 225 | 166 | 70 | 0.496 | 0 | 25 |
| batter | top order | 234 | 186 | 36 | 0.255 | 0 | 79 |
| bowler | Pace | 367 | 286 | 90 | 0.629 | 0 | 76 |
| bowler | Spin | 280 | 187 | 53 | 0.371 | 0 | 42 |
- Batting top 20 (top/middle/lower):
  - now: role-only z 4/12/4; **official 50/50 blend 6/10/4**; pooled z 8/9/3.
  - before the fixes: role-only 6/7/7; pooled 14/6/0. Legacy 8-term: role-only 6/7/7, pooled 12/5/3. [C]
- Why roles at all: Batters are compared partly within their batting role because the roles are different jobs. An opener faces the new ball with no wickets down and is judged on building an innings; a finisher arrives at the death, often after a collapse, and is judged on scoring fast against set bowlers. A strike rate or average is not comparable across those jobs without some adjustment. Pooling every batter rewards the role whose numbers are easiest to post. A role-only z-score assumes each role is equally deep in talent. Neither is a finding about cricket. The 50/50 blend (ROLE_BLEND = 0.5) is a stated compromise between the two.
- Charts: `10_charts/slide_14_roles/`.

## Slide 15: Limitations, fixes and bugs

- **BUG-01 Run-of-play term read the whole innings on legal ball 19 (FIXED)** [FIXED]. Pre-fix behaviour rebuilt and checked against the pre-fix model's own columns (max gap 0.0). Ball 19 mean run of play: batter 0.983 before, 0.076 now; bowler 1.000 before, 0.251 now. Scales: runs 1.1072 before, 0.5928 now; wickets 0.0830 before, 0.0733 now. Ball-19 bowler high-band share 54.9% before, 45.0% now (neighbouring balls 18 and 20 sit at a similar level under the new weights).
- **BUG-02 Deck export 10 labels final shock as 'count_shock'** [VERIFIED (open)]. exports/10_sample_innings_timeline.csv count_shock_bat equals final shock: True; equals count part: False.
- **BUG-03 Bowler clutch compared spell economy without extras to career economy with extras (FIXED)** [FIXED]. Ranked bowlers: career economy with extras minus legal-ball economy = 0.355 runs/over on average. On the current high-band spells, 47.0% would beat the bowler's own rate on the old basis against 43.5% on the legal-ball basis; mean own gap -0.162 vs -0.268 scale units. Comparison economy equals legal-ball economy to 0.0.
- **KI-01 Form term used a full-career bar (look-ahead)** [VERIFIED (legacy); NOT_APPLICABLE (current)]. Source at git 29956ed: bar = float(career.loc[player]). Form was removed earlier (7 terms, consistency 0.10).
- **KI-02 xWicket is trained on bowler wickets but charged against every striker dismissal** [VERIFIED (open)]. Legal balls: striker_out 10,567 vs bowler_wicket 10,247; striker run outs 315; non-striker dismissals 266. Mean xW 5.14% vs striker-out rate 5.49%. Mean wicket part of ball value: batter -0.0140, bowler 0.0074 per ball.
- **KI-03 No wickets-fallen feature in the expectation model (FIXED)** [FIXED]. Runs actual minus expected per ball, before -> now: 0-1 down 0.084 -> 0.048; 2-3 0.018 -> -0.001; 4-5 -0.011 -> 0.012; 6-7 -0.104 -> 0.007; 8-9 -0.345 -> -0.044. Mean bowler ball value at 8-9 down 0.391 -> 0.057.
- **KI-04 Wides and no-balls never enter the ball value or Elo** [VERIFIED (open)]. 11,278 of 279,563 conceded runs (4.0%) are on illegal deliveries; 25 bowler wickets (stumpings off wides) are credited in baseline only.
- **M-01 Recent events still lift the high band, but no longer define it (PARTLY FIXED)** [PARTLY FIXED]. Batter high-band balls within six balls after a wicket: 99.9% before, 75.6% now (base rate 27.5%). Bowler high-band balls after a four or six in the last six: 100.0% before, 86.7% now (base rate 63.6%). Situation share of pressure variance: batters 7.1% -> 68.7%, bowlers 3.1% -> 71.7%. Finals in the batter high band: 26.1% -> 86.4%.
- **M-06 Small high-pressure samples at the top of the bowling table (FIXED)** [FIXED]. Before the fix, 4 of the top-10 bowlers had high n_eff < 60 (Matthew Humphreys 31.3, Haider Ali 58.5, Imad Wasim 38.5, Dwayne Bravo 39.4). Now 0; the smallest high n_eff in the bowling top 10 is 87.0 and in the top 20 78.7. Ranked pools: batters 216 -> 141, bowlers 226 -> 143.
- **M-07 Expectation models discriminate weakly (OPEN)** [VERIFIED (open)]. xR MAE 1.3043 -> 1.2986 against 1.3282 for a constant; R^2 0.0133 -> 0.0159. xW AUC 0.5597 -> 0.5601; calibration slope 0.922 (xR), logistic 0.729 (xW).
- **M-17 Bowler high band moved toward the powerplay (NEW, side effect of the pressure fix)** [VERIFIED (open)]. Share of pace high-band balls by phase, before -> now: powerplay 35.5% -> 72.1%, middle 36.2% -> 17.4%, death 28.4% -> 10.5%. Pace death balls in the high band: 23.9% -> 8.8%.
- **M-18 Batters are z-scored half within role, half against all batters** [MODELLING CHOICE]. Top-20 batting role mix (top/middle/lower): role-only z 4/12/4, official 50/50 blend 6/10/4, pooled z 8/9/3. Before the fixes: role-only 6/7/7, pooled 14/6/0. Rank agreement with the official blend: role-only Spearman 0.991, pooled 0.990.
- **M-19 Pressure weights 0.60/0.25/0.15 are a judgement** [MODELLING CHOICE]. pre_fix_model (raw sum, ball-19 bug): batter after-wicket 99.9%, finals high 26.1%, pace death 28.4%, Spearman bat 0.845 / bowl 0.785; official: batter after-wicket 75.6%, finals high 86.4%, pace death 10.5%; pressure_weights_40_35_25: batter after-wicket 96.3%, finals high 54.0%, pace death 18.3%, Spearman bat 0.903 / bowl 0.862; pressure_weights_50_30_20: batter after-wicket 88.3%, finals high 63.5%, pace death 14.3%, Spearman bat 0.959 / bowl 0.947; pressure_weights_70_20_10: batter after-wicket 63.1%, finals high 86.4%, pace death 10.8%, Spearman bat 0.947 / bowl 0.953; pressure_weights_equal_thirds: batter after-wicket 98.4%, finals high 47.2%, pace death 20.1%, Spearman bat 0.861 / bowl 0.838; pressure_raw_sum_bug_fixed: batter after-wicket 99.9%, finals high 26.0%, pace death 29.9%, Spearman bat 0.836 / bowl 0.722
- Full register: `09_limitations/limitations_register.csv`; before/after: `12_model_fixes/fix_before_after.csv`. Chart: `10_charts/slide_15_limitations/`.

## Slide 16: Takeaways

- See `key_findings.md` and `12_model_fixes/model_fixes.md`.
- Not computed: DLS par analysis [RD]; uncertainty intervals for ranks [RI] (needs a bootstrap over matches); external validation against selections or awards [RD].