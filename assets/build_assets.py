"""Draw the README graphics as SVG. Numbers come from the published ranking tables and the shock timeline.

Run from the repo root: python assets/build_assets.py
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
READOUT = ROOT / "research_readout"

NAVY = "#1b2437"
PAPER = "#f6f3ec"
CARD = "#fffdf8"
LINE = "#ddd6c8"
INK = "#1c1915"
MUTED = "#5e584f"
ACCENT = "#0f6e56"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"


def svg(width: int, height: int, body: str, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(label)}">\n{body}\n</svg>\n'
    )


def hero() -> str:
    t = pd.read_csv(READOUT / "06_shock" / "shock_innings_timeline.csv")
    w, h = 1280, 380
    x0, x1 = 64, 1216
    y_top, y_bot = 258, 340
    lo, hi = 1.5, 8.6
    pts = []
    for n, p in zip(t["legal_ball_n"], t["pressure_bat"]):
        x = x0 + (n - 1) / 119 * (x1 - x0)
        y = y_bot - (p - lo) / (hi - lo) * (y_bot - y_top)
        pts.append((x, y))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{x0},{y_bot} " + line + f" {x1},{y_bot}"
    marks = []
    for n in t.loc[t["is_wicket"].eq(1), "legal_ball_n"]:
        x = x0 + (n - 1) / 119 * (x1 - x0)
        y = pts[int(n) - 1][1]
        marks.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y_bot}" stroke="#f4e4ea" stroke-opacity="0.35" stroke-width="1"/>')
        marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{NAVY}" stroke="#f4a3b5" stroke-width="2"/>')
    body = f"""
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#232d47"/>
    <stop offset="1" stop-color="{NAVY}"/>
  </linearGradient>
  <linearGradient id="glow" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2fb892" stop-opacity="0.38"/>
    <stop offset="1" stop-color="#2fb892" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="22" fill="url(#bg)"/>
