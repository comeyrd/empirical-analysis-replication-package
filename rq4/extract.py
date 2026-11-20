"""Raw reports of the SMS experiment -> traces.csv, batches.csv and control.csv (see data.py).

A recipe is named <harness>-<strategy> (minimal-sms, full-fixed-2000, ...). Per trace, the statistics
reported by Baseliner are kept: N* (repetitions), median, RCV_OQAD, GPU time (sum of the launches) and
wall time (cpu_time); the launch times give the medians of fixed windows of launches.
"""
from __future__ import annotations

import concurrent.futures
import re

import numpy as np
import pandas as pd

from common import report
from rq4 import data as D

WINDOWS = {"m_0_2000": (0, 2000), "m_200_400": (200, 400), "m_1500_2000": (1500, 2000)}
BATCH, N_BATCHES = 25, 80          # batches.csv: 80 batches of 25 launches, the first 2,000


def _ms(scalars: dict, name: str) -> float:
    value, unit = scalars[name]
    return report.in_ms(value, unit)


def _windows(t: np.ndarray) -> dict:
    return {k: float(np.median(t[a:b])) if len(t) >= b else np.nan for k, (a, b) in WINDOWS.items()}


def read_run(path) -> tuple[list[dict], list[tuple]]:
    """Trace rows and batch medians of one run report."""
    clocks, rows, batches = report.clocks_of(path), [], []
    for tr in report.traces(report.load(path)):
        harness, strategy = re.match(r"^(minimal|full)-(.+)$", tr["recipe_name"]).groups()
        sc = tr["scalars"]
        t = np.asarray(report.in_ms(*tr["vectors"]["execution_time_vector"]))
        rows.append({"file": path.name, "trace_id": tr["run_id"], "gpu": tr["card"], "horloges": clocks, "workload": tr["workload"],
                     "work_size": tr["worksize"], "harnais": harness, "critere": strategy, "n_star": sc["repetitions"][0],
                     "median_ms": _ms(sc, "median"), "rcv_oqad": sc["rcv_oqad"][0], "t_gpu_ms": _ms(sc, "gpu_accumulated_time"),
                     "t_cpu_ms": _ms(sc, "cpu_time"), **_windows(t)})
        if strategy == D.REFERENCE:
            batches += [(tr["run_id"], b, float(np.median(t[b * BATCH:(b + 1) * BATCH]))) for b in range(N_BATCHES)]
    return rows, batches


def read_control(path) -> pd.DataFrame:
    """Control run: N >= 2,000 with the Minimal harness, campaigns alternating the statistics of the main
    corpus (preset a) and those of the SMS experiment (preset b), 3 repetitions. Off-GPU time per launch:
    (wall time - launch times - host and device setup - fetch of the results) / N."""
    rows = []
    for tr in report.traces(report.load(path)):
        sc = tr["scalars"]
        t = np.asarray(report.in_ms(*tr["vectors"]["execution_time_vector"]))
        other = sum(_ms(sc, k) for k in ("host_setup_time", "device_setup_time", "fetch_results_time") if k in sc)
        w = _windows(t)
        rows.append({"preset": tr["recipe_name"][0], "rep": int(tr["campaign_name"].split()[-1]), "workload": tr["workload"],
                     "work_size": tr["worksize"], "n": len(t), "acceleration_pct": (w["m_1500_2000"] / w["m_200_400"] - 1) * 100,
                     "off_gpu_us": (_ms(sc, "cpu_time") - t.sum() - other) / len(t) * 1000})
    return pd.DataFrame(rows)


def run(plat: str) -> None:
    folder = D.folder(plat)
    files = sorted((folder / "raw").glob("*.json"))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:   # a loaded report takes several GB
        parts = list(ex.map(read_run, files))
    t = pd.DataFrame([r for rows, _ in parts for r in rows])
    # Campaign k: rank of the run among the runs of its clock regime, in time order
    rank = {f.name: k for regime in D.CLOCKS for k, f in enumerate([f for f in files if report.clocks_of(f) == regime], 1)}
    t.insert(1, "k", t["file"].map(rank))
    t = t[t["k"] <= D.K].sort_values(D.CELL + ["k", "critere"])
    t.to_csv(folder / "traces.csv", index=False)
    pd.DataFrame([b for _, batches in parts for b in batches], columns=["trace_id", "batch", "median_ms"]).to_csv(folder / "batches.csv", index=False)
    print(f"  {folder}/traces.csv ({len(t)} traces), batches.csv")
    control = sorted((folder / "control" / "raw").glob("*.json"))
    if control:
        pd.concat([read_control(f) for f in control]).to_csv(folder / "control.csv", index=False)
        print(f"  {folder}/control.csv")
