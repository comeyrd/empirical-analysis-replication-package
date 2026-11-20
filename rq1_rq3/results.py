"""Values of RQ-E-1 to RQ-E-3 quoted in the thesis text (outputs/results.md).

Paired tests: one pair per cell (workload, work size, clocks, harness) unless stated; level metrics of a
cell are the median of its 10 campaigns, drifts follow the thesis notation (data.cell_drift).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common.results import Results, num
from common.stats import holm, wilcoxon_hl
from rq1_rq3 import data as D
from rq1_rq3.postprocess import OQAD_P

HEAD = 150          # RQ-E-1.3: launches of the head of a trace
FAST_PCT = 2.0      # a launch is fast when at least 2 % faster than the trace median
LEVELS = {"m": "median", "P": "floor_gap_rel", "C": "bulk_horizon_rel", "T": "tail_mass_rel", "rcv": "RCV_QAD_rel"}


def cell_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per cell: levels (median over campaigns), drifts, campaigns where MAD, IQR or OQAD is exactly 0."""
    g = df.groupby(D.CELL)
    cells = g[list(LEVELS.values())].median().rename(columns={v: k for k, v in LEVELS.items()})
    for key, col in (("deg_mad", "mad"), ("deg_iqr", "IQR"), ("deg_oqad", "QAD")):
        cells[key] = g[col].agg(lambda x: int((x == 0).sum()))
    cells = cells.reset_index()
    for drift in (D.cell_drift(df, {"d_m": "median", "d_mu": "mean"}, relative_to="median"),
                  D.cell_drift(df, {"d_P": "floor_gap_rel", "d_C": "bulk_horizon_rel", "d_T": "tail_mass_rel", "d_rcv": "RCV_QAD_rel"}),
                  D.cell_drift(df, {"rd_cv": "cv_rel"}, relative_to="cv_rel"),
                  D.cell_drift(df, {"rd_rcv": "RCV_QAD_rel"}, relative_to="RCV_QAD_rel")):
        cells = cells.merge(drift.drop(columns="K"), on=D.CELL, validate="one_to_one")
    return cells


def _paired(a, b, d=None) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b if d is None else np.asarray(d, float)
    keep = np.isfinite(a) & np.isfinite(b) & np.isfinite(d)
    return wilcoxon_hl(d[keep])


def factor_tests(cells: pd.DataFrame, factor: str) -> dict[str, dict]:
    """Tested level minus reference level, the other factor fixed in each pair, for the 10 metrics;
    Holm over these 10 tests. delta m is relative: (m_b - m_a) / m_a x 100."""
    a_level, b_level = D.FACTOR_LEVELS[factor]
    keys = ["workload", "worksize", "setup" if factor == "clocks" else "clocks"]
    pairs = cells[cells[factor] == b_level].merge(cells[cells[factor] == a_level], on=keys, suffixes=("_b", "_a"), validate="one_to_one")
    out = {}
    for k in ("m", "P", "C", "T", "d_m", "d_P", "d_C", "d_T", "rcv", "d_rcv"):
        a, b = pairs[f"{k}_b"], pairs[f"{k}_a"]
        out[k] = _paired(a, b, (a - b) / b * 100.0 if k == "m" else None)
    for k, p in zip(out, holm([r["p"] for r in out.values()])):
        out[k]["p_holm"] = p
    return out


def fast_shares() -> pd.DataFrame:
    """RQ-E-1.3 (MI210): per trace, % of fast launches among the first HEAD launches and among the next
    ones up to 10,000, and among all launches."""
    df = D.load("MI210")
    meta = df.set_index("run_id")
    rows = []
    for rid, rg in D.traces("MI210"):
        t = rg["time"].to_numpy()[np.argsort(rg["run_ix"].to_numpy(), kind="stable")]
        faster = (meta.at[rid, "median"] - t) / meta.at[rid, "median"] * 100.0
        fast = faster[:D.N_NOMINAL] >= FAST_PCT
        rows.append({"run_id": rid, "worksize": meta.at[rid, "worksize"], "floor": meta.at[rid, "floor_gap_rel"],
                     "head": fast[:HEAD].mean() * 100.0, "rest": fast[HEAD:].mean() * 100.0,
                     "mass_2": np.mean(faster >= 2.0) * 100.0, "mass_3": np.mean(faster >= 3.0) * 100.0})
    return pd.DataFrame(rows)


