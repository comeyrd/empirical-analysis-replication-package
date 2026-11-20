"""Values of RQ-E-4 quoted in the thesis text (outputs/results.md).

Paired tests compare SMS+ (A) with each other strategy (B), one pair per cell, Holm over the 6
comparisons of a quantity. The guarantee is a workload bootstrap of the failure shares (B = 2,000).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common.results import Results, num
from common.stats import holm, loo_drift, weighted_share, wilcoxon_hl
from rq4 import data as D
from rq4.figures import acceleration, corpus_traces


def _holm(tests: dict) -> dict:
    for k, p in zip(tests, holm([r["p"] for r in tests.values()])):
        tests[k]["p_holm"] = p
    return tests


def cost(R: Results, plat: str, c: pd.DataFrame) -> None:
    rq = "RQ-E-4.1 Cost"
    a = D.by_strategy(c, D.RULE)
    pairs = {s: D.pair(a, D.by_strategy(c, s), D.CELL, ["n_star", "t_cpu_ms", "t_gpu_ms"]) for s in D.OTHERS}
    tests = _holm({s: wilcoxon_hl(p["n_star_a"] - p["n_star_b"]) for s, p in pairs.items()})
    R.test(rq, f"{plat}: N* of SMS+ minus N* of N >= 600, per cell (Holm over the 6 strategies)", tests["fixed-600"], 0,
           p_key="p_holm", method="paired Wilcoxon + HL [95 % CI], Holm")
    rel = lambda p, col: (p[f"{col}_a"].sum() - p[f"{col}_b"].sum()) / p[f"{col}_b"].sum() * 100  # noqa: E731
    p = pairs["fixed-600"]
    R.add(rq, f"{plat}: SMS+ vs N >= 600, relative difference of the sums over the cells: launches / wall time / GPU time",
          f"{rel(p, 'n_star'):+.1f} % / {rel(p, 't_cpu_ms'):+.1f} % / {rel(p, 't_gpu_ms'):+.1f} %")
    for s in ("fixed-2000", "primbench", "nvbench-stdrel", "nvbench-entropy"):
        R.add(rq, f"{plat}: SMS+ vs {s}, relative difference of the sum of N* over the cells", f"{rel(pairs[s], 'n_star'):+.1f} %")


def guarantee(R: Results, plat: str, t: pd.DataFrame) -> None:
    """Failure share of each strategy and its excess over N >= 600 and N >= 2,000, per clock regime."""
    rq = "RQ-E-4.2 Guarantee"
    names, w = D.workload_draws(t["workload"].unique())
    code = t["workload"].map({n: i for i, n in enumerate(names)}).to_numpy()
    for h in D.CLOCKS:
        shares = {}
        for s in D.STRATEGIES:
            m = ((t["horloges"] == h) & (t["critere"] == s)).to_numpy()
            counts = np.bincount(code[m], minlength=len(names)).astype(float)
            fails = np.bincount(code[m], weights=t["echec"].to_numpy(float)[m], minlength=len(names))[None, :]
            shares[s] = (weighted_share(np.ones((1, len(names))), fails, counts)[0, 0], weighted_share(w, fails, counts)[:, 0])
        for s in D.STRATEGIES:
            parts = [f"failures {shares[s][0]:.2f} %"]
            for ref in D.FIXED:
                if ref != s:
                    e = shares[s][1] - shares[ref][1]
                    parts.append(f"excess over {ref} {shares[s][0] - shares[ref][0]:+.2f} pp (U95 {np.percentile(e, 95):.2f})")
            R.add(rq, f"{plat}, {h}: {s}", ", ".join(parts), "test",
                  "workload bootstrap, non-inferior when U95 < 1 pp")


def early_stop_repro(R: Results, plat: str, t: pd.DataFrame, c: pd.DataFrame) -> None:
    """RQ-E-4.4: Delta m* of each rule over its traces stopped before the cap (cells with at least 2 of
    them), against Delta m* of N >= 600 over the same campaigns."""
    m600 = t[t["critere"] == "fixed-600"].set_index(D.CELL + ["k"])["median_ms"]
    tests = {}
    for s in D.RULES:
        kept = t[(t["critere"] == s) & ~t["au_plafond"]].sort_values(D.CELL + ["k"]).groupby(D.CELL).filter(lambda g: len(g) >= 2).copy()
        kept["m600"] = m600.reindex(pd.MultiIndex.from_frame(kept[D.CELL + ["k"]])).to_numpy()
        per_cell = kept.groupby(D.CELL).agg(rule=("median_ms", loo_drift), fixed=("m600", loo_drift))
        tests[s] = wilcoxon_hl(per_cell["rule"] - per_cell["fixed"])
    for s, r in _holm(tests).items():
        R.test("RQ-E-4.4 Reproducibility", f"{plat}: Delta m* of {s} minus that of N >= 600, traces stopped before the cap, "
               "same campaigns (Holm over the 2 rules)", r, 3, "pp", p_key="p_holm", method="paired Wilcoxon + HL [95 % CI], Holm")


def harness_gain(R: Results, plat: str, c: pd.DataFrame) -> None:
    """RQ-E-4.5: relative gain g = (N*_rule - N*_600) / N*_600 x 100 per cell, Full minus Minimal."""
    f600, tests = D.by_strategy(c, "fixed-600"), {}
    for s in D.RULES:
        p = D.pair(D.by_strategy(c, s), f600, D.CELL, ["n_star"])
        p["g"] = (p["n_star_a"] - p["n_star_b"]) / p["n_star_b"] * 100
        piv = p.pivot_table(index=["horloges", "workload", "work_size"], columns="harnais", values="g")
        tests[s] = wilcoxon_hl((piv["full"] - piv["minimal"]).dropna())
    for s, r in _holm(tests).items():
        R.test("RQ-E-4.5 Harness and clocks", f"{plat}: gain of {s} over N >= 600 with Full minus with Minimal (pp), paired by "
               "(clocks, workload, work size) (Holm over the 2 rules)", r, 1, "pp", p_key="p_holm", method="paired Wilcoxon + HL [95 % CI], Holm")


def _shift(a: pd.Series, b: pd.Series) -> tuple[dict, str]:
    """Paired test of b - a, with the medians of a and b and the number of pairs going down."""
    d = (b - a.reindex(b.index)).dropna()
    r = wilcoxon_hl(d)
    return r, f"medians {num(a[d.index].median(), 2)} % -> {num(b[d.index].median(), 2)} %, {int((d < 0).sum())} / {d.size} pairs down"


def _add_shift(R: Results, rq: str, label: str, r: dict, extra: str, p_key: str = "p") -> None:
    R.test(rq, label, r, 2, "pp", p_key=p_key, method="paired Wilcoxon + HL [95 % CI]" + (", Holm" if p_key == "p_holm" else ""))
    R.rows[-1]["value"] += f"; {extra}"


def acceleration_tests(R: Results, plat: str, t: pd.DataFrame) -> None:
    """RQ-E-4.6: acceleration m(1,500-2,000) / m(200-400) - 1 per cell, SMS experiment (traces reaching
    2,000 launches, all strategies) minus main corpus; then the control run, SMS statistics minus corpus
    statistics."""
    rq = "RQ-E-4.6 Online measurement"
    cor = acceleration({"corpus": corpus_traces(plat)}).set_index(D.CELL)["acceleration_pct"]
    long = t[t["n_star"] >= 2000].assign(acc=lambda x: (x["m_1500_2000"] / x["m_200_400"] - 1) * 100)
    sms = long.groupby(D.CELL)["acc"].median()
    r, extra = _shift(cor, sms)
    _add_shift(R, rq, f"{plat}: acceleration, SMS experiment minus main corpus, all cells", r, extra)
    for group in (["harnais", "horloges"], ["critere"]):
        if group == ["critere"]:
            parts = {f"strategy {s}": g.groupby(D.CELL)["acc"].median() for s, g in long.groupby("critere")}
        else:
            parts = {f"{col} = {v}": sms[sms.index.get_level_values(col) == v] for col in group for v in sorted(long[col].unique(), reverse=True)}
        shifts = {k: _shift(cor, v) for k, v in parts.items()}
        _holm({k: r for k, (r, _) in shifts.items()})
        for k, (r, extra) in shifts.items():
            _add_shift(R, rq, f"{plat}: acceleration, SMS minus corpus, {k} (Holm over these {len(parts)})", r, extra, "p_holm")
    by_wl = pd.DataFrame({"sms": sms, "corpus": cor.reindex(sms.index)}).groupby(level="workload").median()
    r, extra = _shift(by_wl["corpus"], by_wl["sms"])
    _add_shift(R, rq, f"{plat}: acceleration, SMS minus corpus, per workload (median of its cells)", r, extra)

    path = D.folder(plat) / "control.csv"
    if not path.exists():
        return
    ctl = pd.read_csv(path)
    cell = ctl.pivot_table(index=["workload", "work_size"], columns="preset", values=["acceleration_pct", "off_gpu_us"], aggfunc="median")
    acc = lambda df, p: df[("acceleration_pct", p)]  # noqa: E731
    r, extra = _shift(acc(cell, "a"), acc(cell, "b"))
    _add_shift(R, rq, f"{plat}, control run: acceleration, SMS statistics minus corpus statistics, all cells (median of 3 repetitions)", r, extra)
    R.add(rq, f"{plat}, control run: off-GPU time per launch, corpus statistics -> SMS statistics (median over the cells)",
          f"{cell[('off_gpu_us', 'a')].median():.1f} us -> {cell[('off_gpu_us', 'b')].median():.1f} us")
    reps = ctl.pivot_table(index=["rep", "workload", "work_size"], columns="preset", values="acceleration_pct")
    for name, parts in (("work size", {f"work size {ws}": g for ws, g in cell.groupby(level="work_size")}),
                        ("repetition", {f"repetition {k}": g for k, g in reps.groupby(level="rep")})):
        col = (lambda g, p: acc(g, p)) if name == "work size" else (lambda g, p: g[p])
        shifts = {k: _shift(col(g, "a"), col(g, "b")) for k, g in parts.items()}
        _holm({k: r for k, (r, _) in shifts.items()})
        for k, (r, extra) in shifts.items():
            _add_shift(R, rq, f"{plat}, control run: acceleration, SMS minus corpus statistics, {k} (Holm over the {name}s)", r, extra, "p_holm")
    wl = cell.groupby(level="workload").median()
    r, extra = _shift(acc(wl, "a"), acc(wl, "b"))
    _add_shift(R, rq, f"{plat}, control run: acceleration, SMS minus corpus statistics, per workload (median of its cells)", r, extra)


def make(pfs: dict) -> Results:
    R = Results("Values quoted in the text, RQ-E-4")
    for plat, (t, c) in pfs.items():
        cost(R, plat, c)
        guarantee(R, plat, t)
        early_stop_repro(R, plat, t, c)
        harness_gain(R, plat, c)
        acceleration_tests(R, plat, t)
    return R
