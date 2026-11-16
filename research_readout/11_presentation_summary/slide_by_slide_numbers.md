# Slide-by-slide numbers

One section per slide. Status tags: **[C]** COMPUTED here, **[E]** EXISTING in the repository and reproduced, **[RD]** REQUIRES_DATA, **[RI]** REQUIRES_IMPLEMENTATION, **[NA]** NOT_APPLICABLE. Each section names its source files and charts. The model under audit is the current **7-term** version (Form removed, consistency 0.10). The 8-term version is shown only for comparison.

## Slide 1: Objective and scope

- Rank T20 batters and bowlers on how they perform under pressure, using 192,445 legal balls from 2022-01-22 to 2026-11-01. [C]
- 216 batters and 226 bowlers meet the ranking floor (n_eff ≥ 120 and high-band n_eff ≥ 30). [C]
- The brief lists 8 weighted terms. The code has 7: Form was removed and consistency raised to 0.10. Form is [NA].

## Slide 2: Data and cleaning

- Deliveries: 200,999; none deleted; duplicate delivery keys 0. [C]
- Super overs included: 38 deliveries, 33 legal balls, 6 matches. [C]
- Excluded from ball value: 7,714 wides, 576 no-balls, 264 'other' extras (treated as illegal). [C]
- Legal balls used: **192,445** in 867 matches. IPL 83,755 (367 matches), T20I 101,960 (470), Emerging/Rising 6,730 (30, counted at weight 0.5). [C/E: matches exports/01_cleaning_funnel.csv]
- Players who faced or bowled a legal ball: 888 batters, 647 bowlers. [C]
- Reduced matches: 34. Reduced chases with no supplied target: 2. DLS par: [RD].
- Sources: `01_dataset/*.csv`. Charts: `10_charts/slide_02_dataset/`.

## Slide 3: The pressure index

- pressure = occasion × competition × ball difficulty + shock + run of play (see `02_pressure/pressure_formula_as_executed.csv`). [E]
- Band cut-offs (p50 / p80): batters -0.050 / 1.919; pace 0.320 / 1.446; spin 0.241 / 1.459. [C/E: match exports/08]
- Actual batter band shares (zero / medium / high): 49.9% / 29.0% / 21.1%, against a 50/30/20 design. [C]
- Phase × arm (bowler high-band share):
| arm | phase | legal balls | mean bowler pressure | % balls high | % of arm's high balls | economy (legal) |
|---|---|---|---|---|---|---|
| Pace | powerplay | 48503 | 0.586 | 17.1% | 35.5% | 8.171 |
| Pace | middle | 40885 | 0.393 | 20.7% | 36.2% | 8.528 |
| Pace | death | 27836 | 0.436 | 23.9% | 28.4% | 9.896 |
| Spin | powerplay | 12336 | 0.633 | 21.1% | 17.3% | 7.965 |
| Spin | middle | 57896 | 0.359 | 19.5% | 75.2% | 7.683 |
| Spin | death | 4989 | 0.411 | 22.9% | 7.6% | 9.258 |
- Variance of batter pressure: base 7.1%, shock 51.8%, run of play 41.1%. [C]
- Sources: `02_pressure/`. Charts: `10_charts/slide_03_pressure/`.

## Slide 4: What 'high pressure' actually captures

- 99.94% of batter high-band balls fall within 6 balls after a wicket. Away from those windows, the high band takes only 0.018% of balls. [C]
- 99.98% of bowler high-band balls follow a four or six in the previous 6 (zero band: 35.7%). [C]
- Strike rate by batter band (zero / medium / high): 147.5 / 140.7 / 118.5. Pace economy: 8.34 / 8.54 / 9.83. Spin economy: 7.29 / 8.12 / 8.75 (legal balls). [C]
- High-band share in balls 1–18: 0.04%. In finals: 26.1%; in league games: 21.3%. [C]
- Super overs (33.0 legal balls) carry knockout occasion (mean 1.86) and mean batter pressure 0.688, against 0.835 for other knockout-match balls and 0.926 for other death balls. Yet 0.0% of them reach the batter high band and 0.0% the bowler high band: shock and run of play start at zero in a new innings, and the highest super-over ball is 0.869 below the high cut. [C] (`02_pressure/super_over_pressure.csv`, chart `slide_03_pressure/super_over_pressure.png`)
- Charts: `10_charts/slide_04_high_pressure_meaning/`.

