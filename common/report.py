"""Read Baseliner (v1.0) JSON reports.

A report holds campaigns; each campaign runs benchmarks (one per backend and workload), and each
benchmark holds one result per sweep point: a trace. A metric is a scalar, or a list with one value
per launch (EVERY_ELEMENT) or per batch (EVERY_BATCH).

The clock regime is not in the report: Baseliner's run scripts write it in the file name
(<timestamp>_locked.json or <timestamp>_unlocked.json).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

TO_MS = {"ms": 1.0, "us": 1e-3, "ns": 1e-6, "s": 1e3}


def clocks_of(path: str | Path) -> str:
    name = Path(path).name
    if "unlocked" in name:
        return "unlocked"
    if "locked" in name:
        return "locked"
    raise ValueError(f"{name}: a report name must contain 'locked' or 'unlocked'")


def load(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def traces(report: dict) -> Iterator[dict]:
    """One dict per trace, in report order: identification, scalars {name: (value, unit)} and
    vectors {name: (values, unit)}."""
    for rank, campaign in enumerate(report["campaign_runs"]):
        for backend, by_workload in campaign["benchmark_runs"].items():
            for execution in by_workload.values():
                plan, bench = execution["plan"], execution["benchmark_report"]
                for run in bench["results"]:
                    scalars, vectors = {}, {}
                    for m in run["measurements"]:
                        (vectors if isinstance(m["data"], list) else scalars)[m["name"]] = (m["data"], m["unit"])
                    yield {
                        "report_id": report["id"], "datetime": report["datetime"],
                        "baseliner_version": report["baseliner_version"], "git_version": report["git_version"],
                        "campaign_id": campaign["id"], "campaign_name": campaign["name"],
                        "campaign_rank": rank, "recipe_name": campaign["recipe_name"],
                        "benchmark_id": bench["id"], "run_id": run["id"], "backend": plan["backend"]["impl"],
                        "workload": plan["workload"]["impl"], "card": bench["hardware"]["card_name"],
                        "worksize": int(run["sweep_point"]["Workload"]["work_size"]["value"]),
                        "scalars": scalars, "vectors": vectors,
                    }


def in_ms(value, unit: str):
    """Value (number or list) converted to milliseconds."""
    f = TO_MS[unit]
    return [v * f for v in value] if isinstance(value, list) else value * f
