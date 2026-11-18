"""Jos Buttler's career on one chart: innings path, the matches inside clutch and the high band, and the published score.

Reads the published ratings database. Does not refit the model.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_readout" / "10_charts" / "slide_buttler"
DB = ROOT / "website" / "data" / "ratings.db"
WEIGHTS = {
    "baseline": 0.20,
    "band_zero": 0.10,
    "band_medium": 0.15,
    "band_high": 0.20,
    "clutch": 0.15,
    "peers": 0.10,
    "consistency": 0.10,
}
DECAY = {year: 0.9 ** (2026 - year) for year in range(2022, 2027)}
NAMES = {
    "baseline": "Baseline",
    "band_zero": "Zero",
    "band_medium": "Medium",
    "band_high": "High",
    "clutch": "Clutch",
    "peers": "Peers",
    "consistency": "Consistency",
}
COLORS = {
    "baseline": "#4472c4",
    "band_zero": "#a5a5a5",
    "band_medium": "#ffc000",
    "band_high": "#c00000",
    "clutch": "#7030a0",
    "peers": "#70ad47",
    "consistency": "#264478",
}


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    con = sqlite3.connect(DB)
    balls = pd.read_sql(
        "SELECT match_id, match_date, season, comp_name, stage, innings, band, bat_runs, e_bat, ladder "
        "FROM balls WHERE striker_id = 813",
        con,
    )
    clutch = pd.read_sql("SELECT * FROM batter_clutch WHERE striker_id = 813", con)
    batter = pd.read_sql("SELECT * FROM batters WHERE player_id = 813", con).iloc[0]
    math = pd.read_sql("SELECT * FROM batter_math WHERE player_id = 813", con).iloc[0]
    con.close()

    sides = pd.read_csv(
        ROOT / "silver" / "ball_by_ball.csv",
        usecols=["match_id", "innings", "batting_team_id", "bowling_team_id"],
    ).drop_duplicates(["match_id", "innings"])
    teams = pd.read_csv(ROOT / "silver" / "teams.csv").drop_duplicates("team_id").set_index("team_id")["team_name"]
    sides["batting"] = sides["batting_team_id"].map(teams)
    sides["bowling"] = sides["bowling_team_id"].map(teams)
    balls["match_date"] = pd.to_datetime(balls["match_date"])
    balls = balls.merge(sides[["match_id", "innings", "batting", "bowling"]], on=["match_id", "innings"], how="left")
    clutch["match_date"] = pd.to_datetime(clutch["match_date"])
    return balls, clutch, batter, math


def innings_table(balls: pd.DataFrame) -> pd.DataFrame:
    inn = (
        balls.groupby(["match_id", "innings", "match_date", "season", "ladder", "comp_name", "stage", "batting", "bowling"], sort=False)
        .agg(balls=("bat_runs", "size"), runs=("bat_runs", "sum"), e_bat=("e_bat", "sum"))
        .reset_index()
    )
    inn["sr"] = 100 * inn["runs"] / inn["balls"]
    high = (
        balls.loc[balls["band"].eq("high")]
        .groupby(["match_id", "innings"], sort=False)
        .agg(high_balls=("bat_runs", "size"), high_runs=("bat_runs", "sum"), high_e=("e_bat", "sum"))
        .reset_index()
    )
    inn = inn.merge(high, on=["match_id", "innings"], how="left")
    inn["high_balls"] = inn["high_balls"].fillna(0)
    inn["high_e"] = inn["high_e"].fillna(0.0)
    inn["high_e_decayed"] = inn["high_e"] * inn["season"].map(DECAY)
    return inn


def main() -> None:
    balls, clutch, batter, math = load()
    inn = innings_table(balls)
    qualified = inn.loc[inn["balls"].ge(6)].copy()

    marked = clutch.merge(
        inn,
        on=["match_id", "innings"],
        how="left",
        suffixes=("", "_inn"),
    )
    # The 2022 qualifier is the other high-band innings that moves the rate, and it is not a clutch spell.
    extra_id = (15187, 1)
    extra = inn.loc[inn["match_id"].eq(extra_id[0]) & inn["innings"].eq(extra_id[1])].iloc[0]

    contributions = [(name, float(batter[name]) * weight) for name, weight in WEIGHTS.items()]
    total = float(batter["composite"])

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
    })
    fig, (ax, axw) = plt.subplots(
        2, 1, figsize=(12.4, 8.2), gridspec_kw={"height_ratios": [1.45, 1.0]},
    )

    for ladder, color in (("IPL", "#1f4e79"), ("T20I", "#5b9bd5")):
        sub = qualified.loc[qualified["ladder"].eq(ladder)]
        ax.scatter(
            sub["match_date"], sub["sr"],
            s=18 + sub["balls"] * 1.1,
            color=color, alpha=0.55, linewidths=0, zorder=2,
            label=f"{ladder} innings, 6 or more balls",
        )

    career_sr = float(math["strike_rate"])
    expected_sr = float(math["expected_sr"])
    ax.axhline(career_sr, color="#1f4e79", lw=1.0, ls="--", label=f"Career strike rate {career_sr:.0f}")
    ax.axhline(expected_sr, color="#7f7f7f", lw=1.0, ls=":", label=f"Phase expectation {expected_sr:.0f}")

    def place(row) -> str:
        chase = "chase" if int(row["innings"]) == 2 else "1st inns"
        stage = str(row["stage"])
        short = {
            "Kolkata Knight Riders": "KKR",
            "New Zealand": "New Zealand",
            "Gujarat Titans": "Gujarat",
            "Royal Challengers Bengaluru": "RCB",
        }
        opponent = short.get(row["bowling"], row["bowling"])
        where = {"Final": "IPL final", "Qualifier": "Qualifier"}.get(stage, f"v {opponent}")
        return f"{where}, {chase}"

    def knock(runs, balls) -> str:
        return f"{int(runs)} off {int(balls)}"

    # Manual offsets so the two pairs of matches five days apart do not sit on each other.
    offsets = {
        15190: (14, -46),
        15187: (16, 18),
        25160: (12, 16),
        31250: (14, 18),
        50942: (-88, 16),
        50945: (-72, -36),
    }
    for _, row in marked.iterrows():
        ax.scatter(
            row["match_date"], row["sr"],
            s=90, facecolors="none", edgecolors="#7030a0", linewidths=1.8, zorder=4,
        )
        same = int(row["high_balls"]) == int(row["balls_inn"])
        detail = knock(row["runs_inn"], row["balls_inn"]) if same else (
            f"{knock(row['runs_inn'], row['balls_inn'])}, {int(row['high_balls'])} of them high"
        )
        ax.annotate(
            f"{place(row)}\n{detail}",
            xy=(row["match_date"], row["sr"]),
            xytext=offsets[int(row["match_id"])],
            textcoords="offset points",
            fontsize=7.5,
            color="#7030a0",
            ha="left",
            arrowprops={"arrowstyle": "-", "color": "#7030a0", "lw": 0.6},
            zorder=5,
        )
    ax.scatter(
        extra["match_date"], extra["sr"],
        s=90, facecolors="none", edgecolors="#c00000", linewidths=1.8, zorder=4,
        label="High-band innings, not a clutch spell",
    )
    ax.annotate(
        f"Qualifier, 1st inns\n{knock(extra['runs'], extra['balls'])}",
        xy=(extra["match_date"], extra["sr"]),
        xytext=offsets[15187],
        textcoords="offset points",
        fontsize=7.5,
        color="#c00000",
        ha="left",
        arrowprops={"arrowstyle": "-", "color": "#c00000", "lw": 0.6},
        zorder=5,
    )
    # A purple ring in the legend, drawn once.
    ax.scatter([], [], s=90, facecolors="none", edgecolors="#7030a0", linewidths=1.8, label="Clutch spell (5 in the career)")

    ax.set_ylim(-15, 360)
    ax.set_ylabel("Innings strike rate")
    ax.set_title("Jos Buttler, innings by innings")
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    ax.set_xlabel("")

    # Waterfall of the published contributions.
    labels = [NAMES[name] for name, _ in contributions] + ["Score"]
    values = [value for _, value in contributions] + [total]
    cumulative = 0.0
    xs = np.arange(len(values))
    for i, (name, value) in enumerate(contributions):
        color = COLORS[name]
        axw.bar(i, value, bottom=cumulative, color=color, width=0.72, zorder=2)
        end = cumulative + value
        axw.plot([i + 0.36, i + 1 - 0.36], [end, end], color="#b0b0b0", lw=0.8, zorder=1)
        ypos = end + (0.03 if value >= 0 else -0.055)
        axw.text(i, ypos, f"{value:+.2f}", ha="center", va="bottom" if value >= 0 else "top", fontsize=8, color=color)
        cumulative = end
    axw.bar(len(values) - 1, total, color="#1f4e79", width=0.72, zorder=2)
    axw.text(len(values) - 1, total + 0.03, f"{total:.2f}", ha="center", va="bottom", fontsize=8, color="#1f4e79")
    axw.axhline(0, color="black", lw=0.6)
    axw.set_xticks(xs, labels)
    axw.set_ylabel("Contribution to the score")
    axw.set_ylim(-0.18, 1.28)
    axw.set_title("How those innings land in the published 1.07")

    fig.foot_space = 0.11
    fig.text(
        0.01, 0.012,
        "Purple rings are the only five high-band spells with two teammates also on a long high-band passage. "
        "The red ring, the 2022 qualifier, is high-band ball value and is not one of those five.\n"
        "The strike rate on the line is the whole innings. Clutch uses the high-band balls in that innings. "
        "Source: website/data/ratings.db, player 813, tables balls, batter_clutch, batters, batter_math.",
        fontsize=7.5, color="#555555", ha="left", va="bottom",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "buttler_career.png", dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)

    rows = []
    for _, row in marked.sort_values("match_date").iterrows():
        rows.append({
            "match_date": row["match_date"].strftime("%Y-%m-%d"),
            "match_id": int(row["match_id"]),
            "role_in_score": "clutch spell",
            "competition": row["comp_name"],
            "stage": row["stage"],
            "batting": row["batting"],
            "bowling": row["bowling"],
            "innings": int(row["innings"]),
            "innings_runs": int(row["runs_inn"]),
            "innings_balls": int(row["balls_inn"]),
            "innings_sr": round(float(row["sr"]), 1),
            "high_balls": int(row["high_balls"]),
            "high_band_strike_rate": round(float(row["metric"]), 1),
            "clutch_spell_score": round(float(row["clutch"]), 3),
            "high_band_ball_value": round(float(row["high_e"]), 2),
            "high_band_ball_value_decayed": round(float(row["high_e_decayed"]), 2),
        })
    rows.append({
        "match_date": extra["match_date"].strftime("%Y-%m-%d"),
        "match_id": int(extra["match_id"]),
        "role_in_score": "high band only",
        "competition": extra["comp_name"],
        "stage": extra["stage"],
        "batting": extra["batting"],
        "bowling": extra["bowling"],
        "innings": int(extra["innings"]),
        "innings_runs": int(extra["runs"]),
        "innings_balls": int(extra["balls"]),
        "innings_sr": round(float(extra["sr"]), 1),
        "high_balls": int(extra["high_balls"]),
        "high_band_strike_rate": round(100 * float(extra["high_runs"]) / float(extra["high_balls"]), 1),
        "clutch_spell_score": None,
        "high_band_ball_value": round(float(extra["high_e"]), 2),
        "high_band_ball_value_decayed": round(float(extra["high_e_decayed"]), 2),
    })
    table = pd.DataFrame(rows).sort_values("match_date")
    table.to_csv(OUT / "buttler_matches_that_counted.csv", index=False)
    print(table.to_string(index=False))
    print("contributions", contributions, "total", round(total, 4))
    print("high e decayed sum", round(float(inn["high_e_decayed"].sum()), 2))
    print("wrote", OUT / "buttler_career.png")


if __name__ == "__main__":
    main()