## Slide 5: Expected runs and wickets (ball value)

- Ball value: batter = (runs − xR) − 4 × (out − xW); bowler = (xR − charged) + 4 × (wicket − xW). Predictions use only earlier balls. [E]
| model | target | mean pred | mean actual | MAE | RMSE | OLS slope | OLS intercept | logit slope | logit intercept | AUC | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| xR | bat_runs | 1.381 | 1.394 | 1.304 | 1.731 | 0.985 | 0.035 | – | – | – | – |
| xW | bowler_wicket | 0.051 | 0.053 | 0.099 | 0.224 | – | – | 0.811 | -0.506 | 0.560 | 0.050 |
| xW | striker_out | 0.051 | 0.055 | 0.100 | 0.227 | – | – | 0.891 | -0.242 | 0.566 | 0.052 |
- xR deciles: predicted 1.099 → 1.793, actual 1.101 → 1.801; the largest decile gap is 0.040 runs per ball. [C/E: matches exports/14]
- Wickets fallen, runs actual minus expected per ball: 0–1 down 0.084, 8–9 down -0.345 (KI-03). [C]
- Charts: `10_charts/slide_05_expectation_models/`.

## Slide 6: Elo

- Steps: 4 (runs), 16 (wicket), 20 (team), not halved. Final raw range: batters 931.5–2571.6 (SD 141.8); bowlers 1059.8–2136.6 (SD 118.0). Acceptance limits are 600–2800 and SD 250. [C/E: matches exports/12]
| player | skill | ladder | balls | final | min | max | best match | worst match |
|---|---|---|---|---|---|---|---|---|
| David Miller | batter | IPL | 908 | 1,537.2 | 1,442.7 | 1,728.4 | 125.8 | -56.8 |
| David Miller | batter | T20I | 365 | 1,831.3 | 1,495.0 | 1,882.4 | 198.6 | -41.5 |
| Jos Buttler | batter | IPL | 1,784 | 1,767.0 | 1,468.8 | 2,026.2 | 117.9 | -78.2 |
| Jos Buttler | batter | T20I | 1,036 | 2,228.2 | 1,460.2 | 2,228.2 | 140.0 | -33.8 |
| Rilee Rossouw | batter | IPL | 255 | 1,741.3 | 1,466.2 | 1,770.0 | 150.5 | -33.8 |
| Rilee Rossouw | batter | T20I | 160 | 1,823.0 | 1,468.5 | 1,846.4 | 158.7 | -23.9 |
| Virat Kohli | batter | IPL | 2,090 | 1,914.6 | 1,339.4 | 1,949.8 | 116.7 | -78.3 |
| Virat Kohli | batter | T20I | 364 | 1,726.8 | 1,495.2 | 1,770.5 | 213.5 | -43.9 |
| Corbin Bosch | bowler | IPL | 163 | 1,608.7 | 1,464.0 | 1,653.8 | 77.9 | -29.1 |
| Corbin Bosch | bowler | T20I | 204 | 1,745.2 | 1,424.3 | 1,821.5 | 117.3 | -74.7 |
| Jasprit Bumrah | bowler | IPL | 1,209 | 2,107.9 | 1,412.7 | 2,420.7 | 156.7 | -96.2 |
| Jasprit Bumrah | bowler | T20I | 499 | 1,791.2 | 1,461.3 | 1,903.6 | 100.7 | -124.4 |
| Matthew Humphreys | bowler | T20I | 305 | 1,694.6 | 1,512.2 | 1,740.1 | 120.5 | -55.2 |
| Rashid Khan | bowler | IPL | 1,718 | 1,483.6 | 1,359.1 | 1,830.2 | 107.4 | -111.3 |
| Rashid Khan | bowler | T20I | 1,029 | 2,048.9 | 1,487.2 | 2,168.4 | 88.0 | -55.9 |
- Year-over-year Spearman of season-end ratings (≥ 120 balls in both seasons): batters 0.54, 0.70, 0.76, 0.79; bowlers 0.46, 0.44, 0.72, 0.74. [C]
- Elo shapes xR and xW. It is not a composite component. Charts: `10_charts/slide_06_elo/`.

## Slide 7: Shock timeline, IPL 2025 final (PBKS chase)

