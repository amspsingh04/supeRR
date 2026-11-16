"""Run the existing pipeline in memory and cache every frame the readout needs.

Nothing in the repository is written except research_readout/_cache.
The current model is imported from player_ratings.py as it stands.
The earlier eight-term model (with Form) is loaded read-only from git 29956ed for comparison.
"""

from __future__ import annotations

import copy
import os
import pickle
import subprocess
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "research_readout" / "_cache"
CACHE.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import player_ratings as pr  # noqa: E402

start = time.time()
balls, matches, comps = pr.load()
work, legal_pre = pr.add_situation(balls)
print("situation", round(time.time() - start, 1), "s", len(work), len(legal_pre))

first_pass = pr.run_elo(legal_pre)
first_summary = dict(first_pass.attrs["elo_summary"])
first_ratings = first_pass[["match_id", "innings", "innings_ball_num", "striker_id", "bowler_id", "ladder",
                            "batter_rating_after", "bowler_rating_after"]].copy()
del first_pass
print("first elo pass", round(time.time() - start, 1), "s", first_summary)

legal = pr.fit_elo(legal_pre)
final_summary = dict(legal.attrs["elo_summary"])
print("fit_elo", round(time.time() - start, 1), "s", final_summary)

batters = pr.score_batters(legal)
bowlers = pr.score_bowlers(legal, work)
traces = copy.deepcopy(pr.TRACES)
pooled_current = pr._pooled_batter_order(batters)
print("current scoring", round(time.time() - start, 1), "s")

# The same pipeline with super-over rows removed before tagging: the pre-change ratings, for comparison.
no_super_work, no_super_legal = pr.add_situation(balls.loc[~balls["is_super_over"].astype(bool)])
no_super_legal = pr.fit_elo(no_super_legal)
no_super_batters = pr.score_batters(no_super_legal)
no_super_bowlers = pr.score_bowlers(no_super_legal, no_super_work)
del no_super_work, no_super_legal
print("no-super-over scoring", round(time.time() - start, 1), "s")

LEGACY_REV = "29956ed"
source = subprocess.check_output(["git", "show", f"{LEGACY_REV}:player_ratings.py"], cwd=ROOT).decode("utf-8")
head_rev = subprocess.check_output(["git", "rev-parse", LEGACY_REV], cwd=ROOT).decode().strip()
legacy = types.ModuleType("legacy_player_ratings")
exec(compile(source, f"git:{LEGACY_REV}:player_ratings.py", "exec"), legacy.__dict__)
if "FORM_WEIGHT" not in legacy.__dict__:
    raise AssertionError(f"{LEGACY_REV} is not the eight-term model")
legacy_batters = legacy.score_batters(legal)
legacy_bowlers = legacy.score_bowlers(legal, work)
legacy_traces = copy.deepcopy(legacy.TRACES)
pooled_legacy = legacy._pooled_batter_order(legacy_batters)
legacy_weights = {name: getattr(legacy, name) for name in dir(legacy) if name.endswith("_WEIGHT")}
print("legacy scoring", round(time.time() - start, 1), "s", legacy_weights)

pre_cols = ["match_id", "innings", "n", "shock_bat", "shock_bowl", "pressure_bat", "pressure_bowl", "band", "band_bowl"]
payload = {
    "balls": balls,
    "matches": matches,
    "comps": comps,
    "work": work,
    "legal": legal,
    "legal_pre_pressure": legal_pre[pre_cols].copy(),
    "first_summary": first_summary,
    "first_ratings": first_ratings,
    "final_summary": final_summary,
    "batters": batters,
    "bowlers": bowlers,
    "traces": traces,
    "pooled_current": pooled_current,
    "no_super_batters": no_super_batters,
    "no_super_bowlers": no_super_bowlers,
    "legacy_batters": legacy_batters,
    "legacy_bowlers": legacy_bowlers,
    "legacy_traces": legacy_traces,
    "pooled_legacy": pooled_legacy,
    "legacy_weights": legacy_weights,
    "head_rev": head_rev,
}
with open(CACHE / "pipeline.pkl", "wb") as handle:
    pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
print("cached", CACHE / "pipeline.pkl", round(time.time() - start, 1), "s")
