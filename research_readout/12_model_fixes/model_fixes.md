# Model fixes (November 2026)

What was changed, why, and what moved. Before = the pre-fix model (`_scripts/reference/player_ratings_pre_fix.py`), run in full on the same balls. Numbers: `fix_before_after.csv`.

## Changes

| finding | change | constant |
|---|---|---|
| BUG-01 ball-19 look-ahead | the 18-ball window subtracts 0 before the innings has 18 balls | – |
| Pressure dominated by recent events | each term over its own SD, then weighted 0.60 / 0.25 / 0.15 | `PRESSURE_WEIGHTS` |
| Wickets-fallen bias | full expectation cell = ladder x phase x arm x wickets down (0-1, 2-3, 4-5, 6-7, 8+) | – |
| Small high-pressure samples | high-band n_eff floor 30 → 60 | `RANK_HIGH_BALLS` |
| Bowler clutch delivery basis | career economy on legal balls, same as the spell | – |
| Role normalisation | batter z = 0.5 within role + 0.5 pooled | `ROLE_BLEND` |

## What moved

- **Rankings.** Against the pre-fix model: batters Spearman 0.845, top-20 overlap 9/20; bowlers 0.785, 12/20. The pressure weighting alone is a change of that size: keeping every other fix but going back to raw-sum pressure (bug fixed) gives Spearman 0.836 for batters and 0.722 for bowlers against the official ranking.
- **Pressure.** Batter high-band balls after a recent wicket 99.9% → 75.6% (base rate 27.5%); bowler high-band balls after a boundary 100.0% → 86.7% (base rate 63.6%). Finals in the batter high band 26.1% → 86.4%.
- **Side effect (M-17).** Pace high-band balls in the powerplay 35.5% → 72.1%, at the death 28.4% → 10.5%. This follows from the existing bowler ball-difficulty table and is not tuned here.
- **Expectations.** The 8-9 down residual -0.345 → -0.044 runs per ball. Discrimination barely moves: xR MAE 1.3043 → 1.2986 (constant 1.3282), R² 0.0133 → 0.0159, xW AUC 0.5597 → 0.5601. Single-ball T20 outcomes are mostly noise; this limitation stays open (M-07).
- **Samples.** Top-10 bowlers with high n_eff < 60: 4 → 0. Ranked pools: batters 216 → 141, bowlers 226 → 143.
- **Clutch.** On the current high-band spells, 47.0% would beat their own rate on the old mixed basis; 43.5% do on the legal-ball basis.
- **Roles.** Top-20 batting mix (top/middle/lower): role-only 4/12/4, official blend 6/10/4, pooled 8/9/3; before the fixes role-only 6/7/7 and pooled 14/6/0.

## Why batters are normalised within roles (partly)

Batters are compared partly within their batting role because the roles are different jobs. An opener faces the new ball with no wickets down and is judged on building an innings; a finisher arrives at the death, often after a collapse, and is judged on scoring fast against set bowlers. A strike rate or average is not comparable across those jobs without some adjustment. Pooling every batter rewards the role whose numbers are easiest to post. A role-only z-score assumes each role is equally deep in talent. Neither is a finding about cricket. The 50/50 blend (ROLE_BLEND = 0.5) is a stated compromise between the two.

The evidence that this is a choice and not a discovery: the official ranking agrees with the role-only ranking at Spearman 0.991 and with the pooled ranking at 0.990, but the top-20 role mix changes visibly between them. After the wickets-down fix the role-only and pooled tables are much closer than before, which suggests part of what role normalisation was compensating for was the tail-end expectation bias.

## Pressure weights

The weights are a judgement, chosen from the table in `08_validation/pressure_weight_sensitivity.csv`. Lower situation weights keep the high band tied to recent events; higher ones push death bowling further out of the bowler high band. Chart: `10_charts/slide_04_high_pressure_meaning/pressure_weight_sensitivity.png`.