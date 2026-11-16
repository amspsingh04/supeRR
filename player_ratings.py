"""Batter and bowler pressure ratings from the silver files.

The notebook player_ratings.ipynb runs these steps and shows the tables.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEASONS = [2022, 2023, 2024, 2025, 2026]
WEIGHT = {year: 0.9 ** (2026 - year) for year in SEASONS}
W_SUM = float(sum(WEIGHT.values()))
BANDS = ["zero", "medium", "high"]
# Filled by score_batters and score_bowlers for the explanation site. The rating tables themselves are unchanged.
TRACES: dict = {}
# Seven shares summing to 1.00.
BASELINE_WEIGHT = 0.20
ZERO_WEIGHT = 0.10
MEDIUM_WEIGHT = 0.15
HIGH_WEIGHT = 0.20
CLUTCH_WEIGHT = 0.15
PEERS_WEIGHT = 0.10
CONSISTENCY_WEIGHT = 0.10
# A new player stays near 1500 until they have this many legal balls.
COLD_BALLS = 30.0
VENUE_BALLS = 2400.0
# A phase, arm, and ladder cell is pulled toward the coarser rate with this many balls.
# Emerging Teams and Rising Stars are a lower level than T20I. A ball there counts as half a ball.
LOWER_LEVEL_WEIGHT = 0.5
EXPECTATION_BALLS = 30.0
# Used only before any legal ball has been seen. Not fit on this file.
PRIOR_RUNS = 1.0
PRIOR_WICKET = 0.05
# Every z-score is taken on players with at least this many decay-weighted legal balls.
REFERENCE_BALLS = 30
# A recognized batter is anyone listed at 1 to 7. Numbers 8 to 11 are the tail.
RECOGNIZED_ORDER = 7
OCCASION = {
    "Final": 3.0,
    "Semi Final": 2.0,
    "Qualifier": 1.5,
    "Eliminator": 1.5,
    "Super 4": 1.3,
    "League": 1.0,
    "Others": 0.8,
}
# A super over is sudden death, so it is never below a knockout. A semi-final or final keeps its own weight.
SUPER_OVER_OCCASION = 1.5
SUPER_OVER_BALLS = 6
# Each pressure part is put over its own spread, then weighted. The match situation leads; the last balls follow.
PRESSURE_WEIGHTS = {"situation": 0.60, "shock": 0.25, "run_of_play": 0.15}
# A batting z-score is this much the comparison inside the role and the rest the comparison with every batter.
ROLE_BLEND = 0.5
# To be ranked: this many decay-weighted legal balls, and this many of them in the high band.
RANK_BALLS = 120
RANK_HIGH_BALLS = 60


def find_silver() -> Path:
    start = Path.cwd().resolve()
    for folder in [start, *start.parents]:
        silver = folder / "silver"
        if (silver / "ball_by_ball.csv").exists() and (silver / "matches.csv").exists():
            return silver
    raise FileNotFoundError("silver CSVs were not found from the working directory upward")


def shrink(value: pd.Series, count: pd.Series, prior: pd.Series | float, strength: float) -> pd.Series:
    count = count.reindex(value.index).fillna(0.0).astype(float)
    if np.isscalar(prior):
        prior = pd.Series(float(prior), index=value.index)
    else:
        prior = prior.reindex(value.index).astype(float)
    return (count * value.astype(float) + strength * prior) / (count + strength)


def zscore(value: pd.Series, reference: pd.Series) -> pd.Series:
    sample = value[reference.reindex(value.index).fillna(False).astype(bool)]
    center = sample.mean()
    spread = sample.std(ddof=0)
    if pd.isna(spread) or spread == 0:
        return pd.Series(0.0, index=value.index)
    # A cap keeps one short passage from outweighing the other seven terms.
    return ((value - center) / spread).clip(-3, 3)


def zscore_within(value: pd.Series, groups: pd.Series, reference: pd.Series) -> pd.Series:
    """The same z-score, taken inside each group so one role is not the scale for the others."""
    out = pd.Series(0.0, index=value.index)
    labels = groups.reindex(value.index).fillna("unknown")
    for _, index in labels.groupby(labels, sort=False).groups.items():
        out.loc[index] = zscore(value.loc[index], reference).to_numpy()
    return out


def zscore_blend(value: pd.Series, groups: pd.Series, reference: pd.Series) -> pd.Series:
    """A batting z-score: ROLE_BLEND of the role comparison, the rest against every batter."""
    return ROLE_BLEND * zscore_within(value, groups, reference) + (1 - ROLE_BLEND) * zscore(value, reference)


def _row_weights(frame: pd.DataFrame) -> pd.Series:
    """Season decay times the level weight. A lower-T20 ball counts as half."""
    weights = frame["season"].map(WEIGHT).astype(float)
    if "level_weight" in frame.columns:
        weights = weights * frame["level_weight"].astype(float)
    return weights


def career_rate(frame: pd.DataFrame, player_ids: pd.Index, player_col: str, value_col: str) -> pd.Series:
    """Decay-weighted mean of the rows a player has. A season with no rows is left out."""
    if frame.empty:
        return pd.Series(0.0, index=player_ids)
    weights = _row_weights(frame)
    values = frame[value_col].astype(float) * weights
    numer = values.groupby(frame[player_col]).sum()
    denom = weights.groupby(frame[player_col]).sum()
    rate = numer / denom.replace(0, np.nan)
    return rate.reindex(player_ids).fillna(0.0)


def weighted_count(frame: pd.DataFrame, player_col: str, player_ids: pd.Index) -> pd.Series:
    if frame.empty:
        return pd.Series(0.0, index=player_ids)
    weights = _row_weights(frame)
    counted = weights.groupby(frame[player_col]).sum()
    return counted.reindex(player_ids).fillna(0.0)


def _weighted_mean(frame: pd.DataFrame, player_col: str, value_col: str) -> tuple[pd.Series, pd.Series]:
    """Mean of innings scores. A lower-T20 innings counts as half an innings."""
    weights = frame["level_weight"].astype(float) if "level_weight" in frame.columns else pd.Series(1.0, index=frame.index)
    numer = (frame[value_col].astype(float) * weights).groupby(frame[player_col]).sum()
    denom = weights.groupby(frame[player_col]).sum()
    return numer / denom.replace(0, np.nan), denom


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    silver = find_silver()
    balls = pd.read_csv(silver / "ball_by_ball.csv")
    matches = pd.read_csv(silver / "matches.csv")
    comps = pd.read_csv(silver / "competitions.csv")
    keep = matches.merge(
        comps[["comp_id", "season", "comp_group", "comp_name"]],
        on="comp_id",
        how="left",
        validate="many_to_one",
    )
    context = [
        "match_id", "match_date", "season", "comp_id", "comp_group", "comp_name", "stage", "venue_id",
        "home_team_id", "away_team_id", "knock_out", "win_team_id", "revised_target",
        "first_innings_balls", "second_innings_balls", "is_reduced",
    ]
    out = balls.merge(keep[context], on="match_id", how="left", validate="many_to_one")
    if len(out) != len(balls):
        raise AssertionError("match lookup changed the delivery count")
    if out["season"].isna().any():
        raise AssertionError("a delivery has no season")
    return out, keep, comps


def _phase_labels(position: pd.Series, length: pd.Series) -> pd.Series:
    powerplay_end = np.rint(0.30 * length)
    death_start = np.rint(0.80 * length)
    phase = np.full(len(position), "middle", dtype=object)
    phase[position.to_numpy() <= powerplay_end.to_numpy()] = "powerplay"
    phase[position.to_numpy() > death_start.to_numpy()] = "death"
    return pd.Series(phase, index=position.index)


def add_situation(balls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tag every ball, super overs included. Ratings use the legal rows."""
    work = balls.copy()
    work["is_super_over"] = work["is_super_over"].astype(bool)
    work["bat_runs"] = work["runs"].fillna(0.0)
    first_extra = work["extras1_runs"].fillna(0.0)
    second_extra = work["extras_2_runs"].fillna(0.0)
    work["extra_runs"] = first_extra + second_extra
    work["team_run"] = work["bat_runs"] + work["extra_runs"]
    label = work["extras_label"].fillna("ordinary")
    # Every run off a wide is the bowler's. Off a no-ball only the no-ball run and bat runs are; byes run off it are not.
    bowler_extra = np.select(
        [label.eq("wide"), label.isin(["no-ball", "other"])],
        [first_extra + second_extra, first_extra],
        0.0,
    )
    free = label.isin(["bye", "leg-bye", "penalty"])
    work["conceded"] = np.where(free, 0.0, work["bat_runs"] + bowler_extra)
    work["is_legal"] = work["is_legal"].astype(bool)
    work["wicket_flag"] = work["is_wicket"].fillna(False).astype(bool).astype(int)
    work = work.sort_values(["match_id", "innings", "innings_ball_num"], kind="mergesort")
    grouped = work.groupby(["match_id", "innings"], sort=False)
    work["runs_before"] = grouped["team_run"].cumsum() - work["team_run"]
    work["wickets_before"] = grouped["wicket_flag"].cumsum() - work["wicket_flag"]
    work["legal_before"] = grouped["is_legal"].cumsum() - work["is_legal"].astype(int)
    work["ball_position"] = (work["legal_before"] + work["is_legal"].astype(int)).clip(lower=1)

    length = np.where(
        work["innings"].eq(1),
        work["first_innings_balls"],
        work["second_innings_balls"],
    )
    work["innings_length"] = pd.Series(length, index=work.index).fillna(120).clip(lower=1)
    work.loc[work["is_super_over"], "innings_length"] = SUPER_OVER_BALLS
    work["phase"] = _phase_labels(work["ball_position"], work["innings_length"])
    # Every super-over ball is a death ball.
    work.loc[work["is_super_over"], "phase"] = "death"

    work["ladder"] = np.where(work["comp_group"].eq("IPL"), "IPL", np.where(work["comp_group"].eq("T20I"), "T20I", "T20"))
    work["level_weight"] = np.where(work["ladder"].eq("T20"), LOWER_LEVEL_WEIGHT, 1.0)
    legal = work.loc[work["is_legal"]].copy()
    legal["n"] = legal["legal_before"] + 1
    legal["left"] = (legal["innings_length"] - legal["n"] + 1).clip(lower=0)
    legal["phase"] = _phase_labels(legal["n"], legal["innings_length"])
    legal.loc[legal["is_super_over"], "phase"] = "death"

    first_total = work.loc[work["innings"].eq(1)].groupby("match_id")["team_run"].sum()
    super_total = work.loc[work["innings"].eq(3)].groupby("match_id")["team_run"].sum()
    legal["target"] = legal["revised_target"]
    missing_target = legal["target"].isna() | legal["target"].le(0)
    # An ordinary chase needs one more than the first innings. A DLS target is used as supplied.
    legal.loc[missing_target, "target"] = legal.loc[missing_target, "match_id"].map(first_total) + 1
    # The second super over chases one more than the first super over.
    super_chase = legal["innings"].eq(4)
    legal.loc[super_chase, "target"] = legal.loc[super_chase, "match_id"].map(super_total) + 1
    reduced_without_target = legal["is_reduced"].fillna(False).astype(bool) & missing_target & ~super_chase
    chase = legal["innings"].isin([2, 4]) & legal["target"].notna() & legal["left"].gt(0) & ~reduced_without_target
    needed = (legal["target"] - legal["runs_before"]).clip(lower=0)
    legal["rrr"] = np.where(chase, needed / (legal["left"] / 6.0), np.nan)
    legal["crr"] = np.where(legal["n"].gt(1), legal["runs_before"] / ((legal["n"] - 1) / 6.0), np.nan)
    legal = _attach_pressure(legal)
    legal["striker_out"] = legal["wicket_flag"].eq(1) & legal["dismissed_player_id"].eq(legal["striker_id"])
    legal["bowler_wicket"] = legal["is_bowler_wicket"].fillna(False).astype(bool)
    legal["charged_runs"] = legal["conceded"]
    legal["match_date"] = pd.to_datetime(legal["match_date"])
    work["match_date"] = pd.to_datetime(work["match_date"])
    return work, legal


