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
REFERENCE_BALLS = 120
RANK_HIGH = 30
# A competition-phase-arm cell thinner than this falls back to the ladder, then the phase.
CELL_BALLS = 200
# The published weights were 0.15, 0.10, 0.15, 0.20, 0.10, 0.05, 0.05.
# Clutch is reported but left out, because it repeats the high band.
# Dividing by their total keeps those ratios and makes the composite a weighted mean.
_RAW_WEIGHTS = {
    "baseline": 0.15,
    "zero": 0.10,
    "medium": 0.15,
    "high": 0.20,
    "peers": 0.10,
    "form": 0.05,
    "consistency": 0.05,
}
COMPONENT_WEIGHTS = {name: value / sum(_RAW_WEIGHTS.values()) for name, value in _RAW_WEIGHTS.items()}
VENUE_STRENGTH = 2400.0


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
    observed = value.astype(float).fillna(0.0)
    return (count * observed + strength * prior) / (count + strength)


def zscore(value: pd.Series, reference: pd.Series) -> pd.Series:
    sample = value[reference.reindex(value.index).fillna(False).astype(bool)]
    center = sample.mean()
    spread = sample.std(ddof=0)
    if pd.isna(spread) or spread == 0:
        return pd.Series(0.0, index=value.index)
    return ((value - center) / spread).clip(-3, 3)


def career_rate(frame: pd.DataFrame, player_ids: pd.Index, player_col: str, value_col: str) -> pd.Series:
    """Decay-weighted mean of the balls a player actually faced. A missed season is left out."""
    if frame.empty:
        return pd.Series(np.nan, index=player_ids)
    weights = frame["season"].map(WEIGHT).astype(float)
    weighted = frame[value_col].astype(float) * weights
    numerator = weighted.groupby(frame[player_col]).sum()
    denominator = weights.groupby(frame[player_col]).sum().replace(0, np.nan)
    return (numerator / denominator).reindex(player_ids)


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
        "match_id", "match_date", "season", "comp_group", "comp_name", "stage", "venue_id",
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


def _band_from_points(points: pd.Series) -> pd.Series:
    """The same score is the same band in both innings. High is 5 or more, medium is 3 or 4."""
    values = points.to_numpy(dtype=float)
    labels = np.where(values >= 5, "high", np.where(values >= 3, "medium", "zero"))
    return pd.Series(labels, index=points.index)


def _wicket_state(wickets: pd.Series) -> pd.Series:
    """Coarse wickets-down state. Seven down is not a harder ball than two down for the rating."""
    values = wickets.to_numpy()
    labels = np.where(values <= 1, "0-1", np.where(values <= 4, "2-4", "5+"))
    return pd.Series(labels, index=wickets.index)


def _inherit_situation(work: pd.DataFrame) -> None:
    """A wide or no-ball takes the phase and band of the next legal ball in the innings."""
    columns = ["phase", "band", "pressure_points"]
    marked = work[columns].copy()
    marked.loc[~work["is_legal"], columns] = np.nan
    grouped = marked.groupby([work["match_id"], work["innings"]], sort=False)
    filled = grouped.bfill()
    missing = filled["phase"].isna()
    if bool(missing.any()):
        filled.loc[missing, columns] = grouped.ffill().loc[missing, columns]
    work[columns] = filled


