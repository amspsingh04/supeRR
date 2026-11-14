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
# The eight shares 0.15, 0.10, 0.15, 0.20, 0.15, 0.10, 0.05, 0.05 summed to 0.95.
# The missing 0.05 is added to baseline, the player's usual rates.
BASELINE_WEIGHT = 0.20
ZERO_WEIGHT = 0.10
MEDIUM_WEIGHT = 0.15
HIGH_WEIGHT = 0.20
CLUTCH_WEIGHT = 0.15
PEERS_WEIGHT = 0.10
FORM_WEIGHT = 0.05
CONSISTENCY_WEIGHT = 0.05
# A new player stays near 1500 until they have this many legal balls.
COLD_BALLS = 30.0
VENUE_BALLS = 2400.0
# A phase, arm, and ladder cell is pulled toward the coarser rate with this many balls.
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


def career_rate(frame: pd.DataFrame, player_ids: pd.Index, player_col: str, value_col: str) -> pd.Series:
    """Decay-weighted mean of the rows a player has. A season with no rows is left out."""
    if frame.empty:
        return pd.Series(0.0, index=player_ids)
    weights = frame["season"].map(WEIGHT).astype(float)
    values = frame[value_col].astype(float) * weights
    numer = values.groupby(frame[player_col]).sum()
    denom = weights.groupby(frame[player_col]).sum()
    rate = numer / denom.replace(0, np.nan)
    return rate.reindex(player_ids).fillna(0.0)


def weighted_count(frame: pd.DataFrame, player_col: str, player_ids: pd.Index) -> pd.Series:
    if frame.empty:
        return pd.Series(0.0, index=player_ids)
    weights = frame["season"].map(WEIGHT)
    counted = weights.groupby(frame[player_col]).sum()
    return counted.reindex(player_ids).fillna(0.0)


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
    """Tag every non-super-over ball. Ratings use the legal rows."""
    work = balls.loc[~balls["is_super_over"].astype(bool)].copy()
    work["bat_runs"] = work["runs"].fillna(0.0)
    work["extra_runs"] = work["extras_2_runs"].fillna(0.0)
    work["team_run"] = work["bat_runs"] + work["extra_runs"]
    label = work["extras_label"].fillna("ordinary")
    charged = label.isin(["wide", "no-ball", "other"])
    free = label.isin(["bye", "leg-bye", "penalty"])
    work["conceded"] = np.where(free, 0.0, work["bat_runs"] + np.where(charged, work["extra_runs"], 0.0))
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
    work["phase"] = _phase_labels(work["ball_position"], work["innings_length"])

    legal = work.loc[work["is_legal"]].copy()
    legal["n"] = legal["legal_before"] + 1
    legal["left"] = (legal["innings_length"] - legal["n"] + 1).clip(lower=0)
    legal["phase"] = _phase_labels(legal["n"], legal["innings_length"])

    first_total = work.loc[work["innings"].eq(1)].groupby("match_id")["team_run"].sum()
    legal["target"] = legal["revised_target"]
    missing_target = legal["target"].isna() | legal["target"].le(0)
    # An ordinary chase needs one more than the first innings. A DLS target is used as supplied.
    legal.loc[missing_target, "target"] = legal.loc[missing_target, "match_id"].map(first_total) + 1
    reduced_without_target = legal["is_reduced"].fillna(False).astype(bool) & missing_target
    chase = legal["innings"].eq(2) & legal["target"].notna() & legal["left"].gt(0) & ~reduced_without_target
    needed = (legal["target"] - legal["runs_before"]).clip(lower=0)
    legal["rrr"] = np.where(chase, needed / (legal["left"] / 6.0), np.nan)
    legal["crr"] = np.where(legal["n"].gt(1), legal["runs_before"] / ((legal["n"] - 1) / 6.0), np.nan)
    legal = _attach_pressure(legal)
    legal["striker_out"] = legal["wicket_flag"].eq(1) & legal["dismissed_player_id"].eq(legal["striker_id"])
    legal["bowler_wicket"] = legal["is_bowler_wicket"].fillna(False).astype(bool)
    bye = legal["extras_label"].isin(["bye", "leg-bye", "penalty"])
    legal["charged_runs"] = np.where(bye, 0.0, legal["bat_runs"])
    legal["ladder"] = np.where(legal["comp_group"].eq("IPL"), "IPL", "INT")
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
    chase = legal["innings"].eq(2) & np.isfinite(rate)
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
                gap_wickets[offset + position] = wicket_6 / 6.0 - (wicket_sum[end] - wicket_sum[end - 18]) / 18.0
                gap_runs[offset + position] = run_6 / 6.0 - (run_sum[end] - run_sum[end - 18]) / 18.0
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
    legal["pressure_bat"] = legal["occasion"] * legal["competition"] * legal["ball_bat"] + legal["shock_bat"] + legal["delta_bat"]
    legal["pressure_bowl"] = legal["occasion"] * legal["competition"] * legal["ball_bowl"] + legal["shock_bowl"] + legal["delta_bowl"]
    legal["band"] = _cut_band(legal["pressure_bat"])
    legal["band_bowl"] = _cut_band_within(legal["pressure_bowl"], legal["pace_or_spin"])
    return legal


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
    frame["pressure_bat"] = frame["occasion"] * frame["competition"] * frame["ball_bat"] + frame["shock_bat"] + frame["delta_bat"]
    frame["pressure_bowl"] = frame["occasion"] * frame["competition"] * frame["ball_bowl"] + frame["shock_bowl"] + frame["delta_bowl"]
    frame["band"] = _cut_band(frame["pressure_bat"])
    frame["band_bowl"] = _cut_band_within(frame["pressure_bowl"], frame["pace_or_spin"])
    return frame