def make(criterion_values: dict | None) -> Results:
    R = Results("Values quoted in the text, RQ-E-1 to RQ-E-3")
    data = {p: D.load(p) for p in D.PLATFORMS}
    cells = {p: cell_table(df) for p, df in data.items()}

    rq = "RQ-E-1.1 Normality"
    for p, df in data.items():
        rej = df["reject_normality_abs"].astype(bool)
        R.add(rq, f"{p}: traces where D'Agostino-Pearson K2 rejects normality (alpha = 0.001)",
              f"{rej.mean() * 100:.1f} % ({rej.sum()} / {len(df)})", "test", "K2 omnibus test per trace", share=rej.mean() * 100)
        R.add(rq, f"{p}: work sizes of the non-rejected traces", ", ".join(map(str, sorted(df.loc[~rej, "worksize"].unique()))) or "none")
        R.add(rq, f"{p}: median skewness / median Fisher excess kurtosis over the traces",
              f"{df['skew_moment_abs'].median():.2f} / {df['kurtosis_fisher_abs'].median():.1f}")
        R.add(rq, f"{p}: traces with a negative skewness", f"{(df['skew_moment_abs'] < 0).mean() * 100:.1f} %")

    rq = "RQ-E-1.3 Lower tail (MI210)"
    shares = fast_shares()
    by_ws = shares.groupby("worksize")[["floor", "mass_2", "mass_3"]].mean()
    for ws, r in by_ws.iterrows():
        R.add(rq, f"work size {ws}: mean floor margin P / mean share of launches >= 2 % and >= 3 % faster than the median",
              f"{r['floor']:.2f} % / {r['mass_2']:.2f} % / {r['mass_3']:.2f} %")
    R.test(rq, f"Fast launches (>= {FAST_PCT:g} % faster than the median): first {HEAD} minus launches {HEAD}-9,999, "
               "one pair per trace", _paired(shares["head"], shares["rest"]), 1, "pp")

    rq = "RQ-E-1.4 Location estimators"
    for p, c in cells.items():
        R.test(rq, f"{p}: Delta mu - Delta m (drift of the mean minus drift of the median, % of the median)",
               _paired(c["d_mu"], c["d_m"]), 2, "pp")

    rq = "RQ-E-1.5 Dispersion estimators"
    for p, c in cells.items():
        R.test(rq, f"{p}: relative drift of CV minus that of RCV_OQAD (Delta X / mean X, %)", _paired(c["rd_cv"], c["rd_rcv"]), 0, "pp")
    R.add(rq, "OQAD breakdown point (1 - p) / degeneration point (p), p = 0.8617",
          f"{(1 - OQAD_P) * 100:.2f} % / {OQAD_P * 100:.2f} %")

    rq = "RQ-E-1.6 Degeneration"
    c = cells["V100"]
    tests = {est: _paired(c[col], c["deg_oqad"]) for est, col in (("MAD", "deg_mad"), ("IQR", "deg_iqr"))}
    for (est, r), p in zip(tests.items(), holm([r["p"] for r in tests.values()])):
        r["p_holm"] = p
        R.test(rq, f"V100: campaigns (out of 10) where {est} is 0 minus where OQAD is 0 (Holm over MAD and IQR)", r, 1,
               "campaigns", p_key="p_holm")
    mi = data["MI210"]
    R.add(rq, "MI210: traces where MAD, IQR or OQAD is exactly 0", f"{int(((mi['mad'] == 0) | (mi['IQR'] == 0) | (mi['QAD'] == 0)).sum())} / {len(mi)}")
    steps = {p: df["timer_step_abs"].median() * 1000 for p, df in data.items()}
    R.add(rq, "Timer step V100 / MI210 (median over traces)", f"{steps['V100'] / steps['MI210']:.1f} x "
          f"({steps['V100']:.3f} / {steps['MI210']:.3f} us)")

    effects = {(p, f): factor_tests(c, f) for p, c in cells.items() for f in ("clocks", "setup")}
    quoted = {
        "RQ-E-2.1 Clock locking": [("V100", "clocks", "m", "delta_clk m (%)", 1), ("MI210", "clocks", "m", "delta_clk m (%)", 1),
                                   ("V100", "clocks", "C", "delta_clk C (pp)", 2), ("MI210", "clocks", "P", "delta_clk P (pp)", 1)],
        "RQ-E-2.2 Harness": [("V100", "setup", "m", "delta_harn m (%)", 2), ("V100", "setup", "T", "delta_harn T (pp)", 2),
                             ("MI210", "setup", "m", "delta_harn m (%)", 2)],
        "RQ-E-2.3 Geometry reproducibility": [(p, "clocks", k, f"delta_clk {k[2:]} drift (pp)", 2) for p in D.PLATFORMS for k in ("d_P", "d_C", "d_T")],
        "RQ-E-2.4 Estimator reproducibility": [("V100", "clocks", "rcv", "delta_clk RCV_OQAD (pp)", 2),
                                               ("V100", "clocks", "d_rcv", "delta_clk Delta RCV_OQAD (pp)", 2),
                                               ("MI210", "clocks", "rcv", "delta_clk RCV_OQAD (pp)", 2),
                                               ("MI210", "setup", "rcv", "delta_harn RCV_OQAD (pp)", 2)],
    }
    for rq, items in quoted.items():
        for p, f, k, label, digits in items:
            what = "locked - unlocked clocks, harness fixed" if f == "clocks" else "Full - Minimal harness, clocks fixed"
            R.test(rq, f"{p}: {label}, {what} (Holm over 10 metrics)", effects[(p, f)][k], digits, p_key="p_holm",
                   method="paired Wilcoxon + HL [95 % CI], Holm")

    total = sum(df["benchmark_time"].sum() for df in data.values()) / 3.6e6
    R.add("RQ-E-2.5 Temporal cost", "Cumulative wall time of the traces, both platforms, all configurations "
          "(the thesis quotes 24.81 h, the sum of the rounded hours of the table)", f"{total:.2f} h")

    if criterion_values is not None:
        rq = "RQ-E-3.4 Tuning (training campaigns)"
        q = criterion_values["rule_paired"]
        for _, r in q.iterrows():
            what = "N*" if r["metric"] == "N*" else "stop error (pp)"
            text = (f"HL = {num(r['hl'], 3, True)} [{num(r['ci_low'], 3, True)} ; {num(r['ci_high'], 3, True)}], p Holm = {r['p_holm']:.1e}, "
                    f"cells that differ: {r['share_pos'] + r['share_neg']:.0f} %, HL over them = {num(r['hl_moved'], 3, True)} "
                    f"[{num(r['ci_low_moved'], 3, True)} ; {num(r['ci_high_moved'], 3, True)}]")
            R.add(rq, f"{r['card']}: SMS+ minus {r['label'].split(' - ')[1]}, {what}, per cell (mean over campaigns)", text, "test",
                  "paired Wilcoxon + HL [95 % CI], Holm per platform and measure", **{k: r[k] for k in ("hl", "ci_low", "ci_high", "p_holm")})
    return R
