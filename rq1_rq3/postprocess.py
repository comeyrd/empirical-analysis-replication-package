"""Raw Baseliner reports of the main corpus -> the derived files of one platform (see data.py).

Every metric is recomputed from the launch times (execution_time_vector) of each trace:
  location    median m, mean mu
  dispersion  CV = std / mu, RCV_MAD = 1.4826 MAD / m, RCV_IQR = 0.75 IQR / m, RCV_OQAD = OQAD / m,
              with OQAD = 0.674731 x Q(|t - m|, 0.8617) (breakdown point 13.83 %, degenerates beyond
              86.17 % of ties)
  geometry    floor margin P = (m - t_min) / m, knee margin C = (t_knee - m) / m, upper tail mass T =
              share of launches above t_knee; t_knee from the Kneedle point of the complementary ECDF
  shape       D'Agostino-Pearson K2 test (rejected at 0.001), skewness, Fisher excess kurtosis
  timer       quantization step (median gap between distinct values), distinct values, ties with m
"""
from __future__ import annotations

import concurrent.futures
import warnings

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import scipy.stats as stats

from common import report
from rq1_rq3 import data as D

OQAD_P, OQAD_K = 0.8617, 0.674731
RCV_IQR_FACTOR, RCV_MAD_FACTOR = 0.75, 1.4826
CARD_NICKNAME = {"Tesla V100-DGXS-32GB": "V100", "AMD Instinct MI210": "MI210"}


def qad(x: np.ndarray, median: float) -> float:
    return float(OQAD_K * np.quantile(np.abs(x - median), OQAD_P))


def knee(x: np.ndarray, median: float, alpha_max: float = 15.0, n_points: int = 151) -> tuple[float, float, float]:
    """Kneedle point of the share of launches above median x (1 + alpha), alpha in [0, 15] %:
    returns (t_knee - m in ms, C in %, T in %)."""
    if median <= 0 or len(x) <= 1:
        return 0.0, 0.0, 0.0
    alphas = np.linspace(0.0, alpha_max, n_points)
    above = (len(x) - np.searchsorted(np.sort(x), median * (1.0 + alphas / 100.0), side="right")) / len(x) * 100.0
    span = above[0] - above[-1]
    if span <= 0.05:
        return 0.0, 0.0, float(above[0])
    i = int(np.argmax((1.0 - alphas / alpha_max) - (above - above[-1]) / span))
    return float(alphas[i] / 100.0 * median), float(alphas[i]), float(above[i])