def _expectation_keys(phase: str, arm: str, ladder: str) -> tuple[tuple, ...]:
    """Coarse to fine. Each level is shrunk toward the one before it."""
    return (
        ("all",),
        ("phase", phase),
        ("phase_arm", phase, arm),
        ("full", phase, arm, ladder),
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
            keys = _expectation_keys(str(phase[cursor]), str(arm[cursor]), str(this_ladder))
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
        opposite = buckets.get((match, 1 if innings == 2 else 2 if innings == 1 else -1))
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


def form_by_season(events: pd.DataFrame, player_col: str, metric: str, career: pd.Series, higher_better: bool) -> pd.DataFrame:
    rows = []
    for player, frame in events.groupby(player_col, sort=False):
        frame = frame.sort_values(["match_date", "match_id"], kind="mergesort")
        history: list[float] = []
        bar = float(career.loc[player])
        for metric_value, season in zip(frame[metric].to_numpy(dtype=float), frame["season"].to_numpy()):
            if not history:
                score = 0.0
            else:
                window = history[-8:]
                if higher_better:
                    score = float(np.mean([value > bar for value in window])) - 0.5
                else:
                    score = float(np.mean([value < bar for value in window])) - 0.5
            history.append(float(metric_value))
            rows.append({player_col: player, "season": int(season), "form": score})
    if not rows:
        return pd.DataFrame(columns=[player_col, "season", "form"])
    return pd.DataFrame(rows)


def consistency_score(match_values: pd.DataFrame, player_col: str, value_col: str, players: pd.Index, reference: pd.Series, groups: pd.Series | None = None) -> pd.Series:
    grouped = match_values.groupby(player_col)[value_col]
    counts = grouped.size().reindex(players).fillna(0)
    spreads = grouped.std(ddof=0).reindex(players)
    if groups is None:
        known = spreads.dropna()
        ref_known = known[reference.reindex(known.index).fillna(False).astype(bool)]
        typical = float(ref_known.mean()) if len(ref_known) else float(known.mean()) if len(known) else 0.0
        filled = spreads.fillna(typical)
        shrunk = shrink(filled, counts, typical, 8)
        return zscore(-shrunk, reference)
    signed = pd.Series(0.0, index=players)
    labels = groups.reindex(players).fillna("unknown")
    for _, index in labels.groupby(labels, sort=False).groups.items():
        role_players = pd.Index(index)
        known = spreads.reindex(role_players).dropna()
        ref_known = known[reference.reindex(known.index).fillna(False).astype(bool)]
        typical = float(ref_known.mean()) if len(ref_known) else float(known.mean()) if len(known) else 0.0
        filled = spreads.reindex(role_players).fillna(typical)
        shrunk = shrink(filled, counts.reindex(role_players), typical, 8)
        signed.loc[role_players] = zscore(-shrunk, reference).to_numpy()
    return signed


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
    strike_rate = 100 * runs / balls
    average = runs / dismissals.replace(0, np.nan)

    phase_runs = legal.groupby("phase")["bat_runs"].sum()
    phase_balls = legal.groupby("phase").size()
    phase_outs = legal.groupby("phase")["striker_out"].sum()
    phase_sr = 100 * phase_runs / phase_balls
    overall_average = float(runs.sum() / dismissals.sum())
    phase_average = (phase_runs / phase_outs.replace(0, np.nan)).fillna(overall_average)

    phase_counts = legal.pivot_table(index=player, columns="phase", values="bat_runs", aggfunc="size", fill_value=0)
    phase_counts = phase_counts.reindex(ids).fillna(0)
    shares = phase_counts.div(phase_counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    expected_sr = sum(shares[phase] * phase_sr[phase] for phase in shares.columns if phase in phase_sr.index)
    expected_average = sum(shares[phase] * phase_average[phase] for phase in shares.columns if phase in phase_average.index)
    shrunk_sr = shrink(strike_rate, balls, expected_sr, 120)
    shrunk_average = shrink(average.fillna(expected_average), dismissals, expected_average, 4)
    shrunk_average = shrunk_average.where(dismissals.gt(0), expected_average)

    n_eff = weighted_count(legal, player, ids)
    reference = n_eff.ge(REFERENCE_BALLS)
    roles = orders.reindex(ids).map(_batting_role)
    base = 0.5 * zscore_within(shrunk_sr - expected_sr, roles, reference) + 0.5 * zscore_within(shrunk_average - expected_average, roles, reference)

    band_z = {}
    high_n = weighted_count(legal.loc[legal["band"].eq("high")], player, ids)
    for band in BANDS:
        subset = legal.loc[legal["band"].eq(band), [player, "season", "e_bat"]]
        raw = career_rate(subset, ids, player, "e_bat")
        count = weighted_count(subset, player, ids)
        band_z[band] = zscore_within(shrink(raw, count, 0.0, 30), roles, reference)

    innings = (
        legal.groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(runs=("bat_runs", "sum"), balls=("bat_runs", "size"), e_bat=("e_bat", "mean"))
        .reset_index()
    )
    innings["sr"] = 100 * innings["runs"] / innings["balls"]
    compared = innings_comparisons(innings, player, "sr", True)
    compared["label"] = [
        passage_label(row, float(strike_rate.loc[row[player]]), True)
        for _, row in compared.iterrows()
    ]
    peer_mean = compared.groupby(player)["z_passage"].mean()
    peer_n = compared.groupby(player)["z_passage"].count()
    peer = zscore_within(shrink(peer_mean, peer_n, 0.0, 5).reindex(ids).fillna(0.0), roles, reference)
    stood_out = compared.loc[compared["label"].eq("stood out")].groupby(player).size()
    passages = compared.groupby(player).size()
    stood_share = (stood_out / passages).reindex(ids)

    high = (
        legal.loc[legal["band"].eq("high")]
        .groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(runs=("bat_runs", "sum"), balls=("bat_runs", "size"))
        .reset_index()
    )
    high["sr"] = 100 * high["runs"] / high["balls"]
    high_compared = innings_comparisons(high, player, "sr", True)
    scale = float(innings.loc[innings[player].isin(ids[reference]) & innings["balls"].ge(6), "sr"].std(ddof=0))
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    clutch_rows = high_compared.dropna(subset=["z_team"]).copy()
    own_gap = (clutch_rows["metric"] - clutch_rows[player].map(strike_rate)) / scale
    clutch_rows["clutch"] = _clutch_spell(own_gap, clutch_rows["z_team"])
    clutch_mean = clutch_rows.groupby(player)["clutch"].mean()
    clutch_n = clutch_rows.groupby(player)["clutch"].count()
    clutch = zscore_within(shrink(clutch_mean, clutch_n, 0.0, 5).reindex(ids).fillna(0.0), roles, reference)

    qualified = innings.loc[innings["balls"].ge(6)].copy()
    form = form_by_season(qualified, player, "sr", strike_rate, True)
    form_n = qualified.groupby(player).size().reindex(ids).fillna(0.0)
    form_score = zscore_within(shrink(career_rate(form, ids, player, "form"), form_n, 0.0, 8), roles, reference)
    match_values = qualified.groupby([player, "match_id"], sort=False)["e_bat"].mean().reset_index()
    consistency = consistency_score(match_values, player, "e_bat", ids, reference, roles)

    composite = (
        BASELINE_WEIGHT * base
        + ZERO_WEIGHT * band_z["zero"]
        + MEDIUM_WEIGHT * band_z["medium"]
        + HIGH_WEIGHT * band_z["high"]
        + CLUTCH_WEIGHT * clutch
        + PEERS_WEIGHT * peer
        + FORM_WEIGHT * form_score
        + CONSISTENCY_WEIGHT * consistency
    )
    ranked = n_eff.ge(120) & high_n.ge(30)
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
        "form": form_score.to_numpy(),
        "consistency": consistency.to_numpy(),
        "stood_out_share": stood_share.to_numpy(),
        "composite": composite.to_numpy(),
        "ranked": ranked.to_numpy(),
    })
    table["rank"] = np.nan
    order = table.loc[table["ranked"]].sort_values(["composite", "player_id"], ascending=[False, True]).index
    table.loc[order, "rank"] = np.arange(1, len(order) + 1)
    return table.sort_values(["ranked", "rank", "player_name"], ascending=[False, True, True]).reset_index(drop=True)


