"""Run the ratings, write ratings/*.csv, the deck exports, and website/data/ratings.db."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

import player_ratings as ratings
DB = ROOT / "data" / "ratings.db"
RATINGS = ROOT.parent / "ratings"

BATTER_GAPS = ["sr_gap", "average_gap", "zero_rate", "medium_rate", "high_rate", "peer_pre", "clutch_pre", "consistency_pre"]
BOWLER_GAPS = ["economy_gap", "balls_gap", "zero_rate", "medium_rate", "high_rate", "peer_pre", "clutch_pre", "consistency_pre"]
BALL_COLUMNS = [
    "match_id", "match_date", "season", "comp_name", "stage", "innings", "n", "phase",
    "striker_id", "striker_name", "bowler_id", "bowler_name", "batting_order", "pace_or_spin",
    "bat_runs", "charged_runs", "striker_out", "bowler_wicket", "wickets_before", "rrr",
    "x_runs", "x_runs_bowl", "x_wicket", "e_bat", "e_bowl",
    "occasion", "competition", "ball_bat", "ball_bowl", "shock_bat", "shock_bowl",
    "delta_bat", "delta_bowl", "pressure_bat", "pressure_bowl", "band", "band_bowl", "ladder",
]


def _moments(math: pd.DataFrame, role: pd.Series, columns: list[str], pooled: bool = False) -> pd.DataFrame:
    """Mean and population spread of each pre-z value, inside the role group. With pooled, also across every player."""
    out = math.copy()
    out["role_group"] = role.reindex(out["player_id"]).to_numpy()
    reference = out["reference"].astype(bool)
    for column in columns:
        center = pd.Series(np.nan, index=out.index)
        spread = pd.Series(np.nan, index=out.index)
        for _, index in out.groupby("role_group", sort=False).groups.items():
            sample = out.loc[index].loc[reference.loc[index], column]
            center.loc[index] = float(sample.mean()) if len(sample) else np.nan
            spread.loc[index] = float(sample.std(ddof=0)) if len(sample) else np.nan
        out[f"{column}_center"] = center.to_numpy()
        out[f"{column}_spread"] = spread.to_numpy()
        if pooled:
            sample = out.loc[reference, column]
            out[f"{column}_pcenter"] = float(sample.mean())
            out[f"{column}_pspread"] = float(sample.std(ddof=0))
    out["role_blend"] = ratings.ROLE_BLEND if pooled else 1.0
    return out


def _blend_z(frame: pd.DataFrame, column: str) -> pd.Series:
    """The published z-score: the role part, plus the pooled part when there is one."""
    role_z = ((frame[column] - frame[f"{column}_center"]) / frame[f"{column}_spread"].replace(0, np.nan)).clip(-3, 3)
    if f"{column}_pcenter" not in frame.columns:
        return role_z
    pooled_z = ((frame[column] - frame[f"{column}_pcenter"]) / frame[f"{column}_pspread"].replace(0, np.nan)).clip(-3, 3)
    return frame["role_blend"] * role_z + (1 - frame["role_blend"]) * pooled_z


def _dates(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[column]):
            out[column] = out[column].dt.strftime("%Y-%m-%d")
    return out


def _check(table: pd.DataFrame, math: pd.DataFrame, left: str, right: str, label: str) -> None:
    keep = ["player_id", "role_blend"] + [column for column in math.columns if column.startswith(f"{left}_") or column == left]
    merged = table.merge(math[keep], on="player_id", how="left")
    gap = (_blend_z(merged, left) - merged[right]).abs()
    print(label, "max gap", round(float(gap.max()), 6))


def main() -> None:
    balls, _, _ = ratings.load()
    work, legal = ratings.add_situation(balls)
    legal = ratings.fit_elo(legal)
    batters = ratings.score_batters(legal)
    bowlers = ratings.score_bowlers(legal, work)
    RATINGS.mkdir(exist_ok=True)
    batters.to_csv(RATINGS / "batters.csv", index=False)
    bowlers.to_csv(RATINGS / "bowlers.csv", index=False)

    batter_trace = ratings.TRACES["batters"]
    bowler_trace = ratings.TRACES["bowlers"]
    batter_math = _moments(batter_trace["math"], batters.set_index("player_id")["role"], BATTER_GAPS, pooled=True)
    bowler_math = _moments(bowler_trace["math"], pd.Series("all", index=bowlers["player_id"]), BOWLER_GAPS)
    _check(batters, batter_math, "high_rate", "band_high", "batter high band")
    aligned = batter_math.merge(batters[["player_id", "baseline"]], on="player_id")
    base_gap = (0.5 * _blend_z(aligned, "sr_gap") + 0.5 * _blend_z(aligned, "average_gap") - aligned["baseline"]).abs()
    print("batter baseline max gap", round(float(base_gap.max()), 6))
    _check(bowlers, bowler_math, "high_rate", "band_high", "bowler high band")

    ball_columns = [column for column in BALL_COLUMNS if column in legal.columns]
    deliveries = legal[ball_columns].copy()
    deliveries["match_date"] = pd.to_datetime(deliveries["match_date"]).dt.strftime("%Y-%m-%d")
    for column in ("striker_out", "bowler_wicket"):
        if column in deliveries.columns:
            deliveries[column] = deliveries[column].astype(int)

    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    connection = sqlite3.connect(DB)
    batters.to_sql("batters", connection, index=False)
    bowlers.to_sql("bowlers", connection, index=False)
    batter_math.to_sql("batter_math", connection, index=False)
    bowler_math.to_sql("bowler_math", connection, index=False)
    _dates(batter_trace["spells"]).to_sql("batter_spells", connection, index=False)
    _dates(bowler_trace["spells"]).to_sql("bowler_spells", connection, index=False)
    _dates(batter_trace["clutch"]).to_sql("batter_clutch", connection, index=False)
    _dates(bowler_trace["clutch"]).to_sql("bowler_clutch", connection, index=False)
    batter_trace["phases"].to_sql("batter_phases", connection, index=False)
    bowler_trace["phases"].to_sql("bowler_phases", connection, index=False)
    deliveries.to_sql("balls", connection, index=False, chunksize=20000)
    connection.execute("CREATE INDEX balls_striker ON balls(striker_id)")
    connection.execute("CREATE INDEX balls_bowler ON balls(bowler_id)")
    connection.commit()
    connection.close()
    ratings.write_deck_exports(balls, work, legal, batters, bowlers)
    print("wrote", DB)
    print("ranked batters", int(batters["ranked"].sum()), "ranked bowlers", int(bowlers["ranked"].sum()))
    top = batters.loc[batters["ranked"]].nsmallest(5, "rank")[["rank", "player_name", "n_eff", "high_n_eff", "composite"]]
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