- Royal Challengers Bengaluru v Punjab Kings, IPL 2025 Final, 2025-06-03, result: Royal Challengers Bengaluru Won by 6 runs. Target 191; PBKS made 184. Occasion multiplier 3.0. [C]
- Wickets at legal balls 30, 51, 58, 73, 98, 100, 104: **verified** against the brief. As delivery numbers including extras: 31, 52, 59, 75, 101, 103, 107. [C]
- Batter high-band balls: 48/120. Bowler high-band balls: 50/120. Peak batter pressure 5.00 at ball 99. Run of play on ball 19 = 1.00 (batter) and 1.00 (bowler), pinned by BUG-01. [C]
- Sources: `06_shock/`. Chart: `10_charts/slide_07_shock/ipl2025_final_shock_timeline.png`.

## Slide 8: Components and weights

| component | weight | effective share (bat) | variance share (bat) | effective share (bowl) | variance share (bowl) |
|---|---|---|---|---|---|
| Baseline | 0.200 | 0.186 | 0.300 | 0.155 | 0.204 |
| Zero pressure | 0.100 | 0.095 | 0.073 | 0.089 | 0.051 |
| Medium pressure | 0.150 | 0.155 | 0.184 | 0.140 | 0.078 |
| High pressure | 0.200 | 0.192 | 0.237 | 0.210 | 0.277 |
| Clutch | 0.150 | 0.168 | 0.109 | 0.197 | 0.194 |
| Peers | 0.100 | 0.099 | 0.137 | 0.106 | 0.116 |
| Consistency | 0.100 | 0.105 | -0.041 | 0.103 | 0.080 |
- Form: [NA] in the current model (legacy weight 0.05). Composite among ranked players: batters mean 0.093, SD 0.489; bowlers mean -0.037, SD 0.494. [C]
- Sources: `03_components/`, `08_validation/component_influence.csv`. Charts: `10_charts/slide_08_components/`.

## Slide 9: Top batters

| rank | player | role | composite | baseline z | high z | clutch z | peers z | legacy rank | n_eff | high n_eff |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Rilee Rossouw | top order | 1.413 | 1.389 | 3.000 | 0.008 | 2.059 | 1 | 302.5 | 55.6 |
| 2 | Tim David | middle order | 1.171 | 2.359 | 0.419 | -0.427 | 3.000 | 3 | 998.3 | 313.9 |
| 3 | Mahendra Singh Dhoni | lower order | 1.119 | 1.789 | 1.037 | 3.000 | 1.586 | 2 | 350.2 | 127.4 |
| 4 | George Linde | lower order | 1.059 | 1.091 | 2.028 | 0.262 | 1.732 | 4 | 130.7 | 61.5 |
| 5 | Ashutosh Sharma | lower order | 1.028 | 2.097 | 1.617 | -0.141 | 0.974 | 5 | 300.4 | 93.4 |
| 6 | Tom Banton | middle order | 0.954 | 1.207 | 2.233 | -0.073 | 1.418 | 11 | 238.8 | 68.6 |
| 7 | Vaibhav Sooryavanshi | top order | 0.914 | 2.458 | 0.003 | -2.171 | 3.000 | 6 | 607 | 41.6 |
| 8 | Donovan Ferreira | middle order | 0.913 | 0.973 | 0.969 | 2.013 | 1.047 | 7 | 316.7 | 85.8 |
| 9 | Muhammad Waseem | top order | 0.903 | 0.893 | 1.138 | 0.008 | 1.673 | 9 | 388.7 | 43.2 |
| 10 | Bevon Jacobs | middle order | 0.901 | 1.156 | 2.234 | -0.073 | 0.430 | 15 | 185.9 | 30.6 |
| 11 | Dinesh Karthik | middle order | 0.886 | 1.524 | -0.511 | 2.072 | 1.825 | 8 | 451.5 | 152.3 |
| 12 | Andre Russell | lower order | 0.863 | 2.375 | 0.561 | -1.063 | 1.258 | 12 | 552.3 | 195.8 |
| 13 | Rajat Patidar | middle order | 0.846 | 2.152 | 0.552 | -0.073 | 1.161 | 19 | 777.3 | 198.7 |
| 14 | Cameron Green | middle order | 0.839 | 1.734 | -1.122 | 2.174 | 0.505 | 14 | 898.9 | 183.0 |
| 15 | Yashasvi Jaiswal | top order | 0.837 | 1.252 | -0.427 | 3.000 | 0.898 | 17 | 1,516.8 | 106.5 |
| 16 | Rashid Khan | lower order | 0.805 | 0.859 | -0.070 | 3.000 | 2.114 | 10 | 411.6 | 160.3 |
| 17 | Mukul Choudhary | lower order | 0.795 | 1.264 | 0.819 | 0.455 | 0.639 | 26 | 120 | 50 |
| 18 | Patrick Cummins | lower order | 0.779 | 1.099 | 0.138 | 2.694 | 1.397 | 13 | 198.5 | 92.6 |
| 19 | Finn Allen | top order | 0.762 | 1.283 | -0.142 | 0.008 | 2.756 | 16 | 695.2 | 33.3 |
| 20 | Prabhsimran Singh | top order | 0.758 | 1.026 | 1.302 | 1.110 | 0.514 | 23 | 999.0 | 86.0 |
- Gap between rank 10 and 11: 0.0147. [C]  Chart: `10_charts/slide_09_top_batters/`.