def add_situation(balls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tag every non-super-over ball. Batter ratings use the legal rows."""
    work = balls.loc[~balls["is_super_over"].astype(bool)].copy()
    work["bat_runs"] = work["runs"].fillna(0.0)
    label = work["extras_label"].fillna("ordinary")
    wide = label.eq("wide")
    noball = label.eq("no-ball")
    free = label.isin(["bye", "leg-bye", "penalty"])
    # The file has no bye amounts and no runs beyond the one-run penalty on a wide.
    penalty = np.where(wide | noball, 1.0, 0.0)
    work["team_run"] = work["bat_runs"] + penalty
    work["conceded"] = np.where(free, 0.0, work["bat_runs"] + penalty)
    work["is_legal"] = work["is_legal"].astype(bool)
    work["wicket_flag"] = work["is_wicket"].fillna(False).astype(bool).astype(int)
    work["bowler_wicket"] = work["is_bowler_wicket"].fillna(False).astype(bool)
    work["striker_out"] = work["wicket_flag"].eq(1) & work["dismissed_player_id"].eq(work["striker_id"])
    work["charged_runs"] = np.where(free, 0.0, work["bat_runs"])
    work["ladder"] = np.where(work["comp_group"].eq("IPL"), "IPL", "INT")
    work = work.sort_values(["match_id", "innings", "innings_ball_num"], kind="mergesort")
    grouped = work.groupby(["match_id", "innings"], sort=False)
    work["runs_before"] = grouped["team_run"].cumsum() - work["team_run"]
    work["wickets_before"] = grouped["wicket_flag"].cumsum() - work["wicket_flag"]
    work["legal_before"] = grouped["is_legal"].cumsum() - work["is_legal"].astype(int)
    work["wicket_state"] = _wicket_state(work["wickets_before"])

    length = np.where(
        work["innings"].eq(1),
        work["first_innings_balls"],
        work["second_innings_balls"],
    )
    work["innings_length"] = pd.Series(length, index=work.index).fillna(120).clip(lower=1)

    legal = work.loc[work["is_legal"]].copy()
    legal["n"] = legal["legal_before"] + 1
    legal["left"] = (legal["innings_length"] - legal["n"] + 1).clip(lower=0)
    legal["phase"] = _phase_labels(legal["n"], legal["innings_length"])

    first_total = work.loc[work["innings"].eq(1)].groupby("match_id")["team_run"].sum()
    legal["target"] = legal["revised_target"]
    missing_target = legal["target"].isna() | legal["target"].le(0)
    # An ordinary chase needs one more than the first innings. A DLS target is used as supplied.
    legal.loc[missing_target, "target"] = legal.loc[missing_target, "match_id"].map(first_total) + 1
    chase = legal["innings"].eq(2) & legal["target"].notna() & legal["left"].gt(0)
    needed = (legal["target"] - legal["runs_before"]).clip(lower=0)
    legal["rrr"] = np.where(chase, needed / (legal["left"] / 6.0), np.nan)

    # The powerplay is worth 2 and the death is worth 3, so a league death over with two wickets down is high.
    phase_points = legal["phase"].map({"powerplay": 2, "middle": 0, "death": 3}).fillna(0).to_numpy(dtype=int)
    wickets = legal["wickets_before"].to_numpy()
    wicket_points = np.where(wickets <= 1, 0, 2).astype(int)
    stakes = np.where(
        legal["stage"].eq("Final"),
        2,
        np.where(legal["knock_out"].fillna(0).astype(int).eq(1), 1, 0),
    ).astype(int)
    rain = legal["is_reduced"].fillna(False).astype(bool).to_numpy().astype(int)
    rate = legal["rrr"].to_numpy(dtype=float)
    chase_flag = chase.to_numpy()
    chase_points = np.where(~chase_flag, 0, np.where(rate >= 12, 2, np.where(rate >= 8, 1, 0))).astype(int)
    legal["pressure_points"] = phase_points + wicket_points + stakes + rain + chase_points
    legal["band"] = _band_from_points(legal["pressure_points"])

    for column in ["n", "left", "phase", "target", "rrr", "pressure_points", "band"]:
        work.loc[legal.index, column] = legal[column]
    _inherit_situation(work)
    work["match_date"] = pd.to_datetime(work["match_date"])
    legal = work.loc[work["is_legal"]].copy()
    return work, legal


def band_summary(legal: pd.DataFrame) -> pd.DataFrame:
    counts = legal["band"].value_counts().reindex(BANDS).fillna(0).astype(int)
    frame = counts.rename("balls").to_frame()
    frame["share"] = frame["balls"] / frame["balls"].sum()
    return frame


def _distribution(frame: pd.DataFrame, column: str, clip: bool) -> dict:
    def store(rate: float) -> float:
        if clip:
            return float(np.clip(rate, 0.002, 0.40))
        return float(rate)

    table = {("all",): store(frame[column].mean())}
    levels = (
        (["comp_group", "phase", "pace_or_spin", "wicket_state"], "group"),
        (["comp_group", "phase", "pace_or_spin"], "group"),
        (["comp_group", "phase"], "group"),
        (["ladder", "phase", "pace_or_spin", "wicket_state"], "ladder"),
        (["ladder", "phase", "pace_or_spin"], "ladder"),
        (["ladder", "phase"], "ladder"),
        (["phase", "wicket_state"], "phase"),
        (["phase"], "phase"),
    )
    for columns, prefix in levels:
        for key, part in frame.groupby(columns, dropna=False):
            stored = key if isinstance(key, tuple) else (key,)
            if any(pd.isna(part_key) for part_key in stored) or len(part) < CELL_BALLS:
                continue
            table[(prefix, *tuple(str(part_key) for part_key in stored))] = store(part[column].mean())
    return table


def _key_part(value):
    if value is None or pd.isna(value):
        return None
    return str(value)


def _lookup(table: dict, group, ladder, phase, arm, wickets) -> float:
    group_key = _key_part(group)
    ladder_key = _key_part(ladder)
    phase_key = _key_part(phase)
    arm_key = _key_part(arm)
    wicket_key = _key_part(wickets)
    for key in (
        ("group", group_key, phase_key, arm_key, wicket_key),
        ("group", group_key, phase_key, arm_key),
        ("group", group_key, phase_key),
        ("ladder", ladder_key, phase_key, arm_key, wicket_key),
        ("ladder", ladder_key, phase_key, arm_key),
        ("ladder", ladder_key, phase_key),
        ("phase", phase_key, wicket_key),
        ("phase", phase_key),
        ("all",),
    ):
        if None in key or key not in table:
            continue
        return table[key]
    return table[("all",)]


def expectation_tables(legal: pd.DataFrame) -> tuple[dict, dict, dict, float]:
    rho = float(legal["bat_runs"].mean())
    mu = _distribution(legal, "bat_runs", clip=False)
    p_out = _distribution(legal, "striker_out", clip=True)
    p_bowl = _distribution(legal, "bowler_wicket", clip=True)
    return mu, p_out, p_bowl, rho


def _logit(probability: float) -> float:
    probability = min(max(probability, 1e-4), 1 - 1e-4)
    return float(np.log(probability / (1 - probability)))


def _venue_key(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return int(value)


def run_elo(
    work: pd.DataFrame,
    mu: dict,
    p_out: dict,
    p_bowl: dict,
    k_run: float = 4.0,
    k_wicket: float = 16.0,
    k_team: float = 20.0,
) -> pd.DataFrame:
    frame = work.sort_values(["match_date", "match_id", "innings", "innings_ball_num"], kind="mergesort")
    bat_rating: dict[tuple[int, str], float] = {}
    bowl_rating: dict[tuple[int, str], float] = {}
    team_rating: dict[tuple[int, str], float] = {}
    venue_runs: dict[int, float] = {}
    venue_balls: dict[int, int] = {}
    seen_runs = 0.0
    seen_balls = 0
    e_bat = np.full(len(frame), np.nan)
    e_bowl = np.zeros(len(frame))

    match_id = frame["match_id"].to_numpy()
    ladder = frame["ladder"].to_numpy()
    group = frame["comp_group"].to_numpy()
    striker = frame["striker_id"].to_numpy()
    bowler = frame["bowler_id"].to_numpy()
    batting_side = frame["batting_team_id"].to_numpy()
    bowling_side = frame["bowling_team_id"].to_numpy()
    home = frame["home_team_id"].to_numpy()
    away = frame["away_team_id"].to_numpy()
    winner = frame["win_team_id"].to_numpy()
    phase = frame["phase"].to_numpy()
    arm = frame["pace_or_spin"].to_numpy()
    wickets = frame["wicket_state"].to_numpy()
    venue_id = frame["venue_id"].to_numpy()
    runs = frame["bat_runs"].to_numpy(dtype=float)
    conceded = frame["conceded"].to_numpy(dtype=float)
    dismissed = frame["striker_out"].to_numpy(dtype=bool)
    bowler_wicket = frame["bowler_wicket"].to_numpy(dtype=bool)
    legal_ball = frame["is_legal"].to_numpy(dtype=bool)
    noball = frame["extras_label"].fillna("ordinary").eq("no-ball").to_numpy()
    illegal = ~frame["is_legal"]
    if bool(illegal.any()):
        p_illegal = float(np.clip(frame.loc[illegal, "bowler_wicket"].mean(), 0.002, 0.40))
    else:
        p_illegal = 0.002

    def ground_rating(key) -> float:
        count = venue_balls.get(key, 0)
        if key is None or count == 0 or seen_balls == 0:
            return 1500.0
        rate = venue_runs[key] / count
        rho = seen_runs / seen_balls
        return 1500.0 + 1000.0 * (count / (count + VENUE_STRENGTH)) * (rate - rho)

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
            batter_now = bat_rating.get((striker_id, this_ladder), 1500.0)
            bowler_now = bowl_rating.get((bowler_id, this_ladder), 1500.0)
            ground = _venue_key(venue_id[cursor])
            gap = (
                0.15 * (batter_now - bowler_now) / 400.0
                + 0.05 * (pre_side.get(int(batting_side[cursor]), 1500.0) - pre_side.get(int(bowling_side[cursor]), 1500.0)) / 400.0
                + 0.10 * (ground_rating(ground) - 1500.0) / 400.0
            )
            mean_runs = _lookup(mu, group[cursor], this_ladder, phase[cursor], arm[cursor], wickets[cursor])
            expected_matchup = min(max(mean_runs * np.exp(gap), 0.0), 6.0)
            is_legal = bool(legal_ball[cursor])
            if is_legal:
                expected_bowl = expected_matchup
            elif bool(noball[cursor]):
                expected_bowl = expected_matchup + 1.0
            else:
                expected_bowl = 1.0
            p_dismiss = _lookup(p_out, group[cursor], this_ladder, phase[cursor], arm[cursor], wickets[cursor])
            if is_legal:
                p_credit = _lookup(p_bowl, group[cursor], this_ladder, phase[cursor], arm[cursor], wickets[cursor])
                expected_wicket = min(max(1.0 / (1.0 + np.exp(-(_logit(p_credit) - gap))), 0.002), 0.40)
            else:
                expected_wicket = p_illegal
            expected_out = min(max(1.0 / (1.0 + np.exp(-(_logit(p_dismiss) - gap))), 0.002), 0.40)
            wicket_flag = 1.0 if bowler_wicket[cursor] else 0.0
            bowl_now = bowler_now + k_run * (expected_bowl - conceded[cursor]) + k_wicket * (wicket_flag - expected_wicket)
            bowl_rating[(bowler_id, this_ladder)] = bowl_now
            e_bowl[cursor] = (expected_bowl - conceded[cursor]) + 4.0 * (wicket_flag - expected_wicket)
            if is_legal:
                out_flag = 1.0 if dismissed[cursor] else 0.0
                e_bat[cursor] = (runs[cursor] - expected_matchup) - 4.0 * (out_flag - expected_out)
                bat_rating[(striker_id, this_ladder)] = (
                    batter_now + k_run * (runs[cursor] - expected_matchup) - k_wicket * (out_flag - expected_out)
                )
                if ground is not None:
                    venue_runs[ground] = venue_runs.get(ground, 0.0) + runs[cursor]
                    venue_balls[ground] = venue_balls.get(ground, 0) + 1
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
        "grounds": int(len(venue_balls)),
    }
    scored.attrs["elo_summary"] = summary
    return scored


def fit_elo(work: pd.DataFrame, mu: dict, p_out: dict, p_bowl: dict) -> pd.DataFrame:
    scored = run_elo(work, mu, p_out, p_bowl)
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
        scored = run_elo(work, mu, p_out, p_bowl, k_run=2.0, k_wicket=8.0, k_team=10.0)
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
                    if not higher_better:
                        gap = -gap
                    opp_z = float(min(max(gap, -3.0), 3.0))
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
    team_z = row["z_team"]
    if pd.notna(team_z) and team_z > 0.5 and beat_self:
        return "stood out"
    if pd.notna(team_z) and team_z > 0.5:
        return "above the side"
    if pd.notna(team_z) and abs(team_z) <= 0.5:
        return "in line"
    if pd.notna(row["team_mean"]) and pd.notna(row["opp_mean"]):
        if abs(row["metric"] - row["opp_mean"]) <= abs(row["metric"] - row["team_mean"]):
            return "matched the other side"
    return "below the side"


def clutch_gap(metric: pd.Series, baseline: pd.Series, higher_better: bool, scale: float) -> pd.Series:
    """Positive when the passage is better than the player's own rate."""
    gap = (metric.astype(float) - baseline.astype(float)) / scale
    return gap if higher_better else -gap


def recent_form(
    innings: pd.DataFrame,
    player_col: str,
    amount_col: str,
    balls_col: str,
    multiplier: float,
    higher_better: bool,
) -> tuple[pd.Series, pd.Series]:
    """Last eight qualifying innings against the ball-weighted rate from earlier balls."""
    if innings.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    qualified = innings.loc[innings[balls_col].ge(6)].copy()
    if qualified.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    qualified = qualified.sort_values([player_col, "match_date", "match_id", "innings"], kind="mergesort")
    qualified["from_end"] = qualified.groupby(player_col, sort=False).cumcount(ascending=False)
    window = qualified.loc[qualified["from_end"].lt(8), [player_col, "match_id", "innings", "match_date"]].copy()
    window["in_window"] = True
    start = window.groupby(player_col)["match_date"].min()
    tagged = innings.merge(window[[player_col, "match_id", "innings", "in_window"]], on=[player_col, "match_id", "innings"], how="left")
    tagged["window_start"] = tagged[player_col].map(start)

    def rates(frame: pd.DataFrame) -> pd.Series:
        number = frame.groupby(player_col)[amount_col].sum()
        balls = frame.groupby(player_col)[balls_col].sum().replace(0, np.nan)
        return multiplier * number / balls

    recent = rates(tagged.loc[tagged["in_window"].eq(True)])
    earlier = rates(tagged.loc[tagged["in_window"].isna() & tagged["match_date"].lt(tagged["window_start"])])
    window_balls = tagged.loc[tagged["in_window"].eq(True)].groupby(player_col)[balls_col].sum()
    score = recent - earlier
    if not higher_better:
        score = -score
    score = score.where(earlier.notna() & recent.notna())
    return score, window_balls


def consistency_score(match_values: pd.DataFrame, player_col: str, value_col: str, players: pd.Index, reference: pd.Series) -> pd.Series:
    grouped = match_values.groupby(player_col)[value_col]
    counts = grouped.size().reindex(players).fillna(0)
    spreads = grouped.std(ddof=0).reindex(players)
    known = spreads.dropna()
    ref_known = known[reference.reindex(known.index).fillna(False).astype(bool)]
    typical = float(ref_known.mean()) if len(ref_known) else float(known.mean()) if len(known) else 0.0
    filled = spreads.fillna(typical)
    shrunk = shrink(filled, counts, typical, 8)
    return zscore(-shrunk, reference)


def component_frame(raw: pd.Series, players: pd.Index, reference: pd.Series) -> pd.Series:
    return zscore(raw.reindex(players).fillna(0.0), reference)


def _form_component(score: pd.Series, window_balls: pd.Series, players: pd.Index, reference: pd.Series) -> pd.Series:
    score = score.reindex(players)
    count = window_balls.reindex(players)
    count = count.where(score.notna(), 0).fillna(0.0)
    return zscore(shrink(score, count, 0.0, 48), reference)


def _composite(parts: dict[str, pd.Series]) -> pd.Series:
    total = None
    for name, weight in COMPONENT_WEIGHTS.items():
        term = weight * parts[name]
        total = term if total is None else total + term
    return total


def _cell_table(frame: pd.DataFrame, number_col: str, balls_col: str, multiplier: float, support_col: str = "_balls") -> dict:
    """Competition, phase, and arm first. Thin cells fall back to the ladder, then the phase."""
    table = {}
    denominator = float(frame[balls_col].sum())
    if denominator:
        table[("all",)] = float(multiplier * frame[number_col].sum() / denominator)
    levels = (
        (["comp_group", "phase", "pace_or_spin", "wicket_state"], "group"),
        (["comp_group", "phase", "pace_or_spin"], "group"),
        (["comp_group", "phase", "wicket_state"], "group"),
        (["comp_group", "phase"], "group"),
        (["ladder", "phase", "pace_or_spin", "wicket_state"], "ladder"),
        (["ladder", "phase", "pace_or_spin"], "ladder"),
        (["ladder", "phase", "wicket_state"], "ladder"),
        (["ladder", "phase"], "ladder"),
        (["phase", "wicket_state"], "phase"),
        (["phase"], "phase"),
    )
    for columns, prefix in levels:
        value_columns = list(dict.fromkeys([number_col, balls_col, support_col]))
        grouped = frame.groupby(columns, dropna=False)[value_columns].sum()
        for key, row in grouped.iterrows():
            stored = key if isinstance(key, tuple) else (key,)
            if any(pd.isna(part) for part in stored):
                continue
            if float(row[support_col]) < CELL_BALLS or float(row[balls_col]) == 0:
                continue
            table[(prefix, *tuple(str(part) for part in stored))] = float(multiplier * row[number_col] / row[balls_col])
    return table


def _cell_rate(table: dict, group, ladder, phase, arm, wickets) -> float:
    group, ladder, phase, arm, wickets = str(group), str(ladder), str(phase), str(arm), str(wickets)
    for key in (
        ("group", group, phase, arm, wickets),
        ("group", group, phase, arm),
        ("group", group, phase, wickets),
        ("group", group, phase),
        ("ladder", ladder, phase, arm, wickets),
        ("ladder", ladder, phase, arm),
        ("ladder", ladder, phase, wickets),
        ("ladder", ladder, phase),
        ("phase", phase, wickets),
        ("phase", phase),
        ("all",),
    ):
        if key in table:
            return table[key]
    return np.nan


def _expected_rates(shares: pd.Series, economy: dict, balls_per_wicket: dict) -> tuple[pd.Series, pd.Series]:
    frame = shares.rename("n").reset_index()
    player_col = shares.index.names[0]
    frame["economy"] = [
        _cell_rate(economy, group, ladder, phase, arm, wickets)
        for group, ladder, phase, arm, wickets in zip(
            frame["comp_group"], frame["ladder"], frame["phase"], frame["pace_or_spin"], frame["wicket_state"]
        )
    ]
    frame["bpw"] = [
        _cell_rate(balls_per_wicket, group, ladder, phase, arm, wickets)
        for group, ladder, phase, arm, wickets in zip(
            frame["comp_group"], frame["ladder"], frame["phase"], frame["pace_or_spin"], frame["wicket_state"]
        )
    ]
    weight = frame.groupby(player_col)["n"].sum()
    expected_economy = (frame["n"] * frame["economy"]).groupby(frame[player_col]).sum() / weight
    expected_balls = (frame["n"] * frame["bpw"]).groupby(frame[player_col]).sum() / weight
    return expected_economy, expected_balls


def _environment_rates(legal: pd.DataFrame) -> tuple[dict, dict]:
    """Strike rate and average by competition and phase, with ladder and phase fallbacks."""
    strike = {}
    average = {}

    def add(prefix: str, key, part: pd.DataFrame) -> None:
        stored = key if isinstance(key, tuple) else (key,)
        if any(pd.isna(part_key) for part_key in stored) or len(part) < CELL_BALLS:
            return
        label = (prefix, *tuple(str(part_key) for part_key in stored))
        strike[label] = 100 * float(part["bat_runs"].sum()) / len(part)
        outs = float(part["striker_out"].sum())
        if outs > 0:
            average[label] = float(part["bat_runs"].sum()) / outs

    for columns, prefix in (
        (["comp_group", "phase", "wicket_state"], "group"),
        (["comp_group", "phase"], "group"),
        (["ladder", "phase", "wicket_state"], "ladder"),
        (["ladder", "phase"], "ladder"),
        (["phase", "wicket_state"], "phase"),
        (["phase"], "phase"),
    ):
        for key, part in legal.groupby(columns, dropna=False):
            add(prefix, key, part)
    strike[("all",)] = 100 * float(legal["bat_runs"].sum()) / len(legal)
    average[("all",)] = float(legal["bat_runs"].sum()) / float(legal["striker_out"].sum())
    return strike, average


def _pick_environment(table: dict, group, ladder, phase, wickets) -> float:
    for key in (
        ("group", str(group), str(phase), str(wickets)),
        ("group", str(group), str(phase)),
        ("ladder", str(ladder), str(phase), str(wickets)),
        ("ladder", str(ladder), str(phase)),
        ("phase", str(phase), str(wickets)),
        ("phase", str(phase)),
        ("all",),
    ):
        if key in table:
            return table[key]
    return table[("all",)]


def _band_scores(frame: pd.DataFrame, counted: pd.DataFrame, player_col: str, value_col: str, players: pd.Index) -> dict[str, pd.Series]:
    """Band residual minus the player's own overall residual. Thin bands shrink toward that level."""
    overall = career_rate(frame, players, player_col, value_col).fillna(0.0)
    scores = {}
    for band in BANDS:
        subset = frame.loc[frame["band"].eq(band)]
        raw = career_rate(subset, players, player_col, value_col)
        count = weighted_count(subset, player_col, players)
        contrast = shrink(raw, count, overall, 120) - overall
        support = weighted_count(counted.loc[counted["band"].eq(band)], player_col, players)
        scores[band] = zscore(contrast, support.ge(RANK_HIGH))
    return scores


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

    strike_cells, average_cells = _environment_rates(legal)
    share_counts = legal.groupby([player, "comp_group", "ladder", "phase", "wicket_state"]).size().rename("n").reset_index()
    share_counts["sr"] = [
        _pick_environment(strike_cells, group, ladder, phase, wickets)
        for group, ladder, phase, wickets in zip(
            share_counts["comp_group"], share_counts["ladder"], share_counts["phase"], share_counts["wicket_state"]
        )
    ]
    share_counts["average"] = [
        _pick_environment(average_cells, group, ladder, phase, wickets)
        for group, ladder, phase, wickets in zip(
            share_counts["comp_group"], share_counts["ladder"], share_counts["phase"], share_counts["wicket_state"]
        )
    ]
    expected_sr = (share_counts["n"] * share_counts["sr"]).groupby(share_counts[player]).sum() / share_counts.groupby(player)["n"].sum()
    expected_average = (share_counts["n"] * share_counts["average"]).groupby(share_counts[player]).sum() / share_counts.groupby(player)["n"].sum()
    expected_sr = expected_sr.reindex(ids)
    expected_average = expected_average.reindex(ids)
    shrunk_sr = shrink(strike_rate, balls, expected_sr, 120)
    shrunk_average = shrink(average.fillna(expected_average), dismissals, expected_average, 4)
    shrunk_average = shrunk_average.where(dismissals.gt(0), expected_average)

    n_eff = weighted_count(legal, player, ids)
    reference = n_eff.ge(REFERENCE_BALLS)
    base = 0.5 * zscore(shrunk_sr - expected_sr, reference) + 0.5 * zscore(shrunk_average - expected_average, reference)

    high_n = weighted_count(legal.loc[legal["band"].eq("high")], player, ids)
    band_z = _band_scores(legal, legal, player, "e_bat", ids)
    high_reference = high_n.ge(RANK_HIGH)

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
    peer = component_frame(shrink(peer_mean, peer_n, 0.0, 5), ids, reference)
    stood_out = compared.loc[compared["label"].eq("stood out")].groupby(player).size()
    passages = compared.groupby(player).size()
    stood_share = (stood_out / passages).reindex(ids)

    high = (
        legal.loc[legal["band"].eq("high")]
        .groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(runs=("bat_runs", "sum"), balls=("bat_runs", "size"))
        .reset_index()
    )
    high = high.loc[high["balls"].ge(6)].copy()
    scale = float(innings.loc[innings[player].isin(ids[reference]) & innings["balls"].ge(6), "sr"].std(ddof=0))
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    if high.empty:
        clutch = zscore(pd.Series(0.0, index=ids), high_reference)
    else:
        high["clutch"] = clutch_gap(100 * high["runs"] / high["balls"], high[player].map(strike_rate), True, scale)
        clutch_mean = high.groupby(player)["clutch"].mean()
        clutch_n = high.groupby(player)["clutch"].count()
        clutch = component_frame(shrink(clutch_mean, clutch_n, 0.0, 5), ids, high_reference)

    form_score, form_balls = recent_form(innings, player, "runs", "balls", 100.0, True)
    form_component = _form_component(form_score, form_balls, ids, reference)
    qualified = innings.loc[innings["balls"].ge(6)].copy()
    match_values = qualified.groupby([player, "match_id"], sort=False)["e_bat"].mean().reset_index()
    consistency = consistency_score(match_values, player, "e_bat", ids, reference)

    composite = _composite({
        "baseline": base,
        "zero": band_z["zero"],
        "medium": band_z["medium"],
        "high": band_z["high"],
        "peers": peer,
        "form": form_component,
        "consistency": consistency,
    })
    ranked = n_eff.ge(REFERENCE_BALLS) & high_n.ge(RANK_HIGH)
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
        "form": form_component.to_numpy(),
        "consistency": consistency.to_numpy(),
        "stood_out_share": stood_share.to_numpy(),
        "composite": composite.to_numpy(),
        "ranked": ranked.to_numpy(),
    })
    table["rank"] = np.nan
    order = table.loc[table["ranked"]].sort_values(["composite", "player_id"], ascending=[False, True]).index
    table.loc[order, "rank"] = np.arange(1, len(order) + 1)
    return table.sort_values(["ranked", "rank", "player_name"], ascending=[False, True, True]).reset_index(drop=True)