<text x="64" y="78" font-family="{SANS}" font-size="14" letter-spacing="4.2" fill="#9fb3c8">SUPERR  ·  SELECTOR SEASON 2</text>
<text x="62" y="160" font-family="{SERIF}" font-size="68" font-weight="600" fill="#f7f1e8">Who holds their nerve</text>
<text x="64" y="204" font-family="{SANS}" font-size="21" fill="#c9d3df">Every legal T20 ball, scored against what that ball usually yields.</text>
<text x="64" y="234" font-family="{SANS}" font-size="21" fill="#c9d3df">Pressure decides which of them count the most.</text>
<polygon points="{area}" fill="url(#glow)"/>
<polyline points="{line}" fill="none" stroke="#5be0b8" stroke-width="2.4" stroke-linejoin="round"/>
{"".join(marks)}
<text x="64" y="366" font-family="{SANS}" font-size="12.5" fill="#8fa3b8">Batter pressure, ball by ball. IPL 2025 final, Punjab Kings chasing 191. Rings are the seven wickets.</text>
"""
    return svg(w, h, body, "Who holds their nerve. Batter pressure through the IPL 2025 final chase.")


def kpis() -> str:
    tiles = [
        ("192,445", "legal balls rated"),
        ("867", "matches, Jan 2022 to Nov 2026"),
        ("888 + 647", "batters and bowlers seen"),
        ("141 + 143", "batters and bowlers ranked"),
        ("7", "pieces in every score"),
    ]
    w, h = 1280, 150
    tw, gap = 232, 25
    left = (w - (5 * tw + 4 * gap)) / 2
    parts = [f'<rect width="{w}" height="{h}" fill="{PAPER}" rx="18"/>']
    for i, (big, small) in enumerate(tiles):
        x = left + i * (tw + gap)
        parts.append(f'<rect x="{x + 0.5}" y="14.5" width="{tw}" height="{h - 29}" rx="16" fill="{CARD}" stroke="{LINE}"/>')
        parts.append(f'<rect x="{x + 22}" y="36" width="26" height="4" rx="2" fill="{ACCENT}"/>')
        parts.append(f'<text x="{x + 22}" y="86" font-family="{SERIF}" font-size="38" font-weight="600" fill="{INK}">{escape(big)}</text>')
        parts.append(f'<text x="{x + 22}" y="114" font-family="{SANS}" font-size="14" fill="{MUTED}">{escape(small)}</text>')
    return svg(w, h, "\n".join(parts), "Dataset at a glance")


def weights() -> str:
    pieces = [
        ("Baseline", 0.20, "#4472c4", "#ffffff", ["career rate against", "the phases he plays"]),
        ("Quiet", 0.10, "#a5a5a5", INK, ["the easy half", "of balls"]),
        ("Squeeze", 0.15, "#ffc000", INK, ["the game starts", "to tighten"]),
        ("High pressure", 0.20, "#c00000", "#ffffff", ["the tightest", "fifth of balls"]),
        ("Clutch", 0.15, "#7030a0", "#ffffff", ["beats his own rate", "in a hard spell"]),
        ("Same innings", 0.10, "#70ad47", INK, ["against the others", "in the same match"]),
        ("Consistency", 0.10, "#264478", "#ffffff", ["a narrow spread", "match to match"]),
    ]
    w, h = 1280, 190
    parts = [f'<rect width="{w}" height="{h}" fill="{PAPER}" rx="18"/>']
    parts.append(f'<text x="28" y="40" font-family="{SERIF}" font-size="24" font-weight="600" fill="{INK}">One score, seven pieces</text>')
    parts.append(f'<text x="{w - 28}" y="40" text-anchor="end" font-family="{SANS}" font-size="13.5" fill="{MUTED}">Bar widths are the published weights. They sum to 1.00.</text>')
    x = 28
    total = w - 56
    gap = 4
    for name, weight, fill, ink, cap in pieces:
        width = weight * (total - gap * (len(pieces) - 1))
        parts.append(f'<rect x="{x:.1f}" y="58" width="{width:.1f}" height="64" rx="10" fill="{fill}"/>')
        parts.append(f'<text x="{x + 14:.1f}" y="84" font-family="{SANS}" font-size="15" font-weight="700" fill="{ink}">{escape(name)}</text>')
        parts.append(f'<text x="{x + 14:.1f}" y="109" font-family="{SERIF}" font-size="22" font-weight="600" fill="{ink}">{weight:.2f}</text>')
        for k, text in enumerate(cap):
            parts.append(f'<text x="{x + 2:.1f}" y="{146 + k * 17}" font-family="{SANS}" font-size="12.5" fill="{MUTED}">{escape(text)}</text>')
        x += width + gap
    return svg(w, h, "\n".join(parts), "The seven pieces of the score and their weights")


def podium() -> str:
    bat = pd.read_csv(READOUT / "07_rankings" / "top10_batters.csv").sort_values("rank")
    bowl = pd.read_csv(READOUT / "07_rankings" / "top10_bowlers.csv").sort_values("rank")
    w, h = 1280, 330
    parts = [f'<rect width="{w}" height="{h}" fill="{PAPER}" rx="18"/>']
    card_w = 616
    for k, (title, frame, vmax, tint, spread) in enumerate((
        ("Batters", bat, 1.7, "#1f4e79", float(bat["composite"].iloc[0] - bat["composite"].iloc[9])),
        ("Bowlers", bowl, 1.2, "#b5462f", float(bowl["composite"].iloc[0] - bowl["composite"].iloc[9])),
    )):
        x = 14 + k * (card_w + 20)
        parts.append(f'<rect x="{x + 0.5}" y="14.5" width="{card_w}" height="{h - 29}" rx="16" fill="{CARD}" stroke="{LINE}"/>')
        parts.append(f'<text x="{x + 26}" y="54" font-family="{SERIF}" font-size="26" font-weight="600" fill="{INK}">{title}</text>')
        parts.append(f'<text x="{x + card_w - 24}" y="52" text-anchor="end" font-family="{SANS}" font-size="13" fill="{MUTED}">1st to 10th is {spread:.2f} apart</text>')
        for i in range(3):
            row = frame.iloc[i]
            y = 86 + i * 62
            share = float(row["composite"]) / vmax
            parts.append(f'<circle cx="{x + 42}" cy="{y + 20}" r="17" fill="{tint}"/>')
            parts.append(f'<text x="{x + 42}" y="{y + 26}" text-anchor="middle" font-family="{SERIF}" font-size="18" font-weight="600" fill="#fff">{i + 1}</text>')
            parts.append(f'<text x="{x + 74}" y="{y + 16}" font-family="{SANS}" font-size="18" font-weight="600" fill="{INK}">{escape(str(row["player_name"]))}</text>')
            parts.append(f'<text x="{x + card_w - 28}" y="{y + 16}" text-anchor="end" font-family="{SERIF}" font-size="24" font-weight="600" fill="{INK}">{float(row["composite"]):.2f}</text>')
            bar_w = card_w - 74 - 28
            parts.append(f'<rect x="{x + 74}" y="{y + 28}" width="{bar_w}" height="8" rx="4" fill="#ece6d8"/>')
            parts.append(f'<rect x="{x + 74}" y="{y + 28}" width="{bar_w * share:.1f}" height="8" rx="4" fill="{tint}"/>')
    return svg(w, h, "\n".join(parts), "The top three batters and bowlers and their scores")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, make in (("hero.svg", hero), ("kpis.svg", kpis), ("weights.svg", weights), ("podium.svg", podium)):
        (OUT / name).write_text(make(), encoding="utf-8")
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