## Slide 10: Top bowlers

| rank | player | arm | composite | baseline z | high z | clutch z | peers z | legacy rank | n_eff | high n_eff |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Corbin Bosch | Pace | 1.335 | 1.199 | 2.637 | 3.000 | 0.585 | 1 | 346 | 83.7 |
| 2 | Matthew Humphreys | Spin | 1.324 | 1.166 | 1.468 | 2.679 | 1.713 | 2 | 277.0 | 31.3 |
| 3 | Haider Ali | Spin | 1.076 | 1.233 | 1.876 | 0.254 | 2.152 | 5 | 247.8 | 58.5 |
| 4 | Mujeeb Ur Rahman | Spin | 1.041 | 1.253 | 1.460 | 1.728 | 1.691 | 4 | 676.0 | 117.9 |
| 5 | Imad Wasim | Spin | 1.025 | 1.446 | 1.543 | 0.096 | 3.000 | 3 | 188.6 | 38.5 |
| 6 | Dwayne Bravo | Pace | 0.930 | 0.850 | 1.227 | 1.090 | -0.530 | 8 | 135.2 | 39.4 |
| 7 | Sunil Narine | Spin | 0.892 | 0.565 | 1.001 | 0.698 | 3.000 | 7 | 1,249.7 | 260.2 |
| 8 | Jasprit Bumrah | Pace | 0.890 | 1.285 | 0.360 | 0.004 | 2.940 | 6 | 1,454.2 | 303.9 |
| 9 | Shoriful Islam | Pace | 0.854 | 0.583 | 1.735 | 1.987 | -0.292 | 9 | 649.6 | 87.7 |
| 10 | Haris Rauf | Pace | 0.749 | 1.025 | 0.298 | 3.000 | -0.170 | 11 | 798.4 | 169.6 |
| 11 | Benjamin Lister | Pace | 0.739 | 0.207 | 1.223 | 2.112 | 0.508 | 20 | 186.1 | 39.0 |
| 12 | David Willey | Pace | 0.733 | 0.423 | 2.012 | 0.774 | 1.367 | 14 | 255.9 | 50.4 |
| 13 | Mark Wood | Pace | 0.726 | 1.497 | 0.024 | -1.408 | 0.830 | 13 | 214.7 | 44.6 |
| 14 | Salman Mirza | Pace | 0.716 | 1.644 | 0.697 | -0.357 | 0.756 | 10 | 303 | 41 |
| 15 | Lungi Ngidi | Pace | 0.660 | 0.459 | 1.024 | 1.548 | 0.708 | 12 | 685.8 | 138.5 |
| 16 | Benjamin Sears | Pace | 0.653 | 1.093 | 0.836 | -0.243 | 0.376 | 15 | 386.5 | 97.4 |
| 17 | Abrar Ahmed | Spin | 0.649 | 1.391 | 1.146 | -1.278 | 1.879 | 23 | 689.2 | 125.5 |
| 18 | Mohammad Nawaz | Spin | 0.623 | 1.284 | 0.866 | 0.200 | 1.129 | 16 | 812.2 | 122.2 |
| 19 | Yash Punja | Spin | 0.622 | -0.518 | 0.871 | 1.741 | 0.831 | 18 | 180 | 42 |
| 20 | Harry Tector | Spin | 0.617 | 0.560 | 1.165 | 0.254 | 0.519 | 21 | 185.7 | 30.7 |
- Top 20 by arm: 11 pace, 9 spin. The ranked pool is 65.5% pace. [C]  Chart: `10_charts/slide_10_top_bowlers/`.