def score_bowlers(work: pd.DataFrame) -> pd.DataFrame:
    player = "bowler_id"
    legal = work.loc[work["is_legal"]]
    ids = pd.Index(work[player].unique(), name=player)
    names = _names(work, player, "bowler_name")
    arm = legal.groupby(player)["pace_or_spin"].agg(_mode).reindex(ids)
    legal_balls = legal.groupby(player).size().reindex(ids).fillna(0).astype(float)
    wickets = work.groupby(player)["bowler_wicket"].sum().reindex(ids).fillna(0).astype(float)
    conceded = work.groupby(player)["conceded"].sum().reindex(ids).fillna(0).astype(float)
    economy = 6 * conceded / legal_balls.replace(0, np.nan)
    balls_per_wicket = legal_balls / wickets.replace(0, np.nan)

    marked = work.assign(_balls=work["is_legal"].astype(int), _wickets=work["bowler_wicket"].astype(int))
    economy_table = _cell_table(marked, "conceded", "_balls", 6.0)
    bpw_table = _cell_table(marked, "_balls", "_wickets", 1.0)

    shares = legal.groupby([player, "comp_group", "ladder", "phase", "pace_or_spin", "wicket_state"]).size()
    shares = shares.loc[shares.index.get_level_values("pace_or_spin").notna()]
    expected_economy, expected_balls = _expected_rates(shares, economy_table, bpw_table)
    expected_economy = expected_economy.reindex(ids)
    expected_balls = expected_balls.reindex(ids)
    global_economy = float(6 * work["conceded"].sum() / len(legal)) if len(legal) else 0.0
    global_balls = float(len(legal) / work["bowler_wicket"].sum()) if work["bowler_wicket"].sum() else np.nan
    expected_economy = expected_economy.fillna(global_economy)
    expected_balls = expected_balls.fillna(global_balls)

    shrunk_economy = shrink(economy, legal_balls, expected_economy, 120)
    shrunk_balls = shrink(balls_per_wicket.fillna(expected_balls), wickets, expected_balls, 4)
    shrunk_balls = shrunk_balls.where(wickets.gt(0), expected_balls)
    n_eff = weighted_count(legal, player, ids)
    reference = n_eff.ge(REFERENCE_BALLS)
    base = 0.5 * zscore(expected_economy - shrunk_economy, reference) + 0.5 * zscore(expected_balls - shrunk_balls, reference)

    high_legal = work.loc[work["is_legal"] & work["band"].eq("high")]
    high_n = weighted_count(high_legal, player, ids)
    band_z = _band_scores(work, legal, player, "e_bowl", ids)
    high_reference = high_n.ge(RANK_HIGH)

    spells = (
        work.groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(balls=("is_legal", "sum"), conceded=("conceded", "sum"), e_bowl=("e_bowl", "mean"))
        .reset_index()
    )
    spells = spells.loc[spells["balls"].gt(0)].copy()
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
        work.loc[work["band"].eq("high")]
        .groupby(["match_id", "innings", player, "season", "match_date"], sort=False)
        .agg(balls=("is_legal", "sum"), conceded=("conceded", "sum"))
        .reset_index()
    )
    high_spells = high_spells.loc[high_spells["balls"].ge(6)].copy()
    scale = float(spells.loc[spells[player].isin(ids[reference]) & spells["balls"].ge(6), "economy"].std(ddof=0))
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    if high_spells.empty:
        clutch = zscore(pd.Series(0.0, index=ids), high_reference)
    else:
        high_spells["clutch"] = clutch_gap(6 * high_spells["conceded"] / high_spells["balls"], high_spells[player].map(economy), False, scale)
        clutch_mean = high_spells.groupby(player)["clutch"].mean()
        clutch_n = high_spells.groupby(player)["clutch"].count()
        clutch = component_frame(shrink(clutch_mean, clutch_n, 0.0, 5), ids, high_reference)

    form_score, form_balls = recent_form(spells, player, "conceded", "balls", 6.0, False)
    form_component = _form_component(form_score, form_balls, ids, reference)
    qualified = spells.loc[spells["balls"].ge(6)].copy()
    match_values = qualified.groupby([player, "match_id"], sort=False)["e_bowl"].mean().reset_index()
    consistency = consistency_score(match_values, player, "e_bowl", ids, reference)

    composite = _composite({
        "baseline": base,
        "zero": band_z["zero"],
        "medium": band_z["medium"],
        "high": band_z["high"],
        "peers": peer,
        "form": form_component,
        "consistency": consistency,
    })
    ranked = n_eff.ge(REFERENCE_BALLS) & high_n.ge(RANK_HIGH)
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
        "form": form_component.to_numpy(),
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


