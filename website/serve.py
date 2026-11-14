"""Local site for the method, the rankings, and one player's explanation.

Run website/build_data.py first, then: python website/serve.py
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "ratings.db"
STATIC = ROOT / "static"
MATCHES = ROOT.parent / "silver" / "matches.csv"
HOST = "127.0.0.1"
PORT = 8765

WEIGHTS = [
    ("baseline", "Baseline", 0.20),
    ("band_zero", "Zero pressure", 0.10),
    ("band_medium", "Medium pressure", 0.15),
    ("band_high", "High pressure", 0.20),
    ("clutch", "Clutch", 0.15),
    ("peers", "Peers", 0.10),
    ("form", "Form", 0.05),
    ("consistency", "Consistency", 0.05),
]
PRE = {
    "band_zero": "zero_rate",
    "band_medium": "medium_rate",
    "band_high": "high_rate",
    "peers": "peer_pre",
    "clutch": "clutch_pre",
    "form": "form_pre",
    "consistency": "consistency_pre",
}


def _ready(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: _ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_ready(item) for item in value]
    if hasattr(value, "item"):
        return _ready(value.item())
    return value


def _num(value, digits=3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "missing"
    return f"{float(value):.{digits}f}"


def _z(value, center, spread):
    if value is None or center is None or spread in (None, 0) or (isinstance(spread, float) and (math.isnan(spread) or spread == 0)):
        return None
    raw = (float(value) - float(center)) / float(spread)
    return max(-3.0, min(3.0, raw))


class Site:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.matches = {}
        if MATCHES.exists():
            with MATCHES.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    self.matches[int(row["match_id"])] = row
        self.batters = self._table("batters")
        self.bowlers = self._table("bowlers")
        self.batter_math = self._keyed("batter_math")
        self.bowler_math = self._keyed("bowler_math")
        self.batter_ranks = self._ranks(self.batters)
        self.bowler_ranks = self._ranks(self.bowlers)
        self.batter_role_ranks = self._role_ranks(self.batters)

    def _table(self, name: str) -> list[dict]:
        rows = [dict(row) for row in self.connection.execute(f"SELECT * FROM {name}")]
        for row in rows:
            row["ranked"] = bool(row["ranked"])
        return rows

    def _keyed(self, name: str) -> dict[int, dict]:
        return {int(row["player_id"]): dict(row) for row in self.connection.execute(f"SELECT * FROM {name}")}

    def _ranks(self, rows: list[dict]) -> dict[str, dict[int, int]]:
        ranked = [row for row in rows if row["ranked"]]
        ranks = {}
        for key, _, _ in WEIGHTS:
            def sort_key(row, key=key):
                value = row[key]
                if value is None:
                    value = -10**9
                return (-value, row["player_id"])
            ordered = sorted(ranked, key=sort_key)
            ranks[key] = {int(row["player_id"]): index for index, row in enumerate(ordered, start=1)}
        return ranks

    def _role_ranks(self, rows: list[dict]) -> dict[str, dict[int, int]]:
        ranks = {}
        for key, _, _ in WEIGHTS:
            ranks[key] = {}
            for role in {row["role"] for row in rows}:
                group = [row for row in rows if row["ranked"] and row["role"] == role]

                def sort_key(row, key=key):
                    value = row[key]
                    if value is None:
                        value = -10**9
                    return (-value, row["player_id"])

                ordered = sorted(group, key=sort_key)
                for index, row in enumerate(ordered, start=1):
                    ranks[key][int(row["player_id"])] = index
        return ranks

    def listing(self, skill: str, query: dict) -> dict:
        rows = self.batters if skill == "batters" else self.bowlers
        text = (query.get("q") or [""])[0].strip().lower()
        role = (query.get("role") or [""])[0]
        ranked_only = (query.get("ranked") or ["1"])[0] != "0"
        sort = (query.get("sort") or ["rank"])[0]
        direction = (query.get("dir") or ["asc"])[0]
        if ranked_only:
            rows = [row for row in rows if row["ranked"]]
        if role:
            rows = [row for row in rows if row["role"] == role]
        if text:
            rows = [row for row in rows if text in str(row["player_name"]).lower()]
        def key(row):
            value = row.get(sort)
            missing = value is None or (isinstance(value, float) and math.isnan(value))
            if sort == "rank":
                return (0 if row["ranked"] else 1, value if value is not None else 10**9, row["player_name"])
            if missing:
                return (1, 0, row["player_name"])
            return (0, value, row["player_name"])
        rows = sorted(rows, key=key, reverse=direction == "desc" and sort != "rank")
        if sort == "rank" and direction == "desc":
            rows = list(reversed(rows))
        roles = sorted({row["role"] for row in (self.batters if skill == "batters" else self.bowlers)})
        return {"rows": rows, "count": len(rows), "roles": roles}

    def _rows(self, sql: str, player_id: int) -> list[dict]:
        return [dict(row) for row in self.connection.execute(sql, (player_id,))]

    def player(self, skill: str, player_id: int) -> dict | None:
        table = self.batters if skill == "batters" else self.bowlers
        row = next((item for item in table if int(item["player_id"]) == player_id), None)
        if row is None:
            return None
        math_row = (self.batter_math if skill == "batters" else self.bowler_math)[player_id]
        rank_table = self.batter_ranks if skill == "batters" else self.bowler_ranks
        role_table = self.batter_role_ranks if skill == "batters" else None
        parts = []
        for key, label, weight in WEIGHTS:
            z = row[key]
            parts.append({
                "key": key,
                "label": label,
                "weight": weight,
                "z": z,
                "contribution": None if z is None else weight * z,
                "rank": rank_table[key].get(player_id),
                "role_rank": None if role_table is None else role_table[key].get(player_id),
                "detail": self._detail(skill, key, row, math_row),
            })
        identity = "striker_id" if skill == "batters" else "bowler_id"
        return {
            "player": row,
            "parts": parts,
            "contribution_sum": sum(part["contribution"] or 0 for part in parts),
            "phases": self._rows(f"SELECT * FROM {skill[:-1]}_phases WHERE {identity} = ? ORDER BY balls DESC", player_id),
            "spells": self._rows(f"SELECT * FROM {skill[:-1]}_spells WHERE {identity} = ? ORDER BY match_date, match_id, innings", player_id),
            "clutch": self._rows(f"SELECT * FROM {skill[:-1]}_clutch WHERE {identity} = ? ORDER BY match_date, match_id, innings", player_id),
            "form": self._rows(f"SELECT * FROM {skill[:-1]}_form WHERE {identity} = ? ORDER BY match_date, match_id", player_id),
            "math": math_row,
        }

    def balls(self, skill: str, player_id: int, query: dict) -> dict:
        column = "striker_id" if skill == "batters" else "bowler_id"
        band_column = "band" if skill == "batters" else "band_bowl"
        clauses = [f"{column} = ?"]
        values: list = [player_id]
        phase = (query.get("phase") or [""])[0]
        band = (query.get("band") or [""])[0]
        if phase:
            clauses.append("phase = ?")
            values.append(phase)
        if band:
            clauses.append(f"{band_column} = ?")
            values.append(band)
        where = " AND ".join(clauses)
        total = self.connection.execute(f"SELECT COUNT(*) FROM balls WHERE {where}", values).fetchone()[0]
        limit = min(int((query.get("limit") or ["40"])[0]), 200)
        offset = max(int((query.get("offset") or ["0"])[0]), 0)
        rows = [
            dict(row) for row in self.connection.execute(
                f"SELECT * FROM balls WHERE {where} ORDER BY match_date, match_id, innings, n LIMIT ? OFFSET ?",
                [*values, limit, offset],
            )
        ]
        return {"rows": rows, "total": total, "limit": limit, "offset": offset}

    def innings_options(self, skill: str, player_id: int) -> list[dict]:
        column = "striker_id" if skill == "batters" else "bowler_id"
        figure = "SUM(bat_runs)" if skill == "batters" else "SUM(bowler_wicket)"
        rows = self.connection.execute(
            f"""
            SELECT match_id, innings, MIN(match_date) AS match_date, MIN(comp_name) AS comp_name,
                   MIN(stage) AS stage, COUNT(*) AS balls, SUM(bat_runs) AS runs,
                   SUM(bowler_wicket) AS wickets, {figure} AS figure
            FROM balls WHERE {column} = ?
            GROUP BY match_id, innings
            ORDER BY figure DESC, match_date DESC
            """,
            (player_id,),
        )
        return [dict(row) for row in rows]

    def innings(self, skill: str, player_id: int, match_id: int, innings: int) -> dict:
        rows = [
            dict(row) for row in self.connection.execute(
                """
                SELECT n, phase, striker_id, striker_name, bowler_id, bowler_name, bat_runs, charged_runs,
                       striker_out, bowler_wicket, wickets_before
                FROM balls WHERE match_id = ? AND innings = ? ORDER BY n
                """,
                (match_id, innings),
            )
        ]
        label = self.connection.execute(
            "SELECT comp_name, stage, match_date FROM balls WHERE match_id = ? LIMIT 1",
            (match_id,),
        ).fetchone()
        match = self.matches.get(match_id, {})
        column = "striker_id" if skill == "batters" else "bowler_id"
        own = [row for row in rows if row[column] == player_id]
        return {
            "match_id": match_id,
            "innings": innings,
            "date": match.get("match_date") or (label["match_date"] if label else None),
            "competition": label["comp_name"] if label else None,
            "home": match.get("home_team"),
            "away": match.get("away_team"),
            "stage": match.get("stage") or (label["stage"] if label else None),
            "result": match.get("result"),
            "balls": len(rows),
            "runs": sum(row["bat_runs"] or 0 for row in rows),
            "wickets": sum(int(row["striker_out"] or 0) for row in rows),
            "player_balls": len(own),
            "player_runs": sum(row["bat_runs"] or 0 for row in own),
            "player_wickets": sum(int(row["bowler_wicket"] or 0) for row in own),
            "player_charged": sum(row["charged_runs"] or 0 for row in own),
            "rows": rows,
        }

    def _detail(self, skill: str, key: str, player: dict, math_row: dict) -> list[str]:
        role = player["role"]
        group = role if skill == "batters" else "all bowlers"
        if key == "baseline" and skill == "batters":
            sr_z = _z(math_row["sr_gap"], math_row["sr_gap_center"], math_row["sr_gap_spread"])
            avg_z = _z(math_row["average_gap"], math_row["average_gap_center"], math_row["average_gap_spread"])
            return [
                f"Legal balls { _num(math_row['balls'], 0) }, runs { _num(math_row['runs'], 0) }, striker dismissals { _num(math_row['dismissals'], 0) }.",
                f"Strike rate { _num(math_row['strike_rate'], 2) }. Average { _num(math_row['average'], 2) }.",
                f"Phase-mix expectation: strike rate { _num(math_row['expected_sr'], 2) }, average { _num(math_row['expected_average'], 2) }.",
                f"Strike rate is shrunk toward that expectation with strength 120 balls, giving { _num(math_row['shrunk_sr'], 2) }. The gap is { _num(math_row['sr_gap'], 3) }.",
                f"Average is shrunk with strength 4 dismissals, giving { _num(math_row['shrunk_average'], 2) }. The gap is { _num(math_row['average_gap'], 3) }.",
                f"Inside {group}, the strike-rate gap has mean { _num(math_row['sr_gap_center']) } and spread { _num(math_row['sr_gap_spread']) }, so its z-score is { _num(sr_z) }.",
                f"The average gap has mean { _num(math_row['average_gap_center']) } and spread { _num(math_row['average_gap_spread']) }, so its z-score is { _num(avg_z) }.",
                "Baseline is half of those two z-scores. The reference players are those in the role with at least 30 decay-weighted legal balls. Each z-score stops at 3.",
            ]
        if key == "baseline":
            econ_z = _z(math_row["economy_gap"], math_row["economy_gap_center"], math_row["economy_gap_spread"])
            balls_z = _z(math_row["balls_gap"], math_row["balls_gap_center"], math_row["balls_gap_spread"])
            return [
                f"Legal balls { _num(math_row['legal_balls'], 0) }, wickets { _num(math_row['wickets'], 0) }, conceded runs { _num(math_row['conceded'], 0) }.",
                f"Economy { _num(math_row['economy'], 2) }. Balls per wicket { _num(math_row['balls_per_wicket'], 2) }.",
                f"Phase and arm expectation: economy { _num(math_row['expected_economy'], 2) }, balls per wicket { _num(math_row['expected_balls'], 2) }.",
                f"Economy is shrunk toward that expectation with strength 120 balls. Expected minus shrunk is { _num(math_row['economy_gap'], 3) }, because a lower economy is better.",
                f"Balls per wicket are shrunk with strength 4 wickets. Expected minus shrunk is { _num(math_row['balls_gap'], 3) }.",
                f"Across bowlers with at least 30 decay-weighted balls, the economy gap has mean { _num(math_row['economy_gap_center']) } and spread { _num(math_row['economy_gap_spread']) }, so its z-score is { _num(econ_z) }.",
                f"The balls-per-wicket gap has mean { _num(math_row['balls_gap_center']) } and spread { _num(math_row['balls_gap_spread']) }, so its z-score is { _num(balls_z) }.",
                "Baseline is half of those two z-scores.",
            ]
        pre_key = PRE[key]
        pre = math_row[pre_key]
        center = math_row[f"{pre_key}_center"]
        spread = math_row[f"{pre_key}_spread"]
        rebuilt = _z(pre, center, spread)
        shared = f"The value that enters the z-score is { _num(pre) }. Inside {group} the reference mean is { _num(center) } and the spread is { _num(spread) }, so the z-score is { _num(rebuilt) }."
        if key == "band_high":
            balls = math_row["high_balls"]
            return [
                f"Decay-weighted high-band balls: { _num(balls, 1) }. A player needs 30 of these, and 120 decay-weighted legal balls, to be ranked.",
                "The band rate is the decay-weighted mean of the ball value on high-band balls only. A season with no high-band balls is left out. That rate is then shrunk toward 0 with strength 30.",
                shared,
            ]
        if key in ("band_zero", "band_medium"):
            balls_key = "zero_balls" if key == "band_zero" else "medium_balls"
            return [
                f"Decay-weighted balls in this band: { _num(math_row[balls_key], 1) }.",
                "The band rate is the decay-weighted mean of the ball value in the band, shrunk toward 0 with strength 30. Missed seasons are not filled with zero.",
                shared,
            ]
        if key == "peers":
            return [
                f"Innings of at least 6 legal balls: { _num(math_row['peer_n'], 0) }.",
                "Each innings is the average of the teammate z-score and the opposition z-score. Both are capped at 3. The innings scores are averaged, then shrunk toward 0 with strength 5 innings.",
                shared,
                "The innings rows are below. stood out means the teammate z-score was above 0.5 and the innings also beat the player's own career rate.",
            ]
        if key == "clutch":
            return [
                f"High-band spells of at least 6 balls with a teammate z-score: { _num(math_row['clutch_n'], 0) }. The scale of a spell against the player's own rate is { _num(math_row['clutch_scale'], 2) }.",
                "If the spell is worse than the player's own rate, the spell score is that negative gap. If it is better, the score is the gap times the positive part of the teammate z-score. A negative teammate gap adds nothing.",
                "Those spell scores are averaged and shrunk toward 0 with strength 5, then z-scored.",
                shared,
            ]
        if key == "form":
            return [
                f"Qualified innings: { _num(math_row['form_n'], 0) }.",
                "Each innings scores the share of the previous innings, at most eight, that beat the full-career rate, minus 0.5. The first innings scores 0. The career bar includes later innings.",
                "Those innings scores are decay-weighted by season. A season with no innings is left out. The result is shrunk toward 0 with strength 8 innings.",
                shared,
            ]
        return [
            f"Matches with a qualified innings: { _num(math_row['consistency_matches'], 0) }.",
            f"Population spread of the match-level ball value: { _num(math_row['consistency_spread']) }. The typical spread in the comparison group is { _num(math_row['consistency_typical']) }.",
            f"The spread is shrunk toward that typical spread with strength 8 matches, giving { _num(math_row['consistency_shrunk']) }. The value that enters the z-score is the negative of that, { _num(math_row['consistency_pre']) }, so a narrower spread scores higher.",
            shared,
        ]


SITE: Site | None = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._api(parsed)
            return
        relative = parsed.path.lstrip("/") or "index.html"
        file_path = (STATIC / relative).resolve()
        if not str(file_path).startswith(str(STATIC.resolve())) or not file_path.is_file():
            self.send_error(404)
            return
        kind = "text/html; charset=utf-8"
        if file_path.suffix == ".css":
            kind = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            kind = "text/javascript; charset=utf-8"
        payload = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _api(self, parsed):
        if SITE is None:
            self._json(503, {"error": "ratings database is not loaded"})
            return
        query = parse_qs(parsed.query)
        parts = [part for part in parsed.path.split("/") if part]
        try:
            if parts[:2] == ["api", "batters"] and len(parts) == 2:
                self._json(200, SITE.listing("batters", query))
            elif parts[:2] == ["api", "bowlers"] and len(parts) == 2:
                self._json(200, SITE.listing("bowlers", query))
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "player" and parts[2] in ("batters", "bowlers"):
                payload = SITE.player(parts[2], int(parts[3]))
                self._json(200 if payload else 404, payload or {"error": "player not found"})
            elif len(parts) == 5 and parts[0] == "api" and parts[1] == "player" and parts[4] == "balls":
                self._json(200, SITE.balls(parts[2], int(parts[3]), query))
            elif len(parts) == 5 and parts[0] == "api" and parts[1] == "player" and parts[4] == "innings":
                self._json(200, {"innings": SITE.innings_options(parts[2], int(parts[3]))})
            elif len(parts) == 7 and parts[0] == "api" and parts[1] == "player" and parts[4] == "innings":
                self._json(200, SITE.innings(parts[2], int(parts[3]), int(parts[5]), int(parts[6])))
            else:
                self._json(404, {"error": "unknown request"})
        except (ValueError, KeyError, sqlite3.Error) as error:
            self._json(400, {"error": str(error)})

    def _json(self, status: int, payload: dict):
        body = json.dumps(_ready(payload)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    global SITE
    if not DB.exists():
        raise SystemExit("Run python website/build_data.py before starting the site.")
    SITE = Site(DB)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"SupeRR ratings site at {url}")
    webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