## Slide 11: Sanity checks on named players

| player | skill | role | ranked | rank | composite | legacy rank | baseline-only rank | n_eff | high n_eff |
|---|---|---|---|---|---|---|---|---|---|
| Jos Buttler | batter | top order | True | 34 | 0.583 | 30 | 16 | 2,303.8 | 286.6 |
| Virat Kohli | batter | top order | True | 30 | 0.605 | 41 | 14 | 1,970.1 | 203.8 |
| David Miller | batter | middle order | True | 44 | 0.499 | 54 | 22 | 975.1 | 290.9 |
| Jasprit Bumrah | bowler | Pace | True | 8 | 0.890 | 6 | 7 | 1,454.2 | 303.9 |
| Rashid Khan | batter | lower order | True | 16 | 0.805 | 10 | 62 | 411.6 | 160.3 |
| Rashid Khan | bowler | Spin | True | 117 | -0.037 | 117 | 34 | 2,235.6 | 465.0 |
| Rilee Rossouw | batter | top order | True | 1 | 1.413 | 1 | 29 | 302.5 | 55.6 |
| Matthew Humphreys | bowler | Spin | True | 2 | 1.324 | 2 | 16 | 277.0 | 31.3 |
| Corbin Bosch | batter | lower order | True | 99 | 0.171 | 103 | 109 | 128.4 | 57.6 |
| Corbin Bosch | bowler | Pace | True | 1 | 1.335 | 1 | 15 | 346 | 83.7 |
| Mahendra Singh Dhoni | batter | lower order | True | 3 | 1.119 | 2 | 12 | 350.2 | 127.4 |
| Tim David | batter | middle order | True | 2 | 1.171 | 3 | 5 | 998.3 | 313.9 |
| Imad Wasim | batter | middle order | False | – | 0.567 | – | – | 118.9 | 40.3 |
| Imad Wasim | bowler | Spin | True | 5 | 1.025 | 3 | 4 | 188.6 | 38.5 |
| Vaibhav Sooryavanshi | batter | top order | True | 7 | 0.914 | 6 | 2 | 607 | 41.6 |
| Rahmanullah Gurbaz | batter | top order | True | 40 | 0.551 | 43 | 182 | 902.9 | 68.0 |
- Interpretations: `08_validation/sanity_check_interpretations.md`. Chart: `10_charts/slide_11_sanity_checks/`.

## Slide 12: Ablation and robustness