def sanity_report(work: pd.DataFrame, legal: pd.DataFrame) -> dict:
    """Fail if a corrected rule has slipped."""
    one = legal.loc[legal["season"].eq(int(legal["season"].max())), ["striker_id", "season"]].copy()
    one["value"] = 1.0
    ids = pd.Index(one["striker_id"].unique())
    rate = career_rate(one, ids, "striker_id", "value")
    if rate.isna().any() or not np.allclose(rate.to_numpy(dtype=float), 1.0):
        raise AssertionError("a one-season rate of 1 was pulled below 1")
    if "clutch" in COMPONENT_WEIGHTS:
        raise AssertionError("clutch is still inside the composite")
    if abs(sum(COMPONENT_WEIGHTS.values()) - 1.0) > 1e-12:
        raise AssertionError("component weights do not sum to 1")
    below_strike = float(clutch_gap(pd.Series([100.0]), pd.Series([150.0]), True, 40.0).iloc[0])
    below_economy = float(clutch_gap(pd.Series([10.0]), pd.Series([8.0]), False, 2.0).iloc[0])
    if below_strike >= 0 or below_economy >= 0:
        raise AssertionError("a passage below the player's own rate scored as positive clutch")
    high = legal.loc[legal["band"].eq("high")]
    chase_share = float(high["innings"].eq(2).mean()) if len(high) else 1.0
    if chase_share >= 0.70:
        raise AssertionError(f"high band is still {chase_share:.1%} chases")
    league_first = high["innings"].eq(1) & high["knock_out"].fillna(0).astype(int).eq(0) & ~high["stage"].eq("Final") & ~high["is_reduced"].fillna(False).astype(bool)
    if not bool(league_first.any()):
        raise AssertionError("a league first innings cannot be high pressure")
    split = pd.crosstab(legal["pressure_points"], legal["band"])
    if bool((split.gt(0).sum(axis=1) > 1).any()):
        raise AssertionError("a pressure score falls in two bands")
    if float(legal.loc[legal["band"].eq("high"), "pressure_points"].min()) < 5:
        raise AssertionError("high band includes a score below 5")
    medium_points = legal.loc[legal["band"].eq("medium"), "pressure_points"]
    if float(medium_points.min()) < 3 or float(medium_points.max()) > 4:
        raise AssertionError("medium band is not scores 3 or 4")
    if float(legal.loc[legal["band"].eq("zero"), "pressure_points"].max()) > 2:
        raise AssertionError("zero band includes a score above 2")
    top_share = float(high["batting_order"].le(3).mean()) if len(high) else 0.0
    tail_share = float(high["batting_order"].ge(7).mean()) if len(high) else 1.0
    if top_share < 0.10:
        raise AssertionError(f"top order faces only {top_share:.1%} of high-pressure balls")
    if tail_share > 0.55:
        raise AssertionError(f"the tail faces {tail_share:.1%} of high-pressure balls")
    wide_residual = float(work.loc[~work["is_legal"], "e_bowl"].mean())
    if abs(wide_residual) >= 0.05:
        raise AssertionError(f"wide residual is {wide_residual}")
    conceded = float(work["conceded"].sum())
    batter_runs = float(work.loc[work["is_legal"], "bat_runs"].sum())
    if conceded <= batter_runs:
        raise AssertionError("charging wides did not raise bowler concession")
    bat_means = legal.groupby("ladder")["e_bat"].mean()
    bowl_means = work.groupby("ladder")["e_bowl"].mean()
    if float(bat_means.abs().max()) >= 0.25 or float(bowl_means.abs().max()) >= 0.25:
        raise AssertionError(f"residuals are not near zero: bat {bat_means.to_dict()} bowl {bowl_means.to_dict()}")
    return {
        "career_rate_of_ones": float(rate.mean()),
        "high_chase_share": chase_share,
        "high_first_innings": int((high["innings"].eq(1)).sum()),
        "league_first_innings_high": int(league_first.sum()),
        "high_top_order_share": top_share,
        "high_tail_share": tail_share,
        "wide_residual": wide_residual,
        "weight_sum": float(sum(COMPONENT_WEIGHTS.values())),
        "batter_residual": {str(key): float(value) for key, value in bat_means.items()},
        "bowler_residual": {str(key): float(value) for key, value in bowl_means.items()},
        "conceded": conceded,
        "legal_batter_runs": batter_runs,
    }
