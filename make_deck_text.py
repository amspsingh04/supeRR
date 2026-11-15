"""Join the deck exports into exports/DECK_FOR_CLAUDE.txt, one paste for the slide writer.

Run after website/build_data.py, from the repository root: python make_deck_text.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / "exports"
MATCHES = ROOT / "silver" / "matches.csv"

SMALL = [
    "00_caption_notes.csv", "01_cleaning_funnel.csv", "02_extras_label_counts.csv", "03_dismissal_type_counts.csv",
    "04_comp_group_counts.csv", "05_reduced_innings.csv", "08_band_cutoffs.csv", "09_high_band_composition.csv",
    "12_fit_elo_bounds.csv", "14_calibration_bins.csv", "14b_calibration_wicket_bins.csv", "15_component_weights.csv",
    "17_role_composition_with_split.csv", "18_role_composition_without_split.csv", "19_reference_population_sizes.csv",
    "21_component_breakdown_top10.csv", "22_known_players_scatter.csv",
]


def bins(series: pd.Series, n: int = 20) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    rows = ["bin_left,bin_right,count"]
    for interval, count in values.groupby(pd.cut(values, n), observed=False).size().items():
        rows.append(f"{interval.left:.4f},{interval.right:.4f},{int(count)}")
    return "\n".join(rows)


def main() -> None:
    parts: list[str] = []

    def add(title: str, text: str) -> None:
        parts.extend([f"===== {title} =====", text.rstrip(), ""])

    for name in SMALL:
        add(name, (FOLDER / name).read_text(encoding="utf-8"))

    difficulty = pd.read_csv(FOLDER / "06_ball_difficulty.csv")
    add("06_ball_difficulty_BINS_batter.csv (20 bins of a 50k sample, not every ball)", bins(difficulty.loc[difficulty.role.eq("batter"), "ball_difficulty"]))
    add("06_ball_difficulty_BINS_bowler.csv", bins(difficulty.loc[difficulty.role.eq("bowler"), "ball_difficulty"]))
    pressure = pd.read_csv(FOLDER / "07_pressure_scores.csv")
    add("07_pressure_bat_BINS.csv", bins(pressure.pressure_bat, 24))
    add("07_pressure_bowl_pace_BINS.csv", bins(pressure.loc[pressure.pace_or_spin.eq("Pace"), "pressure_bowl"], 24))
    add("07_pressure_bowl_spin_BINS.csv", bins(pressure.loc[pressure.pace_or_spin.eq("Spin"), "pressure_bowl"], 24))
    ratings = pd.read_csv(FOLDER / "11_final_ratings.csv")
    add("11_final_ratings_BINS_batter.csv", bins(ratings.loc[ratings.role.eq("batter"), "final_rating"]))
    add("11_final_ratings_BINS_bowler.csv", bins(ratings.loc[ratings.role.eq("bowler"), "final_rating"]))
    add("11_final_ratings_BOUNDS.csv", "role,min,max,std,n\n" + "\n".join(
        f"{role},{group.final_rating.min():.4f},{group.final_rating.max():.4f},{group.final_rating.std(ddof=0):.4f},{len(group)}"
        for role, group in ratings.groupby("role")
    ))

    add("10_sample_innings_timeline.csv", (FOLDER / "10_sample_innings_timeline.csv").read_text(encoding="utf-8"))
    trajectory = pd.read_csv(FOLDER / "13_player_trajectory.csv")
    thin = pd.concat([trajectory.iloc[::10], trajectory.groupby("match_id", sort=False).tail(1)])
    thin = thin.drop_duplicates("ball_seq_number").sort_values("ball_seq_number")
    notes = pd.read_csv(FOLDER / "00_caption_notes.csv").set_index("item")["value"]
    player = notes["trajectory_player"]
    add(f"13_player_trajectory_EVERY_10TH_BALL_PLUS_MATCH_ENDS.csv {player}", thin.to_csv(index=False))
    for name in ["16_high_clutch_scatter.csv", "20_composite_scores.csv", "23_ablation_ranks.csv"]:
        add(name, (FOLDER / name).read_text(encoding="utf-8"))

    scatter = pd.read_csv(FOLDER / "16_high_clutch_scatter.csv")
    corr = {
        role: (group["high_zscore"].corr(group["clutch_zscore"]), len(group))
        for role, group in scatter.dropna(subset=["high_zscore", "clutch_zscore"]).groupby("role")
    }
    matches = pd.read_csv(MATCHES).set_index("match_id")

    def fixture(match_id) -> str:
        row = matches.loc[int(match_id)]
        return f"{row['home_team']} vs {row['away_team']}"

    note = "\n".join([
        "HOW TO READ THIS PASTE",
        "Files 06, 07 and 11 are histogram bins (bin_left, bin_right, count), not the raw 50,000 rows. Draw the bar from the midpoint of each bin with height = count.",
        f"File 13 is every 10th ball of {player}'s batting rating, plus the last ball of each match. ball_seq_number is the career ball.",
        "Band cutoffs are the p50 and p80 in file 08. They are the cuts the model used.",
        f"High band vs clutch correlation: batters {corr['batter'][0]:.3f} (n={corr['batter'][1]}), bowlers {corr['bowler'][0]:.3f} (n={corr['bowler'][1]}).",
        f"Sample innings: {notes['sample_competition']} {str(notes['sample_stage']).lower()}, {notes['sample_date']}, {notes['sample_home']} vs {notes['sample_away']}, innings {notes['sample_innings']}.",
        f"{player.split()[-1]} rating rise: {notes['trajectory_up_date']} {fixture(notes['trajectory_up'])}, {float(notes['trajectory_up_runs']):.0f} runs, match_id {notes['trajectory_up']}.",
        f"{player.split()[-1]} rating fall: {notes['trajectory_down_date']} {fixture(notes['trajectory_down'])}, {float(notes['trajectory_down_runs']):.0f} runs, match_id {notes['trajectory_down']}.",
        "Acceptance lines for Elo: min 600, max 2800, std 250.",
        "Component bars in file 21 are already weight times z-score, so they sum to the composite.",
        "Extras: extras1_runs is the run amount of the extra named in extras_type. A wide, a no-ball, or an other-type extra is not a legal ball. A bowler is charged every run off a wide and the one run of a no-ball or other-type extra, plus bat runs.",
        "",
    ])
    text = note + "\n" + "\n".join(parts)
    (FOLDER / "DECK_FOR_CLAUDE.txt").write_text(text, encoding="utf-8")
    print("wrote", FOLDER / "DECK_FOR_CLAUDE.txt", "lines", text.count("\n"))


if __name__ == "__main__":
    main()