| skill | variant | Spearman | Kendall | top-10 overlap | top-20 overlap | top-10 Jaccard | top-20 Jaccard | mean abs rank change |
|---|---|---|---|---|---|---|---|---|
| batter | baseline_only | 0.806 | 0.614 | 3 | 7 | 0.176 | 0.212 | 30.1 |
| batter | pressure_only_bands_clutch | 0.910 | 0.754 | 6 | 14 | 0.429 | 0.538 | 18.6 |
| batter | no_pressure_baseline_peers_consistency | 0.833 | 0.644 | 4 | 10 | 0.250 | 0.333 | 26.4 |
| batter | equal_weights | 0.980 | 0.886 | 8 | 19 | 0.667 | 0.905 | 8.741 |
| batter | drop_baseline | 0.948 | 0.804 | 8 | 17 | 0.667 | 0.739 | 15.5 |
| batter | drop_band_zero | 0.981 | 0.889 | 8 | 17 | 0.667 | 0.739 | 8.611 |
| batter | drop_band_medium | 0.950 | 0.812 | 7 | 16 | 0.538 | 0.667 | 14.3 |
| batter | drop_band_high | 0.929 | 0.767 | 4 | 16 | 0.250 | 0.667 | 18.2 |
| batter | drop_clutch | 0.935 | 0.800 | 8 | 12 | 0.667 | 0.429 | 14.9 |
| batter | drop_peers | 0.986 | 0.898 | 8 | 17 | 0.667 | 0.739 | 8.185 |
| batter | drop_consistency | 0.980 | 0.880 | 7 | 17 | 0.538 | 0.739 | 9.630 |
| batter | legacy_8_term_with_form | 0.989 | 0.915 | 8 | 18 | 0.667 | 0.818 | 6.880 |
| batter | exclude_super_overs | 1.000 | 0.997 | 10 | 20 | 1.000 | 1.000 | 0.343 |
| batter | no_role_split_pooled_z | 0.920 | 0.766 | 5 | 12 | 0.333 | 0.429 | 18.2 |
| batter | diagnostic_runofplay_bugfree | 0.998 | 0.967 | 9 | 20 | 0.818 | 1.000 | 2.685 |
| bowler | baseline_only | 0.698 | 0.507 | 2 | 11 | 0.111 | 0.379 | 38.6 |
| bowler | pressure_only_bands_clutch | 0.897 | 0.718 | 7 | 12 | 0.538 | 0.429 | 22.9 |
| bowler | no_pressure_baseline_peers_consistency | 0.783 | 0.594 | 6 | 9 | 0.429 | 0.290 | 32 |
| bowler | equal_weights | 0.982 | 0.891 | 8 | 17 | 0.667 | 0.739 | 9.027 |
| bowler | drop_baseline | 0.963 | 0.840 | 8 | 15 | 0.667 | 0.600 | 12.9 |
| bowler | drop_band_zero | 0.984 | 0.895 | 9 | 17 | 0.818 | 0.739 | 8.513 |
| bowler | drop_band_medium | 0.957 | 0.826 | 8 | 16 | 0.667 | 0.667 | 13.8 |
| bowler | drop_band_high | 0.932 | 0.775 | 9 | 11 | 0.818 | 0.379 | 18.3 |
| bowler | drop_clutch | 0.923 | 0.765 | 7 | 16 | 0.538 | 0.667 | 19.0 |
| bowler | drop_peers | 0.981 | 0.885 | 8 | 17 | 0.667 | 0.739 | 9.708 |
| bowler | drop_consistency | 0.981 | 0.885 | 10 | 18 | 1.000 | 0.818 | 9.442 |
| bowler | legacy_8_term_with_form | 0.991 | 0.926 | 9 | 18 | 0.818 | 0.818 | 6.204 |
| bowler | exclude_super_overs | 1.000 | 0.996 | 10 | 19 | 1.000 | 0.905 | 0.381 |
| bowler | diagnostic_runofplay_bugfree | 0.958 | 0.831 | 7 | 14 | 0.538 | 0.538 | 13.0 |
- Sooryavanshi: official 7, baseline only 2, legacy 6, pooled z 3, without clutch 2. [C]
- Gurbaz: official 40, baseline only 182, legacy 43, pooled z 30, without clutch 108. [C]
- Super overs: including them (the official run) against excluding them gives batters Spearman 0.9998 (20/20 top-20 overlap) and bowlers 0.9998 (19/20). Largest composite change: batters 0.088, bowlers 0.122. Same ranked pool: True. Movers: `ablation_top_movers.csv` ('super overs included vs excluded'). [C]
- The baseline-only and full ranks reproduce `exports/23_ablation_ranks.csv`: True. [E]  Charts: `10_charts/slide_12_ablation/`.

## Slide 13: Component correlations and influence

- Batters: the most correlated pair is baseline–peers (0.605); the most negative is peers–consistency (-0.400). High vs medium band 0.098. [C]
- Bowlers: most correlated baseline–band_zero (0.530); most negative band_medium–clutch (-0.133). High band vs clutch 0.435. [C]
- Largest variance share: batters Baseline 30.0%; bowlers High pressure 27.7%. Dropping the high band leaves 16/20 batters and 11/20 bowlers in the top 20. [C]
- Sources: `08_validation/component_correlation_*.csv`, `component_influence.csv`. Charts: `10_charts/slide_13_component_correlations/`.

## Slide 14: Roles

| skill | role | players | reference (n_eff ≥ 30) | ranked | share of ranked pool | fail n_eff only | fail high-n only |
|---|---|---|---|---|---|---|---|
| batter | lower order | 429 | 141 | 37 | 0.171 | 36 | 0 |
| batter | middle order | 225 | 166 | 92 | 0.426 | 7 | 3 |
| batter | top order | 234 | 186 | 87 | 0.403 | 1 | 28 |
| bowler | Pace | 367 | 286 | 148 | 0.655 | 2 | 18 |
| bowler | Spin | 280 | 187 | 78 | 0.345 | 1 | 17 |
- Batting top 20 (top/middle/lower):
  - current, role-split z: [6, 7, 7]. **Verified 6/7/7.**
  - current, pooled z: [14, 6, 0]. **The brief's 12/5/3 does not reproduce for the current model.**
  - legacy 8-term, role-split z: [6, 7, 7].
  - legacy 8-term, pooled z: [12, 5, 3]. **12/5/3 reproduces here.** [C]