def score_bowlers(legal: pd.DataFrame, work: pd.DataFrame) -> pd.DataFrame:
    player = "bowler_id"
    ids = pd.Index(legal[player].unique(), name=player)
    names = _names(legal, player, "bowler_name")
    arm = legal.groupby(player)["pace_or_spin"].agg(_mode).reindex(ids)
    legal_balls = legal.groupby(player).size().reindex(ids).astype(float)
    wickets = work.groupby(player)["is_bowler_wicket"].sum().reindex(ids).fillna(0).astype(float)
    # is_bowler_wicket may be bool; sum works. Super overs already left work.
    conceded = work.groupby(player)["conceded"].sum().reindex(ids).fillna(0).astype(float)
    economy = 6 * conceded / legal_balls
    balls_per_wicket = legal_balls / wickets.replace(0, np.nan)

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

    phase_counts = legal.pivot_table(index=player, columns="phase", values="bat_runs", aggfunc="size", fill_value=0)
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

    shrunk_economy = shrink(economy, legal_balls, expected_economy, 120)
    shrunk_balls = shrink(balls_per_wicket.fillna(expected_balls), wickets, expected_balls, 4)
    shrunk_balls = shrunk_balls.where(wickets.gt(0), expected_balls)
    n_eff = weighted_count(legal, player, ids)
    reference = n_eff.ge(REFERENCE_BALLS)
    base = 0.5 * zscore(expected_economy - shrunk_economy, reference) + 0.5 * zscore(expected_balls - shrunk_balls, reference)

    band_z = {}
    high_n = weighted_count(legal.loc[legal["band_bowl"].eq("high")], player, ids)
    for band in BANDS:
        subset = legal.loc[legal["band_bowl"].eq(band), [player, "season", "e_bowl"]]
        raw = career_rate(subset, ids, player, "e_bowl")
        count = weighted_count(subset, player, ids)
        band_z[band] = zscore(shrink(raw, count, 0.0, 30), reference)

    spell_conceded = work.groupby(["match_id", "innings", player])["conceded"].sum()
    spells = (
        legal.groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(balls=("bat_runs", "size"), e_bowl=("e_bowl", "mean"), charged=("charged_runs", "sum"))
        .reset_index()
    )
    spells["conceded"] = spells.set_index(["match_id", "innings", player]).index.map(spell_conceded)
    spells["economy"] = 6 * spells["conceded"] / spells["balls"]
    compared = innings_comparisons(spells, player, "economy", False)
    compared["label"] = [
        passage_label(row, float(economy.loc[row[player]]), False)
        for _, row in compared.iterrows()
    ]
    peer_mean = compared.groupby(player)["z_passage"].mean()
    peer_n = compared.groupby(player)["z_passage"].count()
    peer = component_frame(shrink(peer_mean, peer_n, 0.0, 5), ids, reference)
    stood_out = compared.loc[compared["label"].eq("stood out")].groupby(player).size()
    passages = compared.groupby(player).size()
    stood_share = (stood_out / passages).reindex(ids)

    high_spells = (
        legal.loc[legal["band_bowl"].eq("high")]
        .groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(balls=("charged_runs", "size"), charged=("charged_runs", "sum"))
        .reset_index()
    )
    high_spells["economy"] = 6 * high_spells["charged"] / high_spells["balls"]
    high_compared = innings_comparisons(high_spells, player, "economy", False)
    scale = float(spells.loc[spells[player].isin(ids[reference]) & spells["balls"].ge(6), "economy"].std(ddof=0))
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    clutch_rows = high_compared.dropna(subset=["z_team"]).copy()
    own_gap = (clutch_rows[player].map(economy) - clutch_rows["metric"]) / scale
    clutch_rows["clutch"] = _clutch_spell(own_gap, clutch_rows["z_team"])
    clutch_mean = clutch_rows.groupby(player)["clutch"].mean()
    clutch_n = clutch_rows.groupby(player)["clutch"].count()
    clutch = component_frame(shrink(clutch_mean, clutch_n, 0.0, 5), ids, reference)

    qualified = spells.loc[spells["balls"].ge(6)].copy()
    form = form_by_season(qualified, player, "economy", economy, False)
    form_n = qualified.groupby(player).size().reindex(ids).fillna(0.0)
    form_score = zscore(shrink(career_rate(form, ids, player, "form"), form_n, 0.0, 8), reference)
    match_values = qualified.groupby([player, "match_id"], sort=False)["e_bowl"].mean().reset_index()
    consistency = consistency_score(match_values, player, "e_bowl", ids, reference)

    composite = (
        BASELINE_WEIGHT * base
        + ZERO_WEIGHT * band_z["zero"]
        + MEDIUM_WEIGHT * band_z["medium"]
        + HIGH_WEIGHT * band_z["high"]
        + CLUTCH_WEIGHT * clutch
        + PEERS_WEIGHT * peer
        + FORM_WEIGHT * form_score
        + CONSISTENCY_WEIGHT * consistency
    )
    ranked = n_eff.ge(120) & high_n.ge(30)
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
        "form": form_score.to_numpy(),
        "consistency": consistency.to_numpy(),
        "stood_out_share": stood_share.to_numpy(),
        "composite": composite.to_numpy(),
        "ranked": ranked.to_numpy(),
    })
    table["rank"] = np.nan
    order = table.loc[table["ranked"]].sort_values(["composite", "player_id"], ascending=[False, True]).index
    table.loc[order, "rank"] = np.arange(1, len(order) + 1)
    return table.sort_values(["ranked", "rank", "player_name"], ascending=[False, True, True]).reset_index(drop=True)


def top_table(table: pd.DataFrame, columns: list[str], n: int = 10) -> pd.DataFrame:
    ranked = table.loc[table["ranked"]].nsmallest(n, "rank")
    show = ranked[columns].copy()
    for column in show.columns:
        if pd.api.types.is_float_dtype(show[column]):
            show[column] = show[column].round(3)
    return show
