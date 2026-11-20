"""Data of the SMS experiment (RQ-E-4): paths, strategies, traces and cells.

Layout of one platform folder, rq4/data/<mi210|v100>/:
  raw/*.json           Baseliner reports, <timestamp>_<locked|unlocked>.json, one per run
  traces.csv           one row per trace (extract.py)
  batches.csv          N >= 2,000 traces: median of each batch of 25 launches up to 2,000 (extract.py)
  control/raw/*.json   control run of RQ-E-4.6 (statistics of the corpus vs of the SMS experiment)
  control.csv          one row per trace of the control run (extract.py)

A run measures every cell (workload, work size, harness) with every strategy, at one clock regime;
runs alternate locked and unlocked, and the k-th run of each regime is campaign k.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common.stats import loo_drift

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
PLATFORMS = ("V100", "MI210")
CELL = ["horloges", "workload", "work_size", "harnais"]
HARNESS = ("minimal", "full")
CLOCKS = ("locked", "unlocked")
K = 10
# Strategy code -> name in the LaTeX tables (thesis macros \smsp and \smsz), in table order
STRATEGIES = {"sms": r"\smsp", "sms-c0": r"\smsz", "fixed-600": r"$N$ fixe $\geq 600$", "fixed-2000": r"$N$ fixe $\geq 2\,000$",
              "primbench": "PrimBench", "nvbench-stdrel": r"NVBench \texttt{stdrel}", "nvbench-entropy": r"NVBench \texttt{entropy}"}
FIXED = ("fixed-600", "fixed-2000")
DYNAMIC = tuple(s for s in STRATEGIES if s not in FIXED)
RULES = ("sms", "sms-c0")
RULE = "sms"                                   # A of the paired comparisons
OTHERS = tuple(s for s in STRATEGIES if s != RULE)
REFERENCE = "fixed-2000"
CAP = {"sms": 600, "sms-c0": 600, "fixed-600": 600, "fixed-2000": 2000, "primbench": 2000, "nvbench-entropy": 2000,
       "nvbench-stdrel": 200_000}
ERROR_PCT = 2.0
SEED, B = 20261114, 2000


def folder(plat: str) -> Path:
    return DATA / plat.lower()


def available() -> list[str]:
    return [p for p in PLATFORMS if (folder(p) / "traces.csv").exists()]


def traces(plat: str) -> pd.DataFrame:
    """Traces with their reference and failure. Reference: mean median of the N >= 2,000 traces of the same
    cell in the other campaigns; failure: |m* - ref| / ref > 2 %."""
    t = pd.read_csv(folder(plat) / "traces.csv")
    ref = t[t["critere"] == REFERENCE][CELL + ["k", "median_ms"]]
    tot = ref.groupby(CELL)["median_ms"].agg(total="sum", count="count").reset_index()
    t = t.merge(tot, on=CELL, how="left").merge(ref.rename(columns={"median_ms": "_own"}), on=CELL + ["k"], how="left")
    n = t["count"] - t["_own"].notna().astype(int)
    t["ref_ms"] = (t["total"] - t["_own"].fillna(0.0)) / n.where(n > 0)
    t["err_pct"] = (t["median_ms"] - t["ref_ms"]).abs() / t["ref_ms"] * 100.0
    t["echec"] = t["err_pct"] > ERROR_PCT
    t["au_plafond"] = t["n_star"] >= t["critere"].map(CAP)       # meaningful for the dynamic strategies only
    return t.drop(columns=["total", "count", "_own"]).sort_values(CELL + ["k", "critere"]).reset_index(drop=True)


def cells(t: pd.DataFrame) -> pd.DataFrame:
    """One row per (cell, strategy): medians over the K campaigns, shares, and the inter-campaign drifts
    Delta N* and Delta m* (%). Noise and duration of a cell: RCV_OQAD and median of its N >= 2,000 traces."""
    g = t.groupby(CELL + ["critere"])
    c = g.agg(K=("k", "count"), n_star=("n_star", "median"), median_ms=("median_ms", "median"), t_gpu_ms=("t_gpu_ms", "median"),
              t_cpu_ms=("t_cpu_ms", "median"), part_echecs=("echec", "mean"), part_plafond=("au_plafond", "mean")).reset_index()
    c["dN_pct"] = g["n_star"].agg(loo_drift).values
    c["dm_pct"] = g["median_ms"].agg(loo_drift).values
    ref = t[t["critere"] == REFERENCE].groupby(CELL).agg(bruit_rcv_oqad=("rcv_oqad", "median"), duree_ms=("median_ms", "median"))
    return c.merge(ref.reset_index(), on=CELL, how="left")


def by_strategy(c: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Cells of one strategy, in the same order for every strategy."""
    return c[c["critere"] == strategy].sort_values(CELL).reset_index(drop=True)


def pair(a: pd.DataFrame, b: pd.DataFrame, keys: list[str], cols: list[str]) -> pd.DataFrame:
    """Rows of a and b matched on keys: columns <col>_a and <col>_b."""
    return a[keys + cols].merge(b[keys + cols], on=keys, suffixes=("_a", "_b"), validate="one_to_one")


def workload_draws(workloads) -> tuple[list[str], np.ndarray]:
    """Bootstrap weights of the workloads (sorted), the same for every bootstrap of a platform."""
    from common.stats import bootstrap_weights
    names = sorted(workloads)
    return names, bootstrap_weights(len(names), B, np.random.default_rng(SEED))