def trace_metrics(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    median, mean = float(np.median(x)), float(x.mean())
    std = float(x.std(ddof=1)) if len(x) > 1 else np.nan
    mad = float(np.median(np.abs(x - median)))
    q25, q75 = np.percentile(x, [25, 75])
    iqr, oqad = float(q75 - q25), qad(x, median)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        k2_p = float(stats.normaltest(x).pvalue)
        skew = float(stats.skew(x, bias=False))
        kurt = float(stats.kurtosis(x, fisher=True, bias=False))
    unique = np.unique(x)
    step = float(np.median(np.diff(unique))) if len(unique) > 1 else 0.0
    c_abs, c_rel, tail = knee(x, median)
    return {
        "n": len(x), "min": float(x.min()), "max": float(x.max()), "median": median, "mean": mean, "std": std,
        "mad": mad, "cv": std / mean, "IQR": iqr, "QAD": oqad,
        "RCV_IQR": RCV_IQR_FACTOR * (iqr / median), "RCV_MAD": RCV_MAD_FACTOR * (mad / median), "RCV_QAD": oqad / median,
        "reject_normality_abs": bool(np.isfinite(k2_p) and k2_p < 0.001), "k2_pval_abs": k2_p,
        "floor_gap_rel": (median - x.min()) / median * 100.0,
        "bulk_horizon_abs": c_abs, "bulk_horizon_rel": c_rel, "tail_mass_rel": tail,
        "skew_moment_abs": skew if np.isfinite(skew) else 0.0, "kurtosis_fisher_abs": kurt if np.isfinite(kurt) else 0.0,
        "pct_at_median_rel": float(np.mean(x == median) * 100.0), "unique_values_n": len(unique),
        "timer_step_abs": step, "timer_step_rel": step / median * 100.0,
    }


def run(plat: str) -> None:
    """Rebuild post_process_df.csv, full_run.parquet and the rq3_* files of a platform from raw/."""
    folder = D.folder(plat)
    files = sorted((folder / "raw").glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no report in {folder / 'raw'}")
    schema = pa.schema([("run_id", pa.string()), ("run_ix", pa.int32()), ("time", pa.float64())])
    rows = []
    with pq.ParquetWriter(folder / "full_run.parquet", schema, compression="snappy") as writer:
        for f in files:
            print(f"  {f.name}")
            clocks = report.clocks_of(f)
            for t in report.traces(report.load(f)):
                times, unit = t["vectors"]["execution_time_vector"]
                x = np.asarray(times, dtype=np.float64)
                sc = t.pop("scalars")
                t.pop("vectors")
                rows.append({**t, "clocks": clocks, "locked": clocks == "locked", "unit": unit, **trace_metrics(x),
                             "median_reported": sc["median"][0], "n_reported": sc["repetitions"][0],
                             "benchmark_time": sc["cpu_time"][0]})
                # One row group per trace
                writer.write_table(pa.table({"run_id": [t["run_id"]] * len(x), "run_ix": np.arange(len(x), dtype=np.int32),
                                             "time": x}, schema=schema), row_group_size=len(x))
    df = pd.DataFrame(rows).drop(columns=["campaign_rank"])
    df["setup"] = df["campaign_name"].str.strip().str.capitalize()        # Full / Minimal
    # Campaign index: i-th report (by date) of each clock regime
    reports = df[["report_id", "locked", "datetime"]].drop_duplicates("report_id")
    reports = reports.assign(_dt=pd.to_datetime(reports["datetime"], utc=True)).sort_values(["locked", "_dt"])
    reports["experiment"] = reports.groupby("locked").cumcount()
    df = df.merge(reports[["report_id", "experiment"]], on="report_id")
    for m in ("cv", "RCV_IQR", "RCV_MAD", "RCV_QAD"):
        df[f"{m}_rel"] = df[m] * 100.0
    df["card.nickname"] = df["card"].map(CARD_NICKNAME).fillna(df["card"])
    front = ["run_id", "report_id", "campaign_id", "datetime", "card", "clocks", "locked", "experiment", "setup",
             "workload", "backend", "worksize", "unit", "n"]
    df = df[front + [c for c in df.columns if c not in front]]
    df = df.sort_values(["card", "locked", "experiment", "setup", "workload", "backend", "worksize"]).reset_index(drop=True)
    df.to_csv(folder / "post_process_df.csv", index=False)
    print(f"  {folder / 'post_process_df.csv'} ({len(df)} traces)")
    evolution_files(plat)


def _evolution(args) -> tuple[list, list]:
    """Per 25 launches of the first 10,000: cumulative median and RCV_OQAD (%), median of the batch."""
    run_id, x = args
    cumul, batch = [], []
    for b in range(min(len(x), D.N_NOMINAL) // D.STEP):
        end = (b + 1) * D.STEP
        m = float(np.median(x[:end]))
        cumul.append((run_id, end - 1, b, m, qad(x[:end], m) / m * 100.0 if m > 0 else 0.0))
        batch.append((run_id, end - 1, b, float(np.median(x[end - D.STEP:end]))))
    return cumul, batch


def evolution_files(plat: str) -> None:
    """rq3_cumulative.parquet and rq3_per_batch.parquet, in the trace order of full_run.parquet."""
    jobs = ((rid, rg["time"].to_numpy()) for rid, rg in D.traces(plat, ("run_id", "time")))
    cumul, batch = [], []
    with concurrent.futures.ProcessPoolExecutor() as ex:
        for c, b in ex.map(_evolution, jobs, chunksize=16):
            cumul += c
            batch += b
    folder = D.folder(plat)
    pd.DataFrame(cumul, columns=["run_id", "run_ix", "batch_ix", "median", "RCVOQAD"]).to_parquet(folder / "rq3_cumulative.parquet", index=False)
    pd.DataFrame(batch, columns=["run_id", "run_ix", "batch_ix", "median"]).to_parquet(folder / "rq3_per_batch.parquet", index=False)
    print(f"  {folder}/rq3_cumulative.parquet, rq3_per_batch.parquet")