- Share of balls in the high band, ranked batters: top order 13.9%, middle 27.5%, lower 38.5%. [C]  Charts: `10_charts/slide_14_roles/`.

## Slide 15: Limitations and bugs

- **BUG-01 Run-of-play term reads the whole innings on legal ball 19** (High (bowlers), Low (batters)). Replicated exactly (max gap 0). Ball 19 mean run of play: batter 0.983 (bug-free 0.076), bowler 1.000 (bug-free 0.251). Scale: runs 1.1072 vs bug-free 0.5928; wickets 0.0830 vs 0.0733. Ball 19 bowler high-band share 54.9% vs 20% design.
- **BUG-02 Deck export 10 labels final shock as 'count_shock'** (Low). exports/10_sample_innings_timeline.csv count_shock_bat equals final shock: True; equals count part: False.
- **BUG-03 Bowler clutch compares spell economy without extras to career economy with extras** (Medium). Ranked bowlers: career economy with extras minus legal-balls-only economy = 0.369 runs/over on average = 0.107 clutch-scale units (scale 3.433). High-band spells counted as beating the bowler's own rate: 36.6% as executed vs 33.0% on a like-for-like basis.
- **KI-01 Form term used a full-career bar (look-ahead)** (Resolved in current code). Source at git 29956ed: bar = float(career.loc[player]) with career = strike_rate/economy over all seasons. The current working tree removes Form entirely (7 terms, consistency 0.10).
- **KI-02 xWicket is trained on bowler wickets but charged against every striker dismissal** (Low-Medium). Legal balls: striker_out 10,567 vs bowler_wicket 10,247; striker run outs 315; non-striker dismissals 266. Mean xW 5.13% vs striker-out rate 5.49% and bowler-wicket rate 5.32%. Mean wicket part of ball value: batter -0.0143, bowler 0.0077 per ball.
- **KI-03 No wickets-fallen feature in the expectation model** (High). Runs actual minus expected per ball: 0-1 down 0.084, 2-3 down 0.018, 4-5 down -0.011, 6-7 down -0.104, 8-9 down -0.345. Mean batter ball value at 8-9 down -0.421 on 6,621 balls.
- **KI-04 Wides and no-balls never enter the ball value or Elo** (Medium). 11,278 of 279,563 conceded runs (4.0%) are on illegal deliveries; 25 bowler wickets (stumpings off wides) are credited in baseline only.
- **M-01 High pressure is, in practice, the six balls after a wicket (batters) or a boundary (bowlers)** (High (interpretation)). 99.94% of batter high-band balls are within 6 balls after a wicket; 0.018% of other balls are high. 99.98% of bowler high-band balls follow a four or six in the previous six. Variance share of the occasion x competition x ball term: batters 7.1%, bowlers 3.1%.
- **M-02 The first 18 balls of an innings are almost never high pressure** (Medium). Batter high-band share on balls 1-18: 0.04% vs 25.1% from ball 19; bowlers 4.2% on balls 1-18.
- **M-06 Top bowlers sit close to the sample floor** (Medium). Median high-band n_eff: top-20 bowlers 71.1 vs all ranked 92.8; 4 of the top-10 bowlers have high n_eff < 60. Humphreys high n_eff 31.3; Bosch 367 legal balls.
- **M-07 Expectation models discriminate weakly** (Medium). xR: MAE 1.304 vs 1.328 for a constant; R^2 0.0133; calibration slope 0.985. xW (bowler wicket): AUC 0.560, Brier 0.05025 vs 0.05041 constant, logistic slope 0.811.
- Full register: `09_limitations/limitations_register.csv`. Chart: `10_charts/slide_15_limitations/`.

## Slide 16: Takeaways

- See `key_findings.md`.
- Not computed:
  - DLS par analysis [RD].
  - Uncertainty intervals for ranks [RI]. These need a bootstrap over matches, which is not in the pipeline.
  - External validation against selections or awards [RD].