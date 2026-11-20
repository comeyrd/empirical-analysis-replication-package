"""Data of the main corpus (RQ-E-1 to RQ-E-3): paths, loading and cell-level aggregates.

Layout of one platform folder, rq1_rq3/data/<v100|mi210>/:
  raw/*.json               Baseliner reports, <timestamp>_<locked|unlocked>.json
  post_process_df.csv      one row per trace: metadata and metrics (postprocess.py)
  full_run.parquet         every launch: run_id, run_ix, time (ms); one row group per trace
  rq3_cumulative.parquet   per trace and per 25 launches: median and RCV_OQAD of the launches so far
  rq3_per_batch.parquet    per trace and per 25 launches: median of those 25 launches
  batch_series.npz         traces replayed with Baseliner's batches (criterion.py cache)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
PLATFORMS = ("V100", "MI210")            # order of the table blocks
CELL = ["workload", "worksize", "clocks", "setup"]
FACTOR_LEVELS = {"clocks": ("unlocked", "locked"), "setup": ("Minimal", "Full")}   # (reference a, tested b)
N_NOMINAL = 10_000
STEP = 25                                 # launches between two points of the rq3_* files
CONFIGS = [("Full", "locked", "Full / Locked"), ("Full", "unlocked", "Full / Unlocked"),
           ("Minimal", "locked", "Minimal / Locked"), ("Minimal", "unlocked", "Minimal / Unlocked")]


def folder(plat: str) -> Path:
    return DATA / plat.lower()


def available() -> list[str]:
    return [p for p in PLATFORMS if (folder(p) / "post_process_df.csv").exists()]


def load(plat: str) -> pd.DataFrame:
    return pd.read_csv(folder(plat) / "post_process_df.csv")


def traces(plat: str, columns=("run_id", "run_ix", "time")):
    """Yield (run_id, table) for each trace of full_run.parquet, one row group at a time."""
    pf = pq.ParquetFile(folder(plat) / "full_run.parquet")
    for i in range(pf.num_row_groups):
        rg = pf.read_row_group(i, columns=list(columns))
        yield rg["run_id"][0].as_py(), rg


def trace_times(plat: str, run_ids) -> dict[str, np.ndarray]:
    """Launch times (ms) of a few traces."""
    t = pq.read_table(folder(plat) / "full_run.parquet", filters=[("run_id", "in", list(run_ids))]).to_pandas()
    return {rid: g["time"].to_numpy() for rid, g in t.groupby("run_id", sort=False)}


# --------------------------------------------------------------------------- #
# Cell aggregates (thesis notation)
# --------------------------------------------------------------------------- #
def _loo_mean(values: pd.Series, groups: list[pd.Series]) -> pd.Series:
    """Mean over the K - 1 other campaigns of the same cell."""
    g = values.groupby(groups)
    total, count = g.transform("sum"), g.transform("count")
    return (total - values) / (count - 1).where(count > 1)


def cell_drift(df: pd.DataFrame, columns: dict[str, str], relative_to: str | None = None) -> pd.DataFrame:
    """Inter-campaign drift per cell, Delta X = 1/K sum_k |X_k - mean of the other campaigns|.

    With relative_to, each deviation is divided by the leave-one-out mean of that column (Delta m in %
    of the median); otherwise the drift keeps the unit of the column (pp for a column in %).
    """
    groups = [df[c] for c in CELL]
    ref = _loo_mean(df[relative_to].astype(float), groups) if relative_to else None
    devs = {}
    for name, col in columns.items():
        x = df[col].astype(float)
        dev = (x - _loo_mean(x, groups)).abs()
        if ref is not None:
            dev = (dev / ref * 100.0).where(dev != 0, 0.0).replace([np.inf, -np.inf], np.nan)
        devs[name] = dev
    devs = pd.DataFrame(devs)
    out = devs.groupby(groups).mean().mask(devs.isna().groupby(groups).any())
    out.insert(0, "K", df.groupby(groups).size())
    return out.reset_index()


def factor_effect(df: pd.DataFrame, factor: str, columns: dict[str, str], relative=()) -> pd.DataFrame:
    """delta_f X = mean(X_b) - mean(X_a) per pair of cells differing only by the factor (means over the K
    campaigns); output names in `relative` are (mean(X_b) - mean(X_a)) / mean(X_a) x 100."""
    a_level, b_level = FACTOR_LEVELS[factor]
    keys = [c for c in CELL if c != factor]
    means = df.groupby(keys + [factor])[list(dict.fromkeys(columns.values()))].mean().reset_index()
    pairs = means[means[factor] == a_level].drop(columns=factor).merge(
        means[means[factor] == b_level].drop(columns=factor), on=keys, suffixes=("_a", "_b"), validate="one_to_one")
    out = pairs[keys].copy()
    for name, col in columns.items():
        diff = pairs[f"{col}_b"] - pairs[f"{col}_a"]
        out[name] = diff / pairs[f"{col}_a"] * 100.0 if name in relative else diff
    return out


# --------------------------------------------------------------------------- #
# Evolution with the number of launches (RQ-E-3.1, RQ-E-3.2, RQ-E-4.6)
# --------------------------------------------------------------------------- #
def evolution(plat: str, df: pd.DataFrame, file: str, columns: list[str]) -> tuple[dict, pd.DataFrame]:
    """Matrices (traces x 400 points) of the given columns of an rq3_* file, over the first 10,000
    launches, the metadata aligned on their rows, and `ref`: for each trace, the mean over the other
    campaigns of its cell of the cumulative median at 10,000 launches (leave-one-out reference)."""
    path = folder(plat) / file
    t = pq.read_table(path, columns=["run_id", "run_ix"] + columns, filters=[("run_ix", "<=", N_NOMINAL - 1)]).to_pandas()
    t = t.sort_values(["run_id", "run_ix"]).reset_index(drop=True)
    steps = N_NOMINAL // STEP
    counts = t["run_id"].value_counts()
    t = t[t["run_id"].isin(counts[counts == steps].index)]
    run_ids = t["run_id"].iloc[::steps].values
    mats = {c: t[c].values.reshape(len(run_ids), steps) for c in columns}
    meta = df.drop_duplicates("run_id").set_index("run_id").reindex(run_ids).reset_index()
    m10k = pq.read_table(folder(plat) / "rq3_cumulative.parquet", columns=["run_id", "median"],
                         filters=[("run_ix", "==", N_NOMINAL - 1)]).to_pandas().drop_duplicates("run_id")
    meta["_m10k"] = meta["run_id"].map(m10k.set_index("run_id")["median"])
    g = meta.groupby(CELL)["_m10k"]
    count = g.transform("count").values
    mats["ref"] = np.where(count > 1, (g.transform("sum").values - meta["_m10k"].values) / (count - 1),
                           meta["_m10k"].values)
    return mats, meta
