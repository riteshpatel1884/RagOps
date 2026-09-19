"""
Phase 5: Regression Testing.

Stores metric history per named "version" and compares any two versions,
flagging any metric that got worse beyond a threshold. This is what lets
you answer "did my change actually help?" with a real check instead of
eyeballing a handful of numbers after every edit — the gap Phase 4's
diagnostic engine explicitly flagged (a suggestion that improves recall
can quietly hurt precision or faithfulness).

A "version" here is just a pipeline config + the metrics it produced,
recorded under a name you choose (e.g. "v1", "baseline",
"release-2026-09-19"). Nothing assumes a specific deployment system —
record a version any time you want a fixed point to compare future
changes against. Reuses experiment.py's run_single_config() so this
module contains zero duplicated evaluation logic.
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pipeline import PipelineConfig
from experiment import run_single_config, load_data

HISTORY_PATH = Path(__file__).parent / "regression_history.json"

# Direction each metric should move to be "better". A metric not listed
# here is ignored by regression checks (recorded, but not compared).
METRIC_DIRECTIONS = {
    "recall": "higher",
    "precision": "higher",
    "mrr": "higher",
    "ndcg": "higher",
    "faithfulness": "higher",
    "relevance": "higher",
    "elapsed_seconds": "lower",
}

# Minimum absolute change (in the metric's own units) before a drop counts
# as a real "regression" rather than noise. Same caveat as diagnostics.py's
# thresholds: tuned for a small test set, not universal — retune for your
# own dataset size and risk tolerance.
REGRESSION_THRESHOLDS = {
    "recall": 0.05,
    "precision": 0.05,
    "mrr": 0.05,
    "ndcg": 0.05,
    "faithfulness": 0.03,
    "relevance": 0.05,
    "elapsed_seconds": 1.0,  # seconds
}


@dataclass
class VersionRecord:
    name: str
    timestamp: str
    config: dict
    metrics: dict
    notes: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


class RegressionHistory:
    """JSON-file-backed store of named versions. One file, human-readable, diffable in git."""

    def __init__(self, path: Path = HISTORY_PATH):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {"versions": {}, "baseline": None}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_version(self, name: str, config: dict, metrics: dict, notes: str = "", set_as_baseline: bool = False) -> VersionRecord:
        record = VersionRecord(name=name, timestamp=datetime.now().isoformat(), config=config, metrics=metrics, notes=notes)
        self.data["versions"][name] = record.as_dict()
        if set_as_baseline or self.data["baseline"] is None:
            self.data["baseline"] = name
        self._save()
        return record

    def get_version(self, name: str) -> Optional[dict]:
        return self.data["versions"].get(name)

    def list_versions(self) -> List[dict]:
        return list(self.data["versions"].values())

    def get_baseline_name(self) -> Optional[str]:
        return self.data["baseline"]

    def set_baseline(self, name: str):
        if name not in self.data["versions"]:
            raise ValueError(f"Unknown version: '{name}'")
        self.data["baseline"] = name
        self._save()

    def delete_version(self, name: str):
        if name not in self.data["versions"]:
            raise ValueError(f"Unknown version: '{name}'")
        del self.data["versions"][name]
        if self.data["baseline"] == name:
            remaining = list(self.data["versions"].keys())
            self.data["baseline"] = remaining[0] if remaining else None
        self._save()


def compare_versions(old_metrics: dict, new_metrics: dict) -> dict:
    """
    Compare two metric dicts and classify every shared, direction-known
    metric as a regression, an improvement, or unchanged (within
    threshold). Direction-aware: an increase in elapsed_seconds is a
    regression, but an increase in recall is an improvement.
    """
    regressions, improvements, unchanged = [], [], []

    for metric, direction in METRIC_DIRECTIONS.items():
        if metric not in old_metrics or metric not in new_metrics:
            continue
        old_val, new_val = old_metrics[metric], new_metrics[metric]
        delta = new_val - old_val
        threshold = REGRESSION_THRESHOLDS.get(metric, 0.0)

        got_worse = delta < 0 if direction == "higher" else delta > 0
        entry = {"metric": metric, "old": old_val, "new": new_val, "delta": delta, "direction": direction}

        if got_worse and abs(delta) > threshold:
            regressions.append(entry)
        elif not got_worse and abs(delta) > threshold:
            improvements.append(entry)
        else:
            unchanged.append(entry)

    return {
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
        "has_regression": len(regressions) > 0,
    }


def format_report(old_name: str, new_name: str, comparison: dict) -> str:
    lines = [f"\n=== Regression check: {new_name} vs {old_name} ==="]
    lines.append("\u26a0\ufe0f  REGRESSION DETECTED\n" if comparison["has_regression"] else "\u2705 No regressions detected\n")

    def fmt(e, arrow):
        return f"  {arrow} {e['metric']:<15} {e['old']:.3f} \u2192 {e['new']:.3f}  ({e['delta']:+.3f})"

    if comparison["regressions"]:
        lines.append("Regressions:")
        lines += [fmt(e, "\u2193") for e in comparison["regressions"]]
        lines.append("")

    if comparison["improvements"]:
        lines.append("Improvements:")
        lines += [fmt(e, "\u2191") for e in comparison["improvements"]]
        lines.append("")

    if comparison["unchanged"]:
        lines.append("Unchanged (within threshold):")
        lines += [f"  \u00b7 {e['metric']:<15} {e['old']:.3f} \u2192 {e['new']:.3f}" for e in comparison["unchanged"]]

    return "\n".join(lines)


def record_version(name: str, config: PipelineConfig, judge: str = "offline", notes: str = "",
                    set_as_baseline: bool = False, history: Optional[RegressionHistory] = None) -> VersionRecord:
    """Run a config's full retrieval+generation evaluation and store it as a named version."""
    documents, test_set = load_data()
    raw = run_single_config(config, documents, test_set, judge=judge, skip_generation=False)
    if "error" in raw:
        raise RuntimeError(f"Evaluation failed: {raw['error']}")

    metrics = {k: v for k, v in raw.items() if k != "config"}
    history = history or RegressionHistory()
    return history.add_version(name, config.as_dict(), metrics, notes=notes, set_as_baseline=set_as_baseline)