def _dead_series_matches(legal: pd.DataFrame) -> set[int]:
    """A bilateral match is a dead rubber once one side has already won the series."""
    series = legal.loc[legal["stage"].eq("Others"), ["comp_id", "match_id", "match_date", "win_team_id", "home_team_id", "away_team_id"]]
    series = series.drop_duplicates("match_id")
    dead: set[int] = set()
    for _, frame in series.groupby("comp_id"):
        ordered = frame.sort_values(["match_date", "match_id"])
        needed = len(ordered) // 2 + 1
        wins: dict[int, int] = {}
        for row in ordered.itertuples(index=False):
            if wins.get(int(row.home_team_id), 0) >= needed or wins.get(int(row.away_team_id), 0) >= needed:
                dead.add(int(row.match_id))
            if pd.notna(row.win_team_id):
                winner = int(row.win_team_id)
                wins[winner] = wins.get(winner, 0) + 1
    return dead


def _competition_weight(legal: pd.DataFrame) -> pd.Series:
    name = legal["comp_name"].fillna("")
    minor = name.str.contains("Emerging|Rising", case=False, regex=True) | legal["comp_group"].eq("Other T20")
    return pd.Series(np.where(minor, 0.7, 1.0), index=legal.index)


def _ball_difficulty(legal: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Each skill's ball is scaled from 0 to 1. Wickets down raise the batter and lower the bowler."""
    phase = legal["phase"]
    batter_phase = phase.map({"powerplay": 0.25, "middle": 0.10, "death": 0.40}).fillna(0.10)
    recognized = legal["batting_order"].notna() & legal["batting_order"].le(RECOGNIZED_ORDER)
    bowler_phase = phase.map({"powerplay": 0.32, "middle": 0.24}).fillna(0.24)
    bowler_phase = bowler_phase.where(~phase.eq("death"), np.where(recognized, 0.32, 0.14))
    wickets = legal["wickets_before"].to_numpy()
    batter_wickets = np.where(wickets <= 1, 0.0, np.where(wickets <= 4, 0.15, 0.30))
    bowler_wickets = np.where(wickets <= 1, 0.0, np.where(wickets <= 4, -0.10, -0.25))
    rate = legal["rrr"].to_numpy(dtype=float)
    chase = legal["innings"].isin([2, 4]) & np.isfinite(rate)
    rate_term = np.where(~chase, 0.0, np.where(rate >= 12, 0.30, np.where(rate >= 8, 0.15, 0.0)))
    batter = pd.Series(np.clip(batter_phase.to_numpy() + batter_wickets + rate_term, 0.0, 1.0), index=legal.index)
    bowler = pd.Series(np.clip(bowler_phase.to_numpy() + bowler_wickets + rate_term, 0.0, 1.0), index=legal.index)
    return batter, bowler


def _shock_and_delta(legal: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Last six balls, and the last six against the previous eighteen. Current ball is excluded."""
    ordered = legal.sort_values(["match_id", "innings", "n"], kind="mergesort")
    real_wicket = ordered["wicket_flag"].eq(1) & ~ordered["dismissal_type"].isin(["Retire Out", "Obstructing the field"])
    four = ordered["bat_runs"].eq(4)
    six = ordered["bat_runs"].ge(6)
    dot = ordered["bat_runs"].eq(0) & ~real_wicket
    shock_batter = np.zeros(len(ordered))
    shock_bowler = np.zeros(len(ordered))
    gap_wickets = np.full(len(ordered), np.nan)
    gap_runs = np.full(len(ordered), np.nan)
    offset = 0
    for _, frame in ordered.groupby(["match_id", "innings"], sort=False):
        wickets = real_wicket.loc[frame.index].to_numpy(dtype=float)
        fours = four.loc[frame.index].to_numpy(dtype=float)
        sixes = six.loc[frame.index].to_numpy(dtype=float)
        dots = dot.loc[frame.index].to_numpy(dtype=float)
        runs = frame["bat_runs"].to_numpy(dtype=float)
        count = len(frame)
        wicket_sum = np.cumsum(wickets)
        four_sum = np.cumsum(fours)
        six_sum = np.cumsum(sixes)
        dot_sum = np.cumsum(dots)
        run_sum = np.cumsum(runs)
        for position in range(6, count):
            end = position - 1
            before = end - 6
            wicket_6 = wicket_sum[end] - (wicket_sum[before] if before >= 0 else 0.0)
            four_6 = four_sum[end] - (four_sum[before] if before >= 0 else 0.0)
            six_6 = six_sum[end] - (six_sum[before] if before >= 0 else 0.0)
            dot_6 = dot_sum[end] - (dot_sum[before] if before >= 0 else 0.0)
            # A wicket is the large step. A dot is the small one. Three wickets still reach 1.
            shock_batter[offset + position] = min(1.0, 0.33 * wicket_6 + 0.05 * dot_6)
            # A six is the large step. A four is the small one. Three sixes still reach 1.
            shock_bowler[offset + position] = min(1.0, 0.33 * six_6 + 0.12 * four_6)
            if position >= 18:
                run_6 = run_sum[end] - run_sum[end - 6]
                start = end - 18
                wicket_18 = wicket_sum[end] - (wicket_sum[start] if start >= 0 else 0.0)
                run_18 = run_sum[end] - (run_sum[start] if start >= 0 else 0.0)
                gap_wickets[offset + position] = wicket_6 / 6.0 - wicket_18 / 18.0
                gap_runs[offset + position] = run_6 / 6.0 - run_18 / 18.0
        offset += count
    gap_wickets = pd.Series(gap_wickets, index=ordered.index)
    gap_runs = pd.Series(gap_runs, index=ordered.index)
    shock_batter = pd.Series(shock_batter, index=ordered.index)
    shock_bowler = pd.Series(shock_bowler, index=ordered.index)
    wicket_scale = float(gap_wickets.std(ddof=0))
    run_scale = float(gap_runs.std(ddof=0))
    if not np.isfinite(wicket_scale) or wicket_scale == 0:
        wicket_scale = 1.0
    if not np.isfinite(run_scale) or run_scale == 0:
        run_scale = 1.0
    delta_batter = (gap_wickets / wicket_scale).clip(-0.5, 1.0).fillna(0.0)
    delta_bowler = (gap_runs / run_scale).clip(-0.5, 1.0).fillna(0.0)
    return (
        shock_batter.reindex(legal.index).to_numpy(dtype=float),
        shock_bowler.reindex(legal.index).to_numpy(dtype=float),
        delta_batter.reindex(legal.index).to_numpy(dtype=float),
        delta_bowler.reindex(legal.index).to_numpy(dtype=float),
    )


def _cut_band(pressure: pd.Series) -> pd.Series:
    """High is the top fifth of this pressure. Medium is the next 30 percent."""
    high_cut = float(pressure.quantile(0.80))
    medium_cut = float(pressure.quantile(0.50))
    labels = np.where(pressure >= high_cut, "high", np.where(pressure >= medium_cut, "medium", "zero"))
    return pd.Series(labels, index=pressure.index)


def _cut_band_within(pressure: pd.Series, groups: pd.Series) -> pd.Series:
    """The same top-fifth cut inside each bowling type, so pace and spin are not split by role."""
    labels = pd.Series("zero", index=pressure.index, dtype=object)
    for _, index in pressure.groupby(groups.fillna("unknown"), sort=False).groups.items():
        labels.loc[index] = _cut_band(pressure.loc[index]).to_numpy()
    return labels


def _attach_pressure(legal: pd.DataFrame) -> pd.DataFrame:
    """Occasion, competition, and the ball, plus the shock and the break in rhythm."""
    dead = _dead_series_matches(legal)
    occasion = legal["stage"].map(OCCASION).fillna(1.0).astype(float)
    occasion = occasion.where(~legal["match_id"].isin(dead), 0.4)
    occasion = occasion.where(~legal["is_super_over"], np.maximum(occasion, SUPER_OVER_OCCASION))
    competition = _competition_weight(legal)
    batter_ball, bowler_ball = _ball_difficulty(legal)
    shock_batter, shock_bowler, delta_batter, delta_bowler = _shock_and_delta(legal)
    legal = legal.copy()
    legal["shock_bat"] = shock_batter
    legal["shock_bowl"] = shock_bowler
    legal["delta_bat"] = delta_batter
    legal["delta_bowl"] = delta_bowler
    legal["occasion"] = occasion.to_numpy()
    legal["competition"] = competition.to_numpy()
    legal["ball_bat"] = batter_ball.to_numpy()
    legal["ball_bowl"] = bowler_ball.to_numpy()
    return _combine_pressure(legal)


def _combine_pressure(frame: pd.DataFrame) -> pd.DataFrame:
    """Situation, shock, and run of play, each over its own spread, weighted, then cut into bands."""
    for side in ("bat", "bowl"):
        parts = {
            "situation": frame["occasion"] * frame["competition"] * frame[f"ball_{side}"],
            "shock": frame[f"shock_{side}"],
            "run_of_play": frame[f"delta_{side}"],
        }
        total = pd.Series(0.0, index=frame.index)
        for name, part in parts.items():
            spread = float(part.std(ddof=0))
            if not np.isfinite(spread) or spread == 0:
                spread = 1.0
            total = total + PRESSURE_WEIGHTS[name] * part / spread
        frame[f"situation_{side}"] = parts["situation"]
        frame[f"pressure_{side}"] = total
    frame["band"] = _cut_band(frame["pressure_bat"])
    frame["band_bowl"] = _cut_band_within(frame["pressure_bowl"], frame["pace_or_spin"])
    return frame


def band_summary(legal: pd.DataFrame) -> pd.DataFrame:
    counts = legal["band"].value_counts().reindex(BANDS).fillna(0).astype(int)
    frame = counts.rename("balls").to_frame()
    frame["share"] = frame["balls"] / frame["balls"].sum()
    return frame


def expectation_tables(legal: pd.DataFrame) -> tuple[dict, dict, float]:
    rho = float(legal["bat_runs"].sum() / len(legal))
    grouped = legal.groupby(["phase", "pace_or_spin"], sort=False)
    mu, p0 = {}, {}
    for key, frame in grouped:
        mu[key] = float(frame["bat_runs"].mean())
        rate = float(frame["bowler_wicket"].mean())
        p0[key] = float(np.clip(rate, 0.002, 0.40))
    phase_mu = legal.groupby("phase")["bat_runs"].mean().to_dict()
    phase_p0 = legal.groupby("phase")["bowler_wicket"].mean().to_dict()
    global_mu = float(legal["bat_runs"].mean())
    global_p0 = float(np.clip(legal["bowler_wicket"].mean(), 0.002, 0.40))

    def lookup(table, phase, arm, phase_table, default):
        if (phase, arm) in table:
            return table[(phase, arm)]
        if phase in phase_table:
            return float(phase_table[phase])
        return default

    mu_lookup = {(phase, arm): lookup(mu, phase, arm, phase_mu, global_mu) for phase, arm in mu}
    p0_lookup = {(phase, arm): lookup(p0, phase, arm, phase_p0, global_p0) for phase, arm in p0}
    # Keep the fallbacks available for any unseen pair.
    mu_lookup[("fallback", "fallback")] = global_mu
    p0_lookup[("fallback", "fallback")] = global_p0
    return mu_lookup, p0_lookup, rho


def venue_ratings(legal: pd.DataFrame, rho: float) -> pd.Series:
    grouped = legal.groupby("venue_id")["bat_runs"]
    count = grouped.size()
    rate = grouped.mean()
    rating = 1500 + 1000 * (count / (count + 2400)) * (rate - rho)
    return rating


def _logit(probability: float) -> float:
    probability = min(max(probability, 1e-4), 1 - 1e-4)
    return float(np.log(probability / (1 - probability)))


def _pulled_to_mean(raw: float, balls_seen: int) -> float:
    """A short career stays near 1500. A long career uses the raw rating."""
    return (balls_seen * raw + COLD_BALLS * 1500.0) / (balls_seen + COLD_BALLS)


def _ground_key(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return int(value)


def _add_expected_shock(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the last six balls' wickets above xW, and charged runs above xR, to the shock. The current ball is excluded."""
    ordered = frame.sort_values(["match_id", "innings", "n"], kind="mergesort")
    wickets = ordered["bowler_wicket"].fillna(False).astype(float).to_numpy()
    runs = ordered["charged_runs"].to_numpy(dtype=float)
    expected_wickets = ordered["x_wicket"].to_numpy(dtype=float)
    expected_runs = ordered["x_runs_bowl"].to_numpy(dtype=float)
    excess_wickets = np.zeros(len(ordered))
    excess_runs = np.zeros(len(ordered))
    offset = 0
    for _, part in ordered.groupby(["match_id", "innings"], sort=False):
        count = len(part)
        wicket_gap = np.cumsum(wickets[offset:offset + count] - expected_wickets[offset:offset + count])
        run_gap = np.cumsum(runs[offset:offset + count] - expected_runs[offset:offset + count])
        for position in range(6, count):
            end = position - 1
            before = end - 6
            excess_wickets[offset + position] = wicket_gap[end] - (wicket_gap[before] if before >= 0 else 0.0)
            excess_runs[offset + position] = run_gap[end] - (run_gap[before] if before >= 0 else 0.0)
        offset += count
    wicket_scale = float(pd.Series(excess_wickets).std(ddof=0))
    run_scale = float(pd.Series(excess_runs).std(ddof=0))
    if not np.isfinite(wicket_scale) or wicket_scale == 0:
        wicket_scale = 1.0
    if not np.isfinite(run_scale) or run_scale == 0:
        run_scale = 1.0
    extra_wickets = pd.Series(excess_wickets / wicket_scale, index=ordered.index).clip(-0.5, 1.0)
    extra_runs = pd.Series(excess_runs / run_scale, index=ordered.index).clip(-0.5, 1.0)
    frame = frame.copy()
    frame["shock_bat"] = (frame["shock_bat"] + extra_wickets.reindex(frame.index).fillna(0.0)).clip(-0.5, 1.0)
    frame["shock_bowl"] = (frame["shock_bowl"] + extra_runs.reindex(frame.index).fillna(0.0)).clip(-0.5, 1.0)
    return _combine_pressure(frame)


def _wicket_bucket(wickets_down: float) -> str:
    """Wickets already down, in the steps where scoring and dismissal rates change."""
    if wickets_down <= 1:
        return "0-1"
    if wickets_down <= 3:
        return "2-3"
    if wickets_down <= 5:
        return "4-5"
    if wickets_down <= 7:
        return "6-7"
    return "8+"


def _expectation_keys(phase: str, arm: str, ladder: str, wickets: str) -> tuple[tuple, ...]:
    """Coarse to fine, inside one ladder. IPL, T20I, and lower T20 do not share a base rate. The last cell adds wickets down."""
    return (
        ("all", ladder),
        ("phase", ladder, phase),
        ("phase_arm", ladder, phase, arm),
        ("full", ladder, phase, arm, wickets),
    )


def _cell_mean(cells: dict[tuple, tuple[float, int]], key_chain: tuple[tuple, ...], prior: float) -> float:
    mean = prior
    for key in key_chain:
        total, count = cells.get(key, (0.0, 0))
        mean = (total + EXPECTATION_BALLS * mean) / (count + EXPECTATION_BALLS)
    return mean


def _add_cell(cells: dict[tuple, tuple[float, int]], key_chain: tuple[tuple, ...], value: float) -> None:
    for key in key_chain:
        total, count = cells.get(key, (0.0, 0))
        cells[key] = (total + value, count + 1)


def run_elo(legal: pd.DataFrame, venues: pd.Series | None = None, k_run: float = 4.0, k_wicket: float = 16.0, k_team: float = 20.0) -> pd.DataFrame:
    del venues  # Venue strength is fit from balls already bowled, inside this walk.
    frame = legal.sort_values(["match_date", "match_id", "innings", "innings_ball_num"], kind="mergesort")
    bat_rating: dict[tuple[int, str], float] = {}
    bowl_rating: dict[tuple[int, str], float] = {}
    bat_seen: dict[tuple[int, str], int] = {}
    bowl_seen: dict[tuple[int, str], int] = {}
    team_rating: dict[tuple[int, str], float] = {}
    ground_runs: dict[int, float] = {}
    ground_balls: dict[int, int] = {}
    seen_runs = 0.0
    seen_balls = 0
    run_cells: dict[tuple, tuple[float, int]] = {}
    charged_cells: dict[tuple, tuple[float, int]] = {}
    wicket_cells: dict[tuple, tuple[float, int]] = {}
    e_bat = np.zeros(len(frame))
    e_bowl = np.zeros(len(frame))
    x_runs = np.zeros(len(frame))
    x_runs_bowl = np.zeros(len(frame))
    x_wicket = np.zeros(len(frame))
    bat_after = np.zeros(len(frame))
    bowl_after = np.zeros(len(frame))

    match_id = frame["match_id"].to_numpy()
    ladder = frame["ladder"].to_numpy()
    striker = frame["striker_id"].to_numpy()
    bowler = frame["bowler_id"].to_numpy()
    batting_side = frame["batting_team_id"].to_numpy()
    bowling_side = frame["bowling_team_id"].to_numpy()
    home = frame["home_team_id"].to_numpy()
    away = frame["away_team_id"].to_numpy()
    winner = frame["win_team_id"].to_numpy()
    phase = frame["phase"].to_numpy()
    arm = frame["pace_or_spin"].to_numpy()
    wicket_bucket = [_wicket_bucket(value) for value in frame["wickets_before"].to_numpy(dtype=float)]
    venue_id = frame["venue_id"].to_numpy()
    runs = frame["bat_runs"].to_numpy(dtype=float)
    charged = frame["charged_runs"].to_numpy(dtype=float)
    dismissed = frame["striker_out"].to_numpy(dtype=bool)
    bowler_wicket = frame["bowler_wicket"].to_numpy(dtype=bool)

    row = 0
    total = len(frame)
    while row < total:
        stop = row + 1
        this_match = match_id[row]
        while stop < total and match_id[stop] == this_match:
            stop += 1
        this_ladder = ladder[row]
        home_id = int(home[row])
        away_id = int(away[row])
        pre_home = team_rating.get((home_id, this_ladder), 1500.0)
        pre_away = team_rating.get((away_id, this_ladder), 1500.0)
        pre_side = {home_id: pre_home, away_id: pre_away}
        for cursor in range(row, stop):
            striker_id = int(striker[cursor])
            bowler_id = int(bowler[cursor])
            bat_key = (striker_id, this_ladder)
            bowl_key = (bowler_id, this_ladder)
            batter_raw = bat_rating.get(bat_key, 1500.0)
            bowler_raw = bowl_rating.get(bowl_key, 1500.0)
            batter_now = _pulled_to_mean(batter_raw, bat_seen.get(bat_key, 0))
            bowler_now = _pulled_to_mean(bowler_raw, bowl_seen.get(bowl_key, 0))
            ground = _ground_key(venue_id[cursor])
            ground_n = ground_balls.get(ground, 0) if ground is not None else 0
            if ground is None or ground_n == 0 or seen_balls == 0:
                ground_now = 1500.0
            else:
                ground_rate = ground_runs[ground] / ground_n
                historic = seen_runs / seen_balls
                ground_now = 1500.0 + 1000.0 * (ground_n / (ground_n + VENUE_BALLS)) * (ground_rate - historic)
            gap = (
                0.15 * (batter_now - bowler_now) / 400.0
                + 0.05 * (pre_side.get(int(batting_side[cursor]), 1500.0) - pre_side.get(int(bowling_side[cursor]), 1500.0)) / 400.0
                + 0.10 * (ground_now - 1500.0) / 400.0
            )
            keys = _expectation_keys(str(phase[cursor]), str(arm[cursor]), str(this_ladder), wicket_bucket[cursor])
            mean_runs = _cell_mean(run_cells, keys, PRIOR_RUNS)
            mean_charged = _cell_mean(charged_cells, keys, PRIOR_RUNS)
            wicket_rate = min(max(_cell_mean(wicket_cells, keys, PRIOR_WICKET), 0.002), 0.40)
            expected_runs = min(max(mean_runs * np.exp(gap), 0.0), 6.0)
            expected_charged = min(max(mean_charged * np.exp(gap), 0.0), 6.0)
            expected_wicket = 1.0 / (1.0 + np.exp(-(_logit(wicket_rate) - gap)))
            expected_wicket = min(max(expected_wicket, 0.002), 0.40)
            x_runs[cursor] = expected_runs
            x_runs_bowl[cursor] = expected_charged
            x_wicket[cursor] = expected_wicket
            out_flag = 1.0 if dismissed[cursor] else 0.0
            wicket_flag = 1.0 if bowler_wicket[cursor] else 0.0
            e_bat[cursor] = (runs[cursor] - expected_runs) - 4.0 * (out_flag - expected_wicket)
            e_bowl[cursor] = (expected_charged - charged[cursor]) + 4.0 * (wicket_flag - expected_wicket)
            bat_rating[bat_key] = batter_raw + k_run * (runs[cursor] - expected_runs) - k_wicket * (out_flag - expected_wicket)
            bowl_rating[bowl_key] = bowler_raw - k_run * (charged[cursor] - expected_charged) + k_wicket * (wicket_flag - expected_wicket)
            bat_after[cursor] = bat_rating[bat_key]
            bowl_after[cursor] = bowl_rating[bowl_key]
            _add_cell(run_cells, keys, float(runs[cursor]))
            _add_cell(charged_cells, keys, float(charged[cursor]))
            _add_cell(wicket_cells, keys, wicket_flag)
            bat_seen[bat_key] = bat_seen.get(bat_key, 0) + 1
            bowl_seen[bowl_key] = bowl_seen.get(bowl_key, 0) + 1
            if ground is not None:
                ground_runs[ground] = ground_runs.get(ground, 0.0) + runs[cursor]
                ground_balls[ground] = ground_n + 1
                seen_runs += runs[cursor]
                seen_balls += 1
        win_value = winner[row]
        no_winner = pd.isna(win_value)

        def result_for(side: int) -> float:
            if no_winner:
                return 0.5
            return 1.0 if int(win_value) == side else 0.0

        for side, prior, opponent_prior in (
            (home_id, pre_home, pre_away),
            (away_id, pre_away, pre_home),
        ):
            expected = 1.0 / (1.0 + 10 ** ((opponent_prior - prior) / 400.0))
            team_rating[(side, this_ladder)] = prior + k_team * (result_for(side) - expected)
        row = stop

    scored = frame.copy()
    scored["e_bat"] = e_bat
    scored["e_bowl"] = e_bowl
    scored["x_runs"] = x_runs
    scored["x_runs_bowl"] = x_runs_bowl
    scored["x_wicket"] = x_wicket
    scored["batter_rating_after"] = bat_after
    scored["bowler_rating_after"] = bowl_after
    scored = _add_expected_shock(scored)
    bat_values = pd.Series(bat_rating)
    bowl_values = pd.Series(bowl_rating)
    summary = {
        "k_run": k_run,
        "k_wicket": k_wicket,
        "k_team": k_team,
        "batter_elo_min": float(bat_values.min()),
        "batter_elo_max": float(bat_values.max()),
        "batter_elo_sd": float(bat_values.std(ddof=0)),
        "bowler_elo_min": float(bowl_values.min()),
        "bowler_elo_max": float(bowl_values.max()),
        "bowler_elo_sd": float(bowl_values.std(ddof=0)),
        "team_elo_min": float(min(team_rating.values())),
        "team_elo_max": float(max(team_rating.values())),
        "grounds": int(len(ground_balls)),
    }
    scored.attrs["elo_summary"] = summary
    return scored


def fit_elo(legal: pd.DataFrame, venues: pd.Series | None = None) -> pd.DataFrame:
    scored = run_elo(legal, venues)
    summary = scored.attrs["elo_summary"]
    spread_ok = (
        summary["batter_elo_sd"] <= 250
        and summary["bowler_elo_sd"] <= 250
        and summary["batter_elo_min"] >= 600
        and summary["bowler_elo_min"] >= 600
        and summary["batter_elo_max"] <= 2800
        and summary["bowler_elo_max"] <= 2800
    )
    summary["step_sizes"] = "as written" if spread_ok else "halved once, ratings had reached the edges"
    if not spread_ok:
        scored = run_elo(legal, venues, k_run=2.0, k_wicket=8.0, k_team=10.0)
        summary = scored.attrs["elo_summary"]
        summary["step_sizes"] = "halved once, ratings had reached the edges"
        scored.attrs["elo_summary"] = summary
    return scored


def _names(frame: pd.DataFrame, id_col: str, name_col: str) -> pd.Series:
    ordered = frame.sort_values("match_date", kind="mergesort")
    return ordered.groupby(id_col)[name_col].last()


def _mode(series: pd.Series):
    clean = series.dropna()
    if clean.empty:
        return np.nan
    return clean.mode().iloc[0]


def _batting_role(order) -> str:
    if pd.isna(order):
        return "unknown"
    if order <= 3:
        return "top order"
    if order <= 6:
        return "middle order"
    return "lower order"


def _side_z(metrics: np.ndarray, index: int, higher_better: bool) -> tuple[float, float]:
    others = np.delete(metrics, index)
    if len(others) < 2:
        return np.nan, np.nan
    center = float(others.mean())
    spread = float(others.std(ddof=0))
    if spread == 0:
        return 0.0, center
    gap = (metrics[index] - center) / spread
    signed = gap if higher_better else -gap
    return float(min(max(signed, -3.0), 3.0)), center


def innings_comparisons(spells: pd.DataFrame, player_col: str, metric: str, higher_better: bool) -> pd.DataFrame:
    qualified = spells.loc[spells["balls"] >= 6].copy()
    buckets = {(match, innings): frame for (match, innings), frame in qualified.groupby(["match_id", "innings"], sort=False)}
    rows = []
    for (match, innings), frame in buckets.items():
        opposite = buckets.get((match, {1: 2, 2: 1, 3: 4, 4: 3}.get(innings, -1)))
        values = frame[metric].to_numpy(dtype=float)
        players = frame[player_col].to_numpy()
        seasons = frame["season"].to_numpy()
        dates = frame["match_date"].to_numpy()
        for position, player in enumerate(players):
            team_z, team_mean = _side_z(values, position, higher_better)
            opp_z = np.nan
            opp_mean = np.nan
            if opposite is not None and len(opposite) >= 2:
                opp_values = opposite[metric].to_numpy(dtype=float)
                opp_mean = float(opp_values.mean())
                spread = float(opp_values.std(ddof=0))
                if spread == 0:
                    opp_z = 0.0
                else:
                    gap = (values[position] - opp_mean) / spread
                    signed = gap if higher_better else -gap
                    opp_z = float(min(max(signed, -3.0), 3.0))
            available = [item for item in (team_z, opp_z) if pd.notna(item)]
            combined = float(np.mean(available)) if available else np.nan
            rows.append({
                player_col: player,
                "match_id": match,
                "innings": innings,
                "season": int(seasons[position]),
                "match_date": dates[position],
                "metric": float(values[position]),
                "z_team": team_z,
                "z_opp": opp_z,
                "z_passage": combined,
                "team_mean": team_mean,
                "opp_mean": opp_mean,
            })
    return pd.DataFrame(rows)


def passage_label(row: pd.Series, career_metric: float, higher_better: bool) -> str:
    beat_self = row["metric"] > career_metric if higher_better else row["metric"] < career_metric
    if pd.notna(row["z_team"]) and row["z_team"] > 0.5 and beat_self:
        return "stood out"
    if pd.notna(row["team_mean"]) and pd.notna(row["opp_mean"]):
        if abs(row["metric"] - row["opp_mean"]) <= abs(row["metric"] - row["team_mean"]):
            return "matched the other side"
    if pd.notna(row["z_team"]) and abs(row["z_team"]) <= 0.5:
        return "in line"
    return "below the side"


def consistency_parts(match_values: pd.DataFrame, player_col: str, value_col: str, players: pd.Index, reference: pd.Series, groups: pd.Series | None = None) -> pd.DataFrame:
    """The match spread that enters the consistency z-score, before that z-score is taken."""
    if "level_weight" in match_values.columns:
        counts = pd.Series(0.0, index=players)
        spreads = pd.Series(np.nan, index=players)
        for player, group in match_values.groupby(player_col, sort=False):
            weights = group["level_weight"].to_numpy(dtype=float)
            values = group[value_col].to_numpy(dtype=float)
            total = float(weights.sum())
            counts.loc[player] = total
            if total <= 0 or len(values) == 0:
                continue
            center = float(np.average(values, weights=weights))
            spreads.loc[player] = float(np.sqrt(np.average((values - center) ** 2, weights=weights)))
    else:
        grouped = match_values.groupby(player_col)[value_col]
        counts = grouped.size().reindex(players).fillna(0)
        spreads = grouped.std(ddof=0).reindex(players)
    frame = pd.DataFrame({"matches": counts, "spread": spreads}, index=players)
    frame["typical"] = np.nan
    frame["shrunk"] = np.nan

    def _fill(role_players: pd.Index) -> None:
        known = spreads.reindex(role_players).dropna()
        ref_known = known[reference.reindex(known.index).fillna(False).astype(bool)]
        typical = float(ref_known.mean()) if len(ref_known) else float(known.mean()) if len(known) else 0.0
        filled = spreads.reindex(role_players).fillna(typical)
        shrunk = shrink(filled, counts.reindex(role_players), typical, 8)
        frame.loc[role_players, "typical"] = typical
        frame.loc[role_players, "shrunk"] = shrunk.to_numpy()

    if groups is None:
        _fill(players)
    else:
        labels = groups.reindex(players).fillna("unknown")
        for _, index in labels.groupby(labels, sort=False).groups.items():
            _fill(pd.Index(index))
    frame["pre_z"] = -frame["shrunk"]
    return frame


def consistency_score(match_values: pd.DataFrame, player_col: str, value_col: str, players: pd.Index, reference: pd.Series, groups: pd.Series | None = None) -> pd.Series:
    parts = consistency_parts(match_values, player_col, value_col, players, reference, groups)
    if groups is None:
        return zscore(parts["pre_z"], reference)
    return zscore_within(parts["pre_z"], groups, reference)


def component_frame(raw: pd.Series, players: pd.Index, reference: pd.Series) -> pd.Series:
    return zscore(raw.reindex(players).fillna(0.0), reference)


def _clutch_spell(own_gap: pd.Series, teammate_z: pd.Series) -> pd.Series:
    """A spell below the player's own rate stays negative. A spell above it scales with beating teammates."""
    own_gap = own_gap.astype(float)
    beaten = own_gap.gt(0)
    return own_gap.where(~beaten, own_gap * teammate_z.astype(float).clip(lower=0))


def score_batters(legal: pd.DataFrame) -> pd.DataFrame:
    player = "striker_id"
    ids = pd.Index(legal[player].unique(), name=player)
    names = _names(legal, player, "striker_name")
    orders = legal.groupby(player)["batting_order"].agg(_mode)
    runs = legal.groupby(player)["bat_runs"].sum().reindex(ids)
    balls = legal.groupby(player).size().reindex(ids).astype(float)
    dismissals = legal.groupby(player)["striker_out"].sum().reindex(ids).astype(float)
    weight = legal["level_weight"]
    runs_w = (legal["bat_runs"] * weight).groupby(legal[player]).sum().reindex(ids)
    balls_w = weight.groupby(legal[player]).sum().reindex(ids).astype(float)
    dismissals_w = (legal["striker_out"].astype(float) * weight).groupby(legal[player]).sum().reindex(ids)
    strike_rate = 100 * runs_w / balls_w.replace(0, np.nan)
    average = runs_w / dismissals_w.replace(0, np.nan)

    phase_runs = legal.groupby("phase")["bat_runs"].sum()
    phase_balls = legal.groupby("phase").size()
    phase_outs = legal.groupby("phase")["striker_out"].sum()
    phase_sr = 100 * phase_runs / phase_balls
    overall_average = float(runs.sum() / dismissals.sum())
    phase_average = (phase_runs / phase_outs.replace(0, np.nan)).fillna(overall_average)

    phase_counts = legal.pivot_table(index=player, columns="phase", values="level_weight", aggfunc="sum", fill_value=0)
    phase_counts = phase_counts.reindex(ids).fillna(0)
    shares = phase_counts.div(phase_counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    expected_sr = sum(shares[phase] * phase_sr[phase] for phase in shares.columns if phase in phase_sr.index)
    expected_average = sum(shares[phase] * phase_average[phase] for phase in shares.columns if phase in phase_average.index)
    shrunk_sr = shrink(strike_rate, balls_w, expected_sr, 120)
    shrunk_average = shrink(average.fillna(expected_average), dismissals_w, expected_average, 4)
    shrunk_average = shrunk_average.where(dismissals.gt(0), expected_average)

    n_eff = weighted_count(legal, player, ids)
    reference = n_eff.ge(REFERENCE_BALLS)
    roles = orders.reindex(ids).map(_batting_role)
    base = 0.5 * zscore_blend(shrunk_sr - expected_sr, roles, reference) + 0.5 * zscore_blend(shrunk_average - expected_average, roles, reference)

    band_z = {}
    band_raw = {}
    band_count = {}
    high_n = weighted_count(legal.loc[legal["band"].eq("high")], player, ids)
    for band in BANDS:
        subset = legal.loc[legal["band"].eq(band), [player, "season", "level_weight", "e_bat"]]
        raw = career_rate(subset, ids, player, "e_bat")
        count = weighted_count(subset, player, ids)
        band_raw[band] = raw
        band_count[band] = count
        band_z[band] = zscore_blend(shrink(raw, count, 0.0, 30), roles, reference)

    innings = (
        legal.groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(runs=("bat_runs", "sum"), balls=("bat_runs", "size"), e_bat=("e_bat", "mean"), level_weight=("level_weight", "max"))
        .reset_index()
    )
    innings["sr"] = 100 * innings["runs"] / innings["balls"]
    compared = innings_comparisons(innings, player, "sr", True)
    compared = compared.merge(innings[[player, "match_id", "innings", "balls", "runs", "level_weight"]], on=[player, "match_id", "innings"], how="left")
    compared["label"] = [
        passage_label(row, float(strike_rate.loc[row[player]]), True)
        for _, row in compared.iterrows()
    ]
    peer_mean, peer_n = _weighted_mean(compared, player, "z_passage")
    peer_pre = shrink(peer_mean, peer_n, 0.0, 5).reindex(ids).fillna(0.0)
    peer = zscore_blend(peer_pre, roles, reference)
    stood_out = compared.loc[compared["label"].eq("stood out")].groupby(player).size()
    passages = compared.groupby(player).size()
    stood_share = (stood_out / passages).reindex(ids)

    high = (
        legal.loc[legal["band"].eq("high")]
        .groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(runs=("bat_runs", "sum"), balls=("bat_runs", "size"), level_weight=("level_weight", "max"))
        .reset_index()
    )
    high["sr"] = 100 * high["runs"] / high["balls"]
    high_compared = innings_comparisons(high, player, "sr", True)
    high_compared = high_compared.merge(high[[player, "match_id", "innings", "balls", "runs", "level_weight"]], on=[player, "match_id", "innings"], how="left")
    scale = float(innings.loc[innings[player].isin(ids[reference]) & innings["balls"].ge(6), "sr"].std(ddof=0))
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    clutch_rows = high_compared.dropna(subset=["z_team"]).copy()
    own_gap = (clutch_rows["metric"] - clutch_rows[player].map(strike_rate)) / scale
    clutch_rows["own_gap"] = own_gap.to_numpy()
    clutch_rows["clutch"] = _clutch_spell(own_gap, clutch_rows["z_team"])
    clutch_mean, clutch_n = _weighted_mean(clutch_rows, player, "clutch")
    clutch_pre = shrink(clutch_mean, clutch_n, 0.0, 5).reindex(ids).fillna(0.0)
    clutch = zscore_blend(clutch_pre, roles, reference)

    qualified = innings.loc[innings["balls"].ge(6)].copy()
    match_values = qualified.groupby([player, "match_id"], sort=False).agg(e_bat=("e_bat", "mean"), level_weight=("level_weight", "max")).reset_index()
    match_values = match_values.merge(
        qualified.groupby([player, "match_id"], sort=False)["match_date"].min().reset_index(),
        on=[player, "match_id"],
        how="left",
    )
    consistency_detail = consistency_parts(match_values, player, "e_bat", ids, reference, roles)
    consistency = zscore_blend(consistency_detail["pre_z"], roles, reference)

    composite = (
        BASELINE_WEIGHT * base
        + ZERO_WEIGHT * band_z["zero"]
        + MEDIUM_WEIGHT * band_z["medium"]
        + HIGH_WEIGHT * band_z["high"]
        + CLUTCH_WEIGHT * clutch
        + PEERS_WEIGHT * peer
        + CONSISTENCY_WEIGHT * consistency
    )
    ranked = n_eff.ge(RANK_BALLS) & high_n.ge(RANK_HIGH_BALLS)
    table = pd.DataFrame({
        "player_id": ids,
        "player_name": names.reindex(ids).to_numpy(),
        "role": orders.reindex(ids).map(_batting_role).to_numpy(),
        "runs": runs.to_numpy(),
        "average": average.to_numpy(),
        "strike_rate": strike_rate.to_numpy(),
        "legal_balls": balls.to_numpy(),
        "n_eff": n_eff.to_numpy(),
        "high_n_eff": high_n.to_numpy(),
        "baseline": base.to_numpy(),
        "band_zero": band_z["zero"].to_numpy(),
        "band_medium": band_z["medium"].to_numpy(),
        "band_high": band_z["high"].to_numpy(),
        "clutch": clutch.to_numpy(),
        "peers": peer.to_numpy(),
        "consistency": consistency.to_numpy(),
        "stood_out_share": stood_share.to_numpy(),
        "composite": composite.to_numpy(),
        "ranked": ranked.to_numpy(),
    })
    table["rank"] = np.nan
    order = table.loc[table["ranked"]].sort_values(["composite", "player_id"], ascending=[False, True]).index
    table.loc[order, "rank"] = np.arange(1, len(order) + 1)
    phase_player = (
        legal.groupby([player, "phase"], sort=False)
        .agg(balls=("bat_runs", "size"), runs=("bat_runs", "sum"), dismissals=("striker_out", "sum"))
        .reset_index()
    )
    math = pd.DataFrame({
        "player_id": ids,
        "reference": reference.reindex(ids).fillna(False).to_numpy(),
        "runs": runs.to_numpy(),
        "balls": balls.to_numpy(),
        "dismissals": dismissals.to_numpy(),
        "strike_rate": strike_rate.to_numpy(),
        "average": average.to_numpy(),
        "expected_sr": expected_sr.reindex(ids).to_numpy(),
        "expected_average": expected_average.reindex(ids).to_numpy(),
        "shrunk_sr": shrunk_sr.reindex(ids).to_numpy(),
        "shrunk_average": shrunk_average.reindex(ids).to_numpy(),
        "sr_gap": (shrunk_sr - expected_sr).reindex(ids).to_numpy(),
        "average_gap": (shrunk_average - expected_average).reindex(ids).to_numpy(),
        "zero_rate": shrink(band_raw["zero"], band_count["zero"], 0.0, 30).reindex(ids).to_numpy(),
        "zero_balls": band_count["zero"].reindex(ids).to_numpy(),
        "medium_rate": shrink(band_raw["medium"], band_count["medium"], 0.0, 30).reindex(ids).to_numpy(),
        "medium_balls": band_count["medium"].reindex(ids).to_numpy(),
        "high_rate": shrink(band_raw["high"], band_count["high"], 0.0, 30).reindex(ids).to_numpy(),
        "high_balls": band_count["high"].reindex(ids).to_numpy(),
        "peer_pre": peer_pre.reindex(ids).to_numpy(),
        "peer_n": peer_n.reindex(ids).fillna(0).to_numpy(),
        "clutch_pre": clutch_pre.reindex(ids).to_numpy(),
        "clutch_n": clutch_n.reindex(ids).fillna(0).to_numpy(),
        "clutch_scale": scale,
        "consistency_matches": consistency_detail["matches"].reindex(ids).to_numpy(),
        "consistency_spread": consistency_detail["spread"].reindex(ids).to_numpy(),
        "consistency_typical": consistency_detail["typical"].reindex(ids).to_numpy(),
        "consistency_shrunk": consistency_detail["shrunk"].reindex(ids).to_numpy(),
        "consistency_pre": consistency_detail["pre_z"].reindex(ids).to_numpy(),
    })
    TRACES["batters"] = {
        "math": math,
        "spells": compared,
        "clutch": clutch_rows,
        "phases": phase_player,
    }
    return table.sort_values(["ranked", "rank", "player_name"], ascending=[False, True, True]).reset_index(drop=True)


def score_bowlers(legal: pd.DataFrame, work: pd.DataFrame) -> pd.DataFrame:
    player = "bowler_id"
    ids = pd.Index(legal[player].unique(), name=player)
    names = _names(legal, player, "bowler_name")
    arm = legal.groupby(player)["pace_or_spin"].agg(_mode).reindex(ids)
    legal_balls = legal.groupby(player).size().reindex(ids).astype(float)
    wickets = work.groupby(player)["is_bowler_wicket"].sum().reindex(ids).fillna(0).astype(float)
    # is_bowler_wicket may be bool; sum works.
    conceded = work.groupby(player)["conceded"].sum().reindex(ids).fillna(0).astype(float)
    weight = legal["level_weight"]
    legal_balls_w = weight.groupby(legal[player]).sum().reindex(ids).astype(float)
    wickets_w = (work["is_bowler_wicket"].astype(float) * work["level_weight"]).groupby(work[player]).sum().reindex(ids).fillna(0)
    conceded_w = (work["conceded"] * work["level_weight"]).groupby(work[player]).sum().reindex(ids).fillna(0)
    economy = 6 * conceded_w / legal_balls_w.replace(0, np.nan)
    # Clutch spells are legal balls only, so the career rate they are set against is too.
    charged_w = (legal["charged_runs"] * weight).groupby(legal[player]).sum().reindex(ids).fillna(0)
    legal_economy = 6 * charged_w / legal_balls_w.replace(0, np.nan)
    balls_per_wicket = legal_balls_w / wickets_w.replace(0, np.nan)

    phase_arm = (
        work.groupby(["phase", "pace_or_spin"], sort=False)
        .agg(conceded=("conceded", "sum"), legal=("is_legal", "sum"), wickets=("is_bowler_wicket", "sum"))
    )
    phase_arm["economy"] = 6 * phase_arm["conceded"] / phase_arm["legal"].replace(0, np.nan)
    phase_arm["balls_per_wicket"] = phase_arm["legal"] / phase_arm["wickets"].replace(0, np.nan)
    arm_fallback = (
        work.groupby("pace_or_spin")
        .agg(conceded=("conceded", "sum"), legal=("is_legal", "sum"), wickets=("is_bowler_wicket", "sum"))
    )
    arm_fallback["economy"] = 6 * arm_fallback["conceded"] / arm_fallback["legal"]
    arm_fallback["balls_per_wicket"] = arm_fallback["legal"] / arm_fallback["wickets"].replace(0, np.nan)

    phase_counts = legal.pivot_table(index=player, columns="phase", values="level_weight", aggfunc="sum", fill_value=0)
    phase_counts = phase_counts.reindex(ids).fillna(0)
    shares = phase_counts.div(phase_counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    expected_economy = pd.Series(0.0, index=ids)
    expected_balls = pd.Series(0.0, index=ids)
    for phase in shares.columns:
        for bowling_arm in arm.dropna().unique():
            mask = arm.eq(bowling_arm)
            if (phase, bowling_arm) in phase_arm.index and pd.notna(phase_arm.loc[(phase, bowling_arm), "economy"]):
                econ_cell = float(phase_arm.loc[(phase, bowling_arm), "economy"])
                bpw_cell = phase_arm.loc[(phase, bowling_arm), "balls_per_wicket"]
                if pd.isna(bpw_cell):
                    bpw_cell = float(arm_fallback.loc[bowling_arm, "balls_per_wicket"])
            else:
                econ_cell = float(arm_fallback.loc[bowling_arm, "economy"])
                bpw_cell = float(arm_fallback.loc[bowling_arm, "balls_per_wicket"])
            expected_economy.loc[mask] += shares.loc[mask, phase] * econ_cell
            expected_balls.loc[mask] += shares.loc[mask, phase] * float(bpw_cell)

    shrunk_economy = shrink(economy, legal_balls_w, expected_economy, 120)
    shrunk_balls = shrink(balls_per_wicket.fillna(expected_balls), wickets_w, expected_balls, 4)
    shrunk_balls = shrunk_balls.where(wickets.gt(0), expected_balls)
    n_eff = weighted_count(legal, player, ids)
    reference = n_eff.ge(REFERENCE_BALLS)
    base = 0.5 * zscore(expected_economy - shrunk_economy, reference) + 0.5 * zscore(expected_balls - shrunk_balls, reference)

    band_z = {}
    band_raw = {}
    band_count = {}
    high_n = weighted_count(legal.loc[legal["band_bowl"].eq("high")], player, ids)
    for band in BANDS:
        subset = legal.loc[legal["band_bowl"].eq(band), [player, "season", "level_weight", "e_bowl"]]
        raw = career_rate(subset, ids, player, "e_bowl")
        count = weighted_count(subset, player, ids)
        band_raw[band] = raw
        band_count[band] = count
        band_z[band] = zscore(shrink(raw, count, 0.0, 30), reference)

    spell_conceded = work.groupby(["match_id", "innings", player])["conceded"].sum()
    spells = (
        legal.groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(balls=("bat_runs", "size"), e_bowl=("e_bowl", "mean"), charged=("charged_runs", "sum"), level_weight=("level_weight", "max"))
        .reset_index()
    )
    spells["conceded"] = spells.set_index(["match_id", "innings", player]).index.map(spell_conceded)
    spells["economy"] = 6 * spells["conceded"] / spells["balls"]
    compared = innings_comparisons(spells, player, "economy", False)
    compared = compared.merge(spells[[player, "match_id", "innings", "balls", "charged", "conceded", "level_weight"]], on=[player, "match_id", "innings"], how="left")
    compared["label"] = [
        passage_label(row, float(economy.loc[row[player]]), False)
        for _, row in compared.iterrows()
    ]
    peer_mean, peer_n = _weighted_mean(compared, player, "z_passage")
    peer_pre = shrink(peer_mean, peer_n, 0.0, 5).reindex(ids).fillna(0.0)
    peer = component_frame(peer_pre, ids, reference)
    stood_out = compared.loc[compared["label"].eq("stood out")].groupby(player).size()
    passages = compared.groupby(player).size()
    stood_share = (stood_out / passages).reindex(ids)

    high_spells = (
        legal.loc[legal["band_bowl"].eq("high")]
        .groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(balls=("charged_runs", "size"), charged=("charged_runs", "sum"), level_weight=("level_weight", "max"))
        .reset_index()
    )
    high_spells["economy"] = 6 * high_spells["charged"] / high_spells["balls"]
    high_compared = innings_comparisons(high_spells, player, "economy", False)
    high_compared = high_compared.merge(high_spells[[player, "match_id", "innings", "balls", "charged", "level_weight"]], on=[player, "match_id", "innings"], how="left")
    scale_spells = spells.loc[spells[player].isin(ids[reference]) & spells["balls"].ge(6)]
    scale = float((6 * scale_spells["charged"] / scale_spells["balls"]).std(ddof=0))
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    clutch_rows = high_compared.dropna(subset=["z_team"]).copy()
    own_gap = (clutch_rows[player].map(legal_economy) - clutch_rows["metric"]) / scale
    clutch_rows["own_gap"] = own_gap.to_numpy()
    clutch_rows["clutch"] = _clutch_spell(own_gap, clutch_rows["z_team"])
    clutch_mean, clutch_n = _weighted_mean(clutch_rows, player, "clutch")
    clutch_pre = shrink(clutch_mean, clutch_n, 0.0, 5).reindex(ids).fillna(0.0)
    clutch = component_frame(clutch_pre, ids, reference)

    qualified = spells.loc[spells["balls"].ge(6)].copy()
    match_values = qualified.groupby([player, "match_id"], sort=False).agg(e_bowl=("e_bowl", "mean"), level_weight=("level_weight", "max")).reset_index()
    match_values = match_values.merge(
        qualified.groupby([player, "match_id"], sort=False)["match_date"].min().reset_index(),
        on=[player, "match_id"],
        how="left",
    )
    consistency_detail = consistency_parts(match_values, player, "e_bowl", ids, reference)
    consistency = zscore(consistency_detail["pre_z"], reference)

    composite = (
        BASELINE_WEIGHT * base
        + ZERO_WEIGHT * band_z["zero"]
        + MEDIUM_WEIGHT * band_z["medium"]
        + HIGH_WEIGHT * band_z["high"]
        + CLUTCH_WEIGHT * clutch
        + PEERS_WEIGHT * peer
        + CONSISTENCY_WEIGHT * consistency
    )
    ranked = n_eff.ge(RANK_BALLS) & high_n.ge(RANK_HIGH_BALLS)
    table = pd.DataFrame({
        "player_id": ids,
        "player_name": names.reindex(ids).to_numpy(),
        "role": arm.fillna("unknown").to_numpy(),
        "wickets": wickets.to_numpy(),
        "economy": economy.to_numpy(),
        "balls_per_wicket": balls_per_wicket.to_numpy(),
        "legal_balls": legal_balls.to_numpy(),
        "n_eff": n_eff.to_numpy(),
        "high_n_eff": high_n.to_numpy(),
        "baseline": base.to_numpy(),
        "band_zero": band_z["zero"].to_numpy(),
        "band_medium": band_z["medium"].to_numpy(),
        "band_high": band_z["high"].to_numpy(),
        "clutch": clutch.to_numpy(),
        "peers": peer.to_numpy(),
        "consistency": consistency.to_numpy(),
        "stood_out_share": stood_share.to_numpy(),
        "composite": composite.to_numpy(),
        "ranked": ranked.to_numpy(),
    })
    table["rank"] = np.nan
    order = table.loc[table["ranked"]].sort_values(["composite", "player_id"], ascending=[False, True]).index
    table.loc[order, "rank"] = np.arange(1, len(order) + 1)
    phase_player = (
        legal.groupby([player, "phase"], sort=False)
        .agg(balls=("bat_runs", "size"), runs=("charged_runs", "sum"), wickets=("bowler_wicket", "sum"))
        .reset_index()
    )
    math = pd.DataFrame({
        "player_id": ids,
        "reference": reference.reindex(ids).fillna(False).to_numpy(),
        "legal_balls": legal_balls.reindex(ids).to_numpy(),
        "wickets": wickets.reindex(ids).to_numpy(),
        "conceded": conceded.reindex(ids).to_numpy(),
        "economy": economy.reindex(ids).to_numpy(),
        "balls_per_wicket": balls_per_wicket.reindex(ids).to_numpy(),
        "expected_economy": expected_economy.reindex(ids).to_numpy(),
        "expected_balls": expected_balls.reindex(ids).to_numpy(),
        "shrunk_economy": shrunk_economy.reindex(ids).to_numpy(),
        "shrunk_balls": shrunk_balls.reindex(ids).to_numpy(),
        "economy_gap": (expected_economy - shrunk_economy).reindex(ids).to_numpy(),
        "balls_gap": (expected_balls - shrunk_balls).reindex(ids).to_numpy(),
        "zero_rate": shrink(band_raw["zero"], band_count["zero"], 0.0, 30).reindex(ids).to_numpy(),
        "zero_balls": band_count["zero"].reindex(ids).to_numpy(),
        "medium_rate": shrink(band_raw["medium"], band_count["medium"], 0.0, 30).reindex(ids).to_numpy(),
        "medium_balls": band_count["medium"].reindex(ids).to_numpy(),
        "high_rate": shrink(band_raw["high"], band_count["high"], 0.0, 30).reindex(ids).to_numpy(),
        "high_balls": band_count["high"].reindex(ids).to_numpy(),
        "peer_pre": peer_pre.reindex(ids).to_numpy(),
        "peer_n": peer_n.reindex(ids).fillna(0).to_numpy(),
        "clutch_pre": clutch_pre.reindex(ids).to_numpy(),
        "clutch_n": clutch_n.reindex(ids).fillna(0).to_numpy(),
        "clutch_scale": scale,
        "clutch_economy": legal_economy.reindex(ids).to_numpy(),
        "consistency_matches": consistency_detail["matches"].reindex(ids).to_numpy(),
        "consistency_spread": consistency_detail["spread"].reindex(ids).to_numpy(),
        "consistency_typical": consistency_detail["typical"].reindex(ids).to_numpy(),
        "consistency_shrunk": consistency_detail["shrunk"].reindex(ids).to_numpy(),
        "consistency_pre": consistency_detail["pre_z"].reindex(ids).to_numpy(),
    })
    TRACES["bowlers"] = {
        "math": math,
        "spells": compared,
        "clutch": clutch_rows,
        "phases": phase_player,
    }
    return table.sort_values(["ranked", "rank", "player_name"], ascending=[False, True, True]).reset_index(drop=True)


def _role_token(role: str) -> str:
    text = str(role).lower()
    if text.startswith("top"):
        return "top"
    if text.startswith("middle"):
        return "middle"
    if text.startswith("lower"):
        return "lower"
    if text == "pace":
        return "pace"
    if text == "spin":
        return "spin"
    return text


def _pooled_batter_order(batters: pd.DataFrame) -> pd.DataFrame:
    """Same pieces, z-scored on the whole reference list rather than inside a batting role."""
    math = TRACES["batters"]["math"].set_index("player_id")
    reference = math["reference"].astype(bool)

    def band_piece(rate_col: str, ball_col: str) -> pd.Series:
        shrunk = shrink(math[rate_col], math[ball_col], 0.0, 30)
        return zscore(shrunk, reference)

    pooled = (
        BASELINE_WEIGHT * (0.5 * zscore(math["sr_gap"], reference) + 0.5 * zscore(math["average_gap"], reference))
        + ZERO_WEIGHT * band_piece("zero_rate", "zero_balls")
        + MEDIUM_WEIGHT * band_piece("medium_rate", "medium_balls")
        + HIGH_WEIGHT * band_piece("high_rate", "high_balls")
        + CLUTCH_WEIGHT * zscore(math["clutch_pre"], reference)
        + PEERS_WEIGHT * zscore(math["peer_pre"], reference)
        + CONSISTENCY_WEIGHT * zscore(math["consistency_pre"], reference)
    )
    floor = batters.set_index("player_id")
    keep = floor.index[floor["n_eff"].ge(RANK_BALLS) & floor["high_n_eff"].ge(RANK_HIGH_BALLS)]
    ordered = pooled.reindex(keep).sort_values(ascending=False)
    out = floor.loc[ordered.index, ["player_name", "role"]].copy()
    out["rank"] = np.arange(1, len(out) + 1)
    out["role"] = out["role"].map(_role_token)
    return out.reset_index()


def write_deck_exports(balls: pd.DataFrame, work: pd.DataFrame, legal: pd.DataFrame, batters: pd.DataFrame, bowlers: pd.DataFrame, folder: str | Path = "exports") -> dict:
    """Write the deck files from the frames the notebook already holds."""
    out = Path(folder)
    out.mkdir(exist_ok=True)
    notes = {}

    raw = int(len(balls))
    super_overs = int(balls["is_super_over"].astype(bool).sum())
    wides_noballs = int((~balls["is_legal"].astype(bool)).sum())
    legal_used = int(balls["is_legal"].astype(bool).sum())
    pd.DataFrame({
        "stage": ["raw_deliveries", "super_over_deliveries_included", "wides_noballs_other_excluded", "legal_balls_used"],
        "count": [raw, super_overs, wides_noballs, legal_used],
    }).to_csv(out / "01_cleaning_funnel.csv", index=False)

    extras = balls["extras_label"].fillna("ordinary").value_counts()
    extras.rename_axis("label").reset_index(name="count").to_csv(out / "02_extras_label_counts.csv", index=False)
    dismissals = balls.loc[balls["is_wicket"].fillna(False).astype(bool), "dismissal_type"].fillna("(blank)")
    dismissals.value_counts().rename_axis("dismissal_type").reset_index(name="count").to_csv(out / "03_dismissal_type_counts.csv", index=False)
    legal["comp_group"].value_counts().rename_axis("comp_group").reset_index(name="count").to_csv(out / "04_comp_group_counts.csv", index=False)

    innings = legal.groupby(["match_id", "innings"], sort=False).agg(
        is_reduced=("is_reduced", "max"),
        revised_target=("revised_target", "first"),
    )
    reduced = innings.loc[innings["is_reduced"].fillna(False).astype(bool)]
    reduced_chase = legal.loc[legal["is_reduced"].fillna(False).astype(bool) & legal["innings"].eq(2)]
    excluded_matches = reduced_chase.loc[reduced_chase["revised_target"].isna() | reduced_chase["revised_target"].le(0), "match_id"].nunique()
    pd.DataFrame({
        "category": ["total_innings", "is_reduced_true", "reduced_with_revised_target", "reduced_excluded_from_rrr"],
        "count": [
            int(len(innings)),
            int(len(reduced)),
            int(reduced["revised_target"].notna().sum()),
            int(excluded_matches),
        ],
    }).to_csv(out / "05_reduced_innings.csv", index=False)

    difficulty = pd.concat([
        legal[["ball_bat"]].rename(columns={"ball_bat": "ball_difficulty"}).assign(role="batter"),
        legal[["ball_bowl"]].rename(columns={"ball_bowl": "ball_difficulty"}).assign(role="bowler"),
    ], ignore_index=True)
    difficulty = difficulty.sample(n=min(50000, len(difficulty)), random_state=14)
    difficulty[["role", "ball_difficulty"]].to_csv(out / "06_ball_difficulty.csv", index=False)

    pressure = legal[["pressure_bat", "pressure_bowl", "pace_or_spin"]].sample(n=min(50000, len(legal)), random_state=14)
    pressure.to_csv(out / "07_pressure_scores.csv", index=False)
    pace = legal.loc[legal["pace_or_spin"].eq("Pace"), "pressure_bowl"]
    spin = legal.loc[legal["pace_or_spin"].eq("Spin"), "pressure_bowl"]
    pd.DataFrame({
        "metric": ["pressure_bat", "pressure_bowl_pace", "pressure_bowl_spin"],
        "p50": [float(legal["pressure_bat"].quantile(0.50)), float(pace.quantile(0.50)), float(spin.quantile(0.50))],
        "p80": [float(legal["pressure_bat"].quantile(0.80)), float(pace.quantile(0.80)), float(spin.quantile(0.80))],
    }).to_csv(out / "08_band_cutoffs.csv", index=False)

    high = legal.loc[legal["band"].eq("high")]
    high.groupby(["phase", "pace_or_spin"], sort=False).size().reset_index(name="count").to_csv(out / "09_high_band_composition.csv", index=False)

    chase = legal.loc[legal["innings"].eq(2) & legal["comp_group"].eq("IPL") & legal["stage"].eq("Final")]
    if chase.empty:
        chase = legal.loc[legal["innings"].eq(2)]
    wickets = chase.groupby(["match_id", "innings"])["wicket_flag"].sum()
    match_id, innings_no = wickets.sort_values(ascending=False).index[0]
    sample = legal.loc[legal["match_id"].eq(match_id) & legal["innings"].eq(innings_no)].sort_values("n")
    sample_out = pd.DataFrame({
        "ball_position": sample["n"].to_numpy(),
        "count_shock_bat": sample["shock_bat"].to_numpy(),
        "count_shock_bowl": sample["shock_bowl"].to_numpy(),
        "run_of_play_bat": sample["delta_bat"].to_numpy(),
        "run_of_play_bowl": sample["delta_bowl"].to_numpy(),
        "is_wicket": sample["wicket_flag"].to_numpy(),
        "bat_runs": sample["bat_runs"].to_numpy(),
    })
    sample_out.to_csv(out / "10_sample_innings_timeline.csv", index=False)
    info = sample.iloc[0]
    match_names = pd.read_csv(find_silver() / "matches.csv", usecols=["match_id", "home_team", "away_team"])
    named = match_names.loc[match_names["match_id"].eq(match_id)].iloc[0]
    notes["sample_match_id"] = int(match_id)
    notes["sample_innings"] = int(innings_no)
    notes["sample_date"] = str(pd.to_datetime(info["match_date"]).date())
    notes["sample_stage"] = str(info["stage"])
    notes["sample_competition"] = str(info["comp_name"])
    notes["sample_home"] = str(named["home_team"])
    notes["sample_away"] = str(named["away_team"])

    def rating_rows(id_col: str, name_col: str, rating_col: str, role: str) -> pd.DataFrame:
        ordered = legal.sort_values(["match_date", "match_id", "innings", "innings_ball_num"])
        last = ordered.groupby([id_col, "ladder"], sort=False).agg(
            player_name=(name_col, "last"),
            final_rating=(rating_col, "last"),
            balls_seen=(rating_col, "size"),
        ).reset_index()
        last["role"] = role
        return last.rename(columns={id_col: "player_id"})[["player_id", "player_name", "role", "ladder", "final_rating", "balls_seen"]]

    ratings = pd.concat([
        rating_rows("striker_id", "striker_name", "batter_rating_after", "batter"),
        rating_rows("bowler_id", "bowler_name", "bowler_rating_after", "bowler"),
    ], ignore_index=True)
    ratings.to_csv(out / "11_final_ratings.csv", index=False)
    summary = legal.attrs.get("elo_summary", {})
    pd.DataFrame({
        "metric": ["min_rating", "max_rating", "std_rating"],
        "batter_value": [summary.get("batter_elo_min"), summary.get("batter_elo_max"), summary.get("batter_elo_sd")],
        "bowler_value": [summary.get("bowler_elo_min"), summary.get("bowler_elo_max"), summary.get("bowler_elo_sd")],
    }).to_csv(out / "12_fit_elo_bounds.csv", index=False)

    focus = legal.loc[legal["striker_name"].eq("Jos Buttler")].sort_values(["match_date", "match_id", "innings", "innings_ball_num"])
    if focus.empty:
        focus_name = batters.loc[batters["ranked"]].sort_values("rank").iloc[0]["player_name"]
        focus = legal.loc[legal["striker_name"].eq(focus_name)].sort_values(["match_date", "match_id", "innings", "innings_ball_num"])
    else:
        focus_name = "Jos Buttler"
    path = pd.DataFrame({
        "ball_seq_number": np.arange(1, len(focus) + 1),
        "raw_rating": focus["batter_rating_after"].to_numpy(),
        "match_date": pd.to_datetime(focus["match_date"]).dt.date.astype(str).to_numpy(),
        "match_id": focus["match_id"].to_numpy(),
        "bat_runs": focus["bat_runs"].to_numpy(),
    })
    path.to_csv(out / "13_player_trajectory.csv", index=False)
    by_match = path.groupby("match_id", sort=False).agg(start=("raw_rating", "first"), end=("raw_rating", "last"), date=("match_date", "first"), runs=("bat_runs", "sum"))
    by_match["move"] = by_match["end"] - by_match["start"]
    notes["trajectory_player"] = focus_name
    notes["trajectory_up"] = by_match["move"].idxmax()
    notes["trajectory_down"] = by_match["move"].idxmin()
    notes["trajectory_up_date"] = str(by_match.loc[notes["trajectory_up"], "date"])
    notes["trajectory_down_date"] = str(by_match.loc[notes["trajectory_down"], "date"])
    notes["trajectory_up_runs"] = float(by_match.loc[notes["trajectory_up"], "runs"])
    notes["trajectory_down_runs"] = float(by_match.loc[notes["trajectory_down"], "runs"])

    def deciles(predicted: pd.Series, actual: pd.Series) -> pd.DataFrame:
        bin_id = pd.qcut(predicted, 10, labels=False, duplicates="drop") + 1
        frame = pd.DataFrame({"decile": bin_id, "predicted": predicted, "actual": actual})
        return frame.groupby("decile", sort=True).agg(
            mean_predicted=("predicted", "mean"),
            mean_actual=("actual", "mean"),
            n_balls=("actual", "size"),
        ).reset_index()

    runs_bins = deciles(legal["x_runs"], legal["bat_runs"])
    runs_bins = runs_bins.rename(columns={"mean_predicted": "mean_predicted_x_runs", "mean_actual": "mean_actual_bat_runs"})
    runs_bins.to_csv(out / "14_calibration_bins.csv", index=False)
    wicket_bins = deciles(legal["x_wicket"], legal["striker_out"].astype(float))
    wicket_bins = wicket_bins.rename(columns={"mean_predicted": "mean_predicted_x_wicket", "mean_actual": "mean_actual_striker_out"})
    wicket_bins.to_csv(out / "14b_calibration_wicket_bins.csv", index=False)

    pd.DataFrame({
        "component": ["baseline", "zero", "medium", "high", "clutch", "peers", "consistency"],
        "weight": [BASELINE_WEIGHT, ZERO_WEIGHT, MEDIUM_WEIGHT, HIGH_WEIGHT, CLUTCH_WEIGHT, PEERS_WEIGHT, CONSISTENCY_WEIGHT],
    }).to_csv(out / "15_component_weights.csv", index=False)

    scatter = pd.concat([
        batters.loc[batters["ranked"], ["player_id", "player_name", "band_high", "clutch"]].assign(role="batter"),
        bowlers.loc[bowlers["ranked"], ["player_id", "player_name", "band_high", "clutch"]].assign(role="bowler"),
    ], ignore_index=True)
    scatter = scatter.rename(columns={"band_high": "high_zscore", "clutch": "clutch_zscore"})
    scatter.to_csv(out / "16_high_clutch_scatter.csv", index=False)

    top20 = batters.loc[batters["ranked"]].nsmallest(20, "rank")[["rank", "player_name", "role"]].copy()
    top20["role"] = top20["role"].map(_role_token)
    top20.to_csv(out / "17_role_composition_with_split.csv", index=False)
    without = _pooled_batter_order(batters).head(20)[["rank", "player_name", "role"]]
    without.to_csv(out / "18_role_composition_without_split.csv", index=False)

    def population(frame: pd.DataFrame, label: str) -> tuple[int, int]:
        group = frame.loc[frame["role"].map(_role_token).eq(label)]
        return int(group["n_eff"].ge(30).sum()), int(group["ranked"].sum())

    rows = []
    for label in ["top", "middle", "lower"]:
        ge30, ranked = population(batters, label)
        rows.append({"group": f"batters_{label}_order", "n_eff_ge_30": ge30, "n_eff_ge_120_and_high_30": ranked})
    for label in ["pace", "spin"]:
        ge30, ranked = population(bowlers, label)
        rows.append({"group": f"bowlers_{label}", "n_eff_ge_30": ge30, "n_eff_ge_120_and_high_30": ranked})
    pd.DataFrame(rows).to_csv(out / "19_reference_population_sizes.csv", index=False)

    ranked_all = pd.concat([
        batters.loc[batters["ranked"], ["player_id", "player_name", "role", "composite", "rank"]],
        bowlers.loc[bowlers["ranked"], ["player_id", "player_name", "role", "composite", "rank"]],
    ], ignore_index=True).rename(columns={"composite": "composite_score"})
    ranked_all.to_csv(out / "20_composite_scores.csv", index=False)

    weights = {
        "baseline": BASELINE_WEIGHT, "zero": ZERO_WEIGHT, "medium": MEDIUM_WEIGHT, "high": HIGH_WEIGHT,
        "clutch": CLUTCH_WEIGHT, "peers": PEERS_WEIGHT, "consistency": CONSISTENCY_WEIGHT,
    }
    source = {"zero": "band_zero", "medium": "band_medium", "high": "band_high"}

    def contribution(frame: pd.DataFrame, skill: str) -> pd.DataFrame:
        top = frame.loc[frame["ranked"]].nsmallest(5, "rank")
        piece = pd.DataFrame({"player_name": top["player_name"], "role": skill})
        for name, weight in weights.items():
            column = source.get(name, name)
            piece[name] = top[column].to_numpy() * weight
        return piece

    pd.concat([contribution(batters, "batter"), contribution(bowlers, "bowler")], ignore_index=True).to_csv(
        out / "21_component_breakdown_top10.csv", index=False
    )

    wanted = ["Jos Buttler", "Virat Kohli", "David Miller", "Jasprit Bumrah", "Rashid Khan"]
    known_rows = []
    for name in wanted:
        bat_row = batters.loc[batters["player_name"].eq(name)]
        bowl_row = bowlers.loc[bowlers["player_name"].eq(name)]
        chosen = bat_row if not bat_row.empty else bowl_row
        if chosen.empty:
            continue
        row = chosen.iloc[0]
        known_rows.append({"player_name": name, "high_zscore": row["band_high"], "baseline_zscore": row["baseline"]})
    pd.DataFrame(known_rows).to_csv(out / "22_known_players_scatter.csv", index=False)

    def ablation(frame: pd.DataFrame, skill: str) -> pd.DataFrame:
        ranked = frame.loc[frame["ranked"]].copy()
        ranked["full_composite_rank"] = ranked["rank"]
        ranked["baseline_only_rank"] = ranked["baseline"].rank(ascending=False, method="min")
        ranked["role"] = skill
        return ranked[["player_name", "role", "baseline_only_rank", "full_composite_rank"]]

    pd.concat([ablation(batters, "batter"), ablation(bowlers, "bowler")], ignore_index=True).to_csv(
        out / "23_ablation_ranks.csv", index=False
    )
    pd.DataFrame({"item": list(notes.keys()), "value": [str(item) for item in notes.values()]}).to_csv(
        out / "00_caption_notes.csv", index=False
    )
    return notes


def top_table(table: pd.DataFrame, columns: list[str], n: int = 10) -> pd.DataFrame:
    ranked = table.loc[table["ranked"]].nsmallest(n, "rank")
    show = ranked[columns].copy()
    for column in show.columns:
        if pd.api.types.is_float_dtype(show[column]):
            show[column] = show[column].round(3)
    return show
