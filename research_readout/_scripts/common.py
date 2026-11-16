"""Shared paths, the cached pipeline frames, and the traceability and facts registries."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_readout"
CACHE = OUT / "_cache"

STATUSES = ("COMPUTED", "EXISTING", "REQUIRES_DATA", "REQUIRES_IMPLEMENTATION", "NOT_APPLICABLE")

SANITY_PLAYERS = [
    "Jos Buttler", "Virat Kohli", "David Miller", "Jasprit Bumrah", "Rashid Khan",
    "Rilee Rossouw", "Matthew Humphreys", "Corbin Bosch", "Mahendra Singh Dhoni", "Tim David",
    "Imad Wasim", "Vaibhav Sooryavanshi", "Rahmanullah Gurbaz",
]
ELO_PLAYERS = SANITY_PLAYERS[:8]
COMPONENTS = ["baseline", "band_zero", "band_medium", "band_high", "clutch", "peers", "consistency"]
WEIGHTS = {"baseline": 0.20, "band_zero": 0.10, "band_medium": 0.15, "band_high": 0.20,
           "clutch": 0.15, "peers": 0.10, "consistency": 0.10}
LEGACY_COMPONENTS = ["baseline", "band_zero", "band_medium", "band_high", "clutch", "peers", "form", "consistency"]
LEGACY_WEIGHTS = {"baseline": 0.20, "band_zero": 0.10, "band_medium": 0.15, "band_high": 0.20,
                  "clutch": 0.15, "peers": 0.10, "form": 0.05, "consistency": 0.05}
LABEL = {"baseline": "Baseline", "band_zero": "Zero pressure", "band_medium": "Medium pressure",
         "band_high": "High pressure", "clutch": "Clutch", "peers": "Peers", "consistency": "Consistency",
         "form": "Form (removed)"}

_PAYLOAD = None


def load() -> dict:
    global _PAYLOAD
    if _PAYLOAD is None:
        with open(CACHE / "pipeline.pkl", "rb") as handle:
            _PAYLOAD = pickle.load(handle)
    return _PAYLOAD


class Registry:
    """Collects one traceability row per output and a flat dictionary of headline facts."""

    def __init__(self, name: str):
        self.name = name
        self.rows: list[dict] = []
        self.facts: dict = {}

    def save(self, frame: pd.DataFrame, rel: str, source: str, method: str, status: str = "COMPUTED", index: bool = False) -> Path:
        assert status in STATUSES, status
        path = OUT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=index)
        self.rows.append({"output": rel, "rows": int(len(frame)), "status": status, "source": source, "method": method})
        return path

    def note(self, rel: str, source: str, method: str, status: str = "COMPUTED") -> None:
        self.rows.append({"output": rel, "rows": "", "status": status, "source": source, "method": method})

    def fact(self, key: str, value) -> None:
        if isinstance(value, (np.integer,)):
            value = int(value)
        elif isinstance(value, (np.floating,)):
            value = float(value)
        elif isinstance(value, (np.bool_,)):
            value = bool(value)
        self.facts[key] = value

    def close(self) -> None:
        CACHE.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.rows).to_csv(CACHE / f"trace_{self.name}.csv", index=False)
        with open(CACHE / f"facts_{self.name}.json", "w", encoding="utf-8") as handle:
            json.dump(self.facts, handle, indent=1, default=str)


def all_facts() -> dict:
    facts = {}
    for path in sorted(CACHE.glob("facts_*.json")):
        with open(path, encoding="utf-8") as handle:
            facts.update(json.load(handle))
    return facts


def metric_row(metric: str, value, status: str = "COMPUTED", source: str = "", notes: str = "") -> dict:
    return {"metric": metric, "value": value, "status": status, "source": source, "notes": notes}


def describe(series: pd.Series, name: str) -> dict:
    clean = pd.Series(series, dtype=float).dropna()
    out = {"variable": name, "n": int(len(clean)), "mean": clean.mean(), "sd": clean.std(ddof=0),
           "min": clean.min()}
    for q in (0.01, 0.05, 0.25, 0.50, 0.75, 0.80, 0.90, 0.95, 0.99):
        out[f"p{int(round(q * 100)):02d}"] = clean.quantile(q)
    out["max"] = clean.max()
    return out


def player_ids(frame: pd.DataFrame, name: str, col: str = "player_name") -> list:
    return frame.loc[frame[col].eq(name), "player_id"].tolist()
