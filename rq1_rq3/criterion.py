"""Offline study of the stopping criterion SMS (RQ-E-3.3 to RQ-E-3.6).

Each trace of the main corpus is replayed with Baseliner's batches (25 launches with the Minimal
harness, a dynamic size with Full) and every stopping strategy is simulated on it. After batch j, with
m_j the batch median, m~_j the cumulative median and tau = alpha x cumulative RCV_OQAD (%), SMS stops
when, over its last S batches:
  C0  mean |m_i - m~_j| / m~_j x 100 <= tau                      (window/cumulative agreement)
  C1  max |m_i - m_(i-1)| / m~_j x 100 <= tau                     (local stability)
  C2  no two consecutive changes of the same sign with |d_i + d_(i-1)| / m~_j x 100 > tau   (no drift)
and otherwise at the first batch reaching N_max. SMS+ uses C0, C1 and C2, SMS_0 only C0.

A trace fails when its median at the stop is more than 2 % away from its reference, the mean of the
10,000-launch medians of the same cell over the other training campaigns. The guarantee is a
non-inferiority to the fixed budget N >= 2,000 with a 1 pp margin, by workload bootstrap.

  design (training campaigns)  N_max (3.3), (alpha, S) (3.4), conditions (3.5)
  test   (test campaigns)      the frozen rules (3.6)
Raw values go to outputs/criterion/, formatted by tables.py and results.py.
"""
from __future__ import annotations

import concurrent.futures
import itertools
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from common.stats import bootstrap_weights, holm, weighted_share, wilcoxon_hl
from rq1_rq3 import data as D
from rq1_rq3.postprocess import OQAD_K, qad

OUT = D.OUT / "criterion"
BASE_BATCH, MIN_BATCH_MS, MAX_N = 25, 10.0, 2000    # Baseliner batches; traces are replayed up to 2,000 launches
CELL = ["workload", "worksize", "clocks", "setup"]
TRAIN, TEST = (0, 1, 2, 4, 5, 7, 8), (3, 6, 9)       # campaigns (experiment index)
ERROR_PCT, MARGIN_PP, NI_LEVEL, STABLE_PCT, MIN_P = 2.0, 1.0, 95.0, 5.0, 0.80
BUDGETS = (200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 900, 1000, 1250, 1500)
ALPHAS = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00,
          1.10, 1.25, 1.35, 1.50, 1.60, 1.75, 2.00)
WINDOWS = tuple(range(2, 17))
CONDITIONS = ("C0", "C1", "C2")
SUBSETS = tuple(c for r in (3, 2, 1) for c in itertools.combinations(CONDITIONS, r))
SEED, B, OUTER, INNER = 20261107, 2000, 500, 500    # nested bootstrap: OUTER samples, INNER replicates each
# Pair retained for SMS+ among the admissible ones (author's choice: highest P, see RQ-E-3.4)
RETAINED = {"alpha": 0.70, "s": 10}
# Rules frozen on the training campaigns, evaluated on the test campaigns
FROZEN = {"sms+": {"alpha": 0.70, "s": 10, "conditions": CONDITIONS},
          "sms0": {"alpha": 0.25, "s": 10, "conditions": ("C0",)}, "n_max": 600}


# --------------------------------------------------------------------------- #
# Replay of the traces with Baseliner's batches
# --------------------------------------------------------------------------- #
@dataclass
class Series:
    """State at the end of each batch (traces x batches, NaN-padded)."""
    n: np.ndarray    # launches so far
    mb: np.ndarray   # batch median
    mc: np.ndarray   # cumulative median
    rc: np.ndarray   # cumulative RCV_OQAD (%)

    def subset(self, mask):
        return Series(self.n[mask], self.mb[mask], self.mc[mask], self.rc[mask])


def next_batch_size(size: int, duration_ms: float) -> int:
    """Dynamic batching of Baseliner (Benchmark::single_run)."""
    if duration_ms < MIN_BATCH_MS:
        return size * 2
    if duration_ms > MIN_BATCH_MS * 2:
        return size // 2 + 1
    return size


def replay(times: np.ndarray, dynamic: bool) -> np.ndarray:
    """One row per batch up to MAX_N launches: launches, batch median, cumulative median, RCV_OQAD.
    Baseliner's estimators: upper median (element n // 2) and RCV_OQAD in 32-bit floats."""
    rows, start, size = [], 0, BASE_BATCH
    while start < MAX_N and start + size <= len(times):
        end = start + size
        batch, cumul = times[start:end], np.sort(times[:end])
        median = cumul[end // 2]
        rcv = float(np.float32(qad(cumul, median)) / np.float32(median) * np.float32(100.0)) if median > 0 else 100.0
        rows.append((end, np.sort(batch)[size // 2], median, rcv))
        if dynamic:
            size = next_batch_size(size, float(batch.astype(np.float32).sum()))
        start = end
    return np.array(rows)


def _replay_row_group(args) -> tuple[str, np.ndarray]:
    path, i, dynamic = args
    rg = pq.ParquetFile(path).read_row_group(i, columns=["run_id", "time"])
    return rg["run_id"][0].as_py(), replay(rg["time"].to_numpy(), dynamic)


def batch_series(plat: str, run_ids: np.ndarray, dynamic_ids: set) -> Series:
    """Replayed batches of every trace, in the order of run_ids, cached in data/<platform>/batch_series.npz."""
    cache = D.folder(plat) / "batch_series.npz"
    rows = None
    if cache.exists():
        with np.load(cache) as z:
            ids = [str(r) for r in z["run_ids"]]
            if set(ids) == set(map(str, run_ids)):
                rows = dict(zip(ids, np.split(z["rows"][:, :4], z["offsets"][1:-1])))
    if rows is None:
        path = D.folder(plat) / "full_run.parquet"
        jobs = [(str(path), i, rid in dynamic_ids) for i, (rid, _) in enumerate(D.traces(plat, ("run_id",)))]
        print(f"  replaying the batches of {len(jobs)} {plat} traces...")
        with concurrent.futures.ProcessPoolExecutor() as ex:
            results = list(ex.map(_replay_row_group, jobs, chunksize=32))
        np.savez(cache, run_ids=np.array([r for r, _ in results]), rows=np.concatenate([x for _, x in results]),
                 offsets=np.cumsum([0] + [len(x) for _, x in results]))
        rows = dict(results)
    arrays = np.full((4, len(run_ids), max(len(r) for r in rows.values())), np.nan)
    for i, rid in enumerate(run_ids):
        arrays[:, i, :len(rows[str(rid)])] = rows[str(rid)].T
    return Series(*arrays)


def first_batch_reaching(n: np.ndarray, budget: int) -> np.ndarray:
    """Per trace, the first batch reaching the budget (or the last batch)."""
    reached = np.nan_to_num(n, nan=-np.inf) >= budget
    return np.where(reached.any(axis=1), reached.argmax(axis=1), np.sum(~np.isnan(n), axis=1) - 1)


# --------------------------------------------------------------------------- #
# The criterion
# --------------------------------------------------------------------------- #
def conditions(window: np.ndarray, m_c: np.ndarray, tol: np.ndarray) -> np.ndarray:
    """C0, C1, C2 (traces x 3, True when met) on windows of the last S batch medians (traces x S)."""
    scale = 100.0 / np.maximum(1e-12, m_c)
    diffs = np.diff(window, axis=1)
    fc = np.abs(window - m_c[:, None]).mean(axis=1) * scale
    ls = np.abs(diffs).max(axis=1) * scale
    drift = ((diffs[:, 1:] * diffs[:, :-1] > 0) & (np.abs(diffs[:, 1:] + diffs[:, :-1]) * scale[:, None] > tol[:, None])).any(axis=1)
    return np.stack([fc <= tol, ls <= tol, ~drift], axis=1)


def simulate(series: Series, alpha: float, s: int, n_max: int, used=CONDITIONS) -> np.ndarray:
    """Stop batch of each trace. Without any condition, the rule is the fixed budget n_max."""
    last = first_batch_reaching(series.n, n_max)
    if not used:
        return last
    off = ~np.array([c in used for c in CONDITIONS])
    stop, running = last.copy(), np.ones(len(last), dtype=bool)
    for step in range(s - 1, int(last.max()) + 1):
        idx = np.flatnonzero(running & (step <= last))
        if idx.size == 0:
            break
        ok = conditions(series.mb[idx, step - s + 1:step + 1], series.mc[idx, step], alpha * series.rc[idx, step]) | off
        hit = idx[ok.all(axis=1)]
        stop[hit], running[hit] = step, False
    return stop


# --------------------------------------------------------------------------- #
# Platforms, outcomes and bootstrap totals
# --------------------------------------------------------------------------- #
@dataclass
class Context:
    """One platform restricted to some campaigns."""
    meta: pd.DataFrame
    series: Series
    m10k: np.ndarray      # trace median at 10,000 launches
    ref: np.ndarray       # reference median of the failures
    cell: np.ndarray
    workload: np.ndarray

    def outcome(self, step: np.ndarray, n_max: int) -> dict:
        rows = np.arange(len(step))
        n, m = self.series.n[rows, step], self.series.mc[rows, step]
        return {"n": n, "err_self": np.abs(m - self.m10k) / self.m10k * 100.0, "ceiling": n >= n_max}

    def strata(self) -> dict[str, np.ndarray]:
        locked = (self.meta["clocks"] == "locked").values
        return {"verrouillées": locked, "libres": ~locked}


def load_platform(plat: str) -> tuple[pd.DataFrame, Series, np.ndarray]:
    """Metadata, batch series and 10,000-launch median of every trace, in the order of rq3_cumulative."""
    m10k = pq.read_table(D.folder(plat) / "rq3_cumulative.parquet", columns=["run_id", "median"],
                         filters=[("run_ix", "==", D.N_NOMINAL - 1)]).to_pandas()
    meta = D.load(plat).set_index("run_id").loc[m10k["run_id"].values].reset_index()
    dynamic = set(meta.loc[meta["setup"] == "Full", "run_id"])
    return meta, batch_series(plat, meta["run_id"].values, dynamic), m10k["median"].values


def context(platform, campaigns, reference=None) -> Context:
    """Traces of the given campaigns. Reference of a trace: mean 10,000-launch median of its cell over
    the other given campaigns, or over the `reference` campaigns when given (test set)."""
    meta, series, m10k = platform
    keep = meta["experiment"].isin(campaigns).values
    sub, m = meta[keep].reset_index(drop=True), m10k[keep]
    if reference is None:
        g = pd.Series(m).groupby([sub[k] for k in CELL])
        ref = ((g.transform("sum") - m) / (g.transform("count") - 1)).values
    else:
        r = meta["experiment"].isin(reference).values
        means = pd.Series(m10k[r]).groupby([meta.loc[r, k].values for k in CELL]).mean()
        ref = means.reindex(pd.MultiIndex.from_frame(sub[CELL])).values
    return Context(sub, series.subset(keep), m, ref, sub.groupby(CELL).ngroup().values, pd.factorize(sub["workload"])[0])


@dataclass
class Totals:
    """Per workload: traces, launches and failures of each configuration (configs x workloads)."""
    counts: np.ndarray
    n: np.ndarray
    fail: np.ndarray

    def launches(self, w):
        return (w @ self.n.T) / (w @ self.counts)[:, None]

    def failures(self, w):
        return weighted_share(w, self.fail, self.counts)


def totals(ctx: Context, steps: np.ndarray, mask=None) -> Totals:
    mask = np.ones(len(ctx.meta), dtype=bool) if mask is None else mask
    g, k, rows = ctx.workload, int(ctx.workload.max()) + 1, np.arange(len(ctx.meta))
    n, fail = np.zeros((len(steps), k)), np.zeros((len(steps), k))
    for i, step in enumerate(steps):
        err = np.abs(ctx.series.mc[rows, step] - ctx.ref) / ctx.ref * 100.0
        n[i] = np.bincount(g, ctx.series.n[rows, step] * mask, k)
        fail[i] = np.bincount(g, (err > ERROR_PCT) & mask, k)
    return Totals(np.bincount(g, mask, k).astype(float), n, fail)


class Grid:
    """Stop batches of a set of configurations on both platforms, with what the selection needs."""

    def __init__(self, ctxs: dict[str, Context], stable, configs: list[dict]):
        self.configs, self.ctxs = configs, ctxs
        self.steps = {c: np.array([simulate(x.series, **cfg) for cfg in configs], dtype=np.int16) for c, x in ctxs.items()}
        self.whole = {c: totals(x, self.steps[c]) for c, x in ctxs.items()}
        self.constraints = [(name, c, totals(ctxs[c], self.steps[c], mask),
                             totals(ctxs[c], first_batch_reaching(ctxs[c].series.n, 2000)[None, :], mask))
                            for name, c, mask in stable]

    def probability(self, w: dict) -> np.ndarray:
        """P: share of replicates within the margin on every stable stratum, multiplied across platforms."""
        ok = {}
        for _, c, tot, ref in self.constraints:
            inside = tot.failures(w[c]) - ref.failures(w[c]) <= MARGIN_PP
            ok[c] = inside if c not in ok else ok[c] & inside
        return np.prod([m.mean(axis=0) for m in ok.values()], axis=0)

    def cost(self, w: dict) -> np.ndarray:
        """Mean N*, maximum over platforms (replicates x configs)."""
        return np.max([self.whole[c].launches(w[c]) for c in self.ctxs], axis=0)

    def cheapest(self, prob: np.ndarray, w: dict) -> int:
        cost = self.cost(w)[0].astype(float)
        cost[prob < MIN_P] = np.inf
        return int(cost.argmin()) if np.isfinite(cost.min()) else -1

    def frame(self, prob: np.ndarray, point: dict) -> pd.DataFrame:
        df = pd.DataFrame({"alpha": [c["alpha"] for c in self.configs], "S": [c["s"] for c in self.configs]})
        for c in self.ctxs:
            df[f"N* {c}"] = self.whole[c].launches(point[c])[0]
        caps = np.array([c["n_max"] for c in self.configs])[:, None]
        for c, x in self.ctxs.items():
            df[f"Au plafond {c} (%)"] = (x.series.n[np.arange(len(x.meta)), self.steps[c]] >= caps).mean(axis=1) * 100.0
        for name, c, tot, ref in self.constraints:
            df[f"Excès {name} (pp)"] = tot.failures(point[c])[0] - ref.failures(point[c])[0, 0]
        df["N* max"] = df[[f"N* {c}" for c in self.ctxs]].max(axis=1)
        df["P (%)"] = prob * 100.0
        return df


def paired_tests(pairs) -> pd.DataFrame:
    """Wilcoxon + HL of A - B per cell (mean over its campaigns), for N* and the stop error |m* - m_10k| /
    m_10k; hl_moved: HL over the cells where A and B differ. Holm per platform and measure."""
    rows = []
    for label, card, ctx, a_out, b_out in pairs:
        for metric, key in (("N*", "n"), ("Erreur d'arrêt (%)", "err_self")):
            a, b = (pd.Series(o[key]).groupby(ctx.cell).mean().values for o in (a_out, b_out))
            d = np.round(a - b, 10)
            moved = wilcoxon_hl(d[d != 0])
            rows.append({"label": label, "card": card, "metric": metric, **wilcoxon_hl(d),
                         "hl_moved": moved["hl"], "ci_low_moved": moved["ci_low"], "ci_high_moved": moved["ci_high"]})
    df = pd.DataFrame(rows)
    df["p_holm"] = df.groupby(["card", "metric"])["p"].transform(lambda p: pd.Series(holm(p), index=p.index))
    return df


def _near_timer_step(alpha: float) -> bool:
    """alpha within 2 % of a quantization step of the timer (the share of accepted comparisons jumps)."""
    return any(abs(alpha - s) / s <= 0.02 for s in (1.0 / (j * OQAD_K) for j in range(1, 5)))


def _cfg(alpha, s, n_max, used=CONDITIONS) -> dict:
    return {"alpha": alpha, "s": s, "n_max": n_max, "used": used}


# --------------------------------------------------------------------------- #
# Design on the training campaigns (RQ-E-3.3 to 3.5)
# --------------------------------------------------------------------------- #
def design(platforms: dict) -> dict:
    ctxs = {c: context(p, TRAIN) for c, p in platforms.items()}
    rng = np.random.default_rng(SEED)
    w = {c: bootstrap_weights(int(x.workload.max()) + 1, B, rng) for c, x in ctxs.items()}
    point = {c: np.ones((1, v.shape[1])) for c, v in w.items()}
    last_2k = {c: first_batch_reaching(x.series.n, 2000) for c, x in ctxs.items()}

    # 3.3: stable strata (at most 5 % of failures at N = 2,000), then the smallest non-inferior budget
    every, stable, curves = [], [], {}
    for c, x in ctxs.items():
        for label, mask in x.strata().items():
            ref = totals(x, last_2k[c][None, :], mask)
            tot = totals(x, np.array([first_batch_reaching(x.series.n, n) for n in BUDGETS], dtype=np.int16), mask)
            p2000 = float(ref.failures(point[c])[0, 0])
            curves[f"{c} {label}"] = {"card": c, "stable": p2000 <= STABLE_PCT, "p2000": p2000,
                                      "delta": (tot.failures(point[c]) - ref.failures(point[c]))[0],
                                      "u95": np.percentile(tot.failures(w[c]) - ref.failures(w[c]), NI_LEVEL, axis=0)}
            every.append((f"{c} {label}", c, mask))
            if p2000 <= STABLE_PCT:
                stable.append((f"{c} {label}", c, mask))
    admissible = np.all([v["u95"] <= MARGIN_PP for v in curves.values() if v["stable"]], axis=0)
    n_max = BUDGETS[int(np.argmax(admissible))]
    nmax = pd.DataFrame([{"Strate": name, "Plateforme": v["card"], "Stable": v["stable"], "N": n, "p(2000) (%)": v["p2000"],
                          "Delta (pp)": v["delta"][i], "U95 (pp)": v["u95"][i]}
                         for name, v in curves.items() for i, n in enumerate(BUDGETS)])

    # 3.4: joint grid of (alpha, S) for every subset of conditions; nested bootstrap of the selection
    alphas = [a for a in ALPHAS if not _near_timer_step(a)]
    grids, prob, best, frames = {}, {}, {}, {}
    for used in SUBSETS:
        print(f"  grid {' + '.join(used)}")
        grids[used] = Grid(ctxs, stable, [_cfg(a, s, n_max, used) for s in WINDOWS for a in alphas])
        prob[used] = grids[used].probability(w)
        best[used] = grids[used].cheapest(prob[used], point)
        frames[used] = grids[used].frame(prob[used], point)
    boot = selection_bootstrap(grids, w)
    frame = frames[CONDITIONS]
    frontier = []
    for s in WINDOWS:
        sub = frame[frame["S"] == s]
        ok = sub[sub["P (%)"] >= MIN_P * 100.0]
        r = ok.loc[ok["N* max"].idxmin()] if len(ok) else sub.loc[sub["P (%)"].idxmax()]
        frontier.append({"S": s, "alpha": r["alpha"], "Admissible": len(ok) > 0,
                         **{k: r[k] for k in frame.columns if k.startswith(("N* V", "N* M", "Au plafond", "Excès"))}, "P (%)": r["P (%)"]})
    full = grids[CONDITIONS]
    kept = next(i for i, c in enumerate(full.configs) if np.isclose(c["alpha"], RETAINED["alpha"]) and c["s"] == RETAINED["s"])
    if prob[CONDITIONS][kept] < MIN_P:
        raise SystemExit("the retained (alpha, S) is not admissible")
    kw = full.configs[kept]
    pairs = []
    for c, x in ctxs.items():
        rule = x.outcome(full.steps[c][kept], n_max)
        pairs.append((f"règle - N fixe = {n_max}", c, x, rule, x.outcome(first_batch_reaching(x.series.n, n_max), n_max)))
        pairs.append(("règle - N fixe = 2 000", c, x, rule, x.outcome(last_2k[c], 2000)))
    rule_paired = paired_tests(pairs)

    # 3.5: the 7 subsets and the fixed budget at the retained (alpha, S)
    arms = [_cfg(kw["alpha"], kw["s"], n_max, used) for used in SUBSETS] + [_cfg(kw["alpha"], kw["s"], n_max, ())]
    steps = {c: np.array([simulate(x.series, **a) for a in arms], dtype=np.int16) for c, x in ctxs.items()}
    factorial = pd.DataFrame({"Clé": ["+".join(u) for u in SUBSETS] + ["aucune"]})
    for c, x in ctxs.items():
        outs = [x.outcome(st, n_max) for st in steps[c]]
        factorial[f"N* {c}"] = [float(o["n"].mean()) for o in outs]
        factorial[f"Au plafond {c} (%)"] = [float(o["ceiling"].mean() * 100.0) for o in outs]
    within = {}
    for name, c, mask in stable:
        x = ctxs[c]
        tot, ref = totals(x, steps[c], mask), totals(x, last_2k[c][None, :], mask)
        factorial[f"Excès {name} (pp)"] = tot.failures(point[c])[0] - ref.failures(point[c])[0, 0]
        inside = tot.failures(w[c]) - ref.failures(w[c]) <= MARGIN_PP
        within[c] = inside if c not in within else within[c] & inside
    factorial["P (%)"] = np.prod([m.mean(axis=0) for m in within.values()], axis=0) * 100.0

    # Reduced rules re-tuned at their own optimum: extra cost against SMS+ on the same bootstrap samples
    full_cost = np.where(np.isinf(boot[CONDITIONS]["cost"]), np.inf, boot[CONDITIONS]["costs"][:, kept])
    components = []
    for j in CONDITIONS:
        row = {"Composante": j}
        for prefix, used in (("Sans elle", tuple(c for c in CONDITIONS if c != j)), ("Seule", (j,))):
            b, fr = best[used], frames[used]
            with np.errstate(invalid="ignore"):
                gap = np.where(np.isinf(boot[used]["cost"]) & np.isinf(full_cost), np.nan, boot[used]["cost"] - full_cost)
            finite = gap[~np.isnan(gap)]
            low, high = np.percentile(finite, [2.5, 97.5], method="nearest") if finite.size else (np.nan, np.nan)
            row.update({f"{prefix}, alpha": grids[used].configs[b]["alpha"], f"{prefix}, S": grids[used].configs[b]["s"],
                        f"{prefix}, surcoût": float(fr.loc[b, "N* max"] - frame.loc[kept, "N* max"]),
                        f"{prefix}, IC bas": low, f"{prefix}, IC haut": high,
                        **{f"{prefix}, Excès {name} (pp)": float(fr.loc[b, f"Excès {name} (pp)"]) for name, _, _ in stable}})
        components.append(row)

    decisions = {"stable": [name for name, _, _ in stable], "n_max": n_max, "alpha": kw["alpha"], "s": kw["s"],
                 "c0_only": {"alpha": grids[("C0",)].configs[best[("C0",)]]["alpha"], "s": grids[("C0",)].configs[best[("C0",)]]["s"]},
                 "train_campaigns": list(TRAIN), "test_campaigns": list(TEST)}
    return {"decisions": decisions, "nmax": nmax, "frontier": pd.DataFrame(frontier), "rule_paired": rule_paired,
            "factorial": factorial, "components": pd.DataFrame(components)}


def selection_bootstrap(grids: dict, w: dict) -> dict:
    """The selection redone on OUTER workload samples, the same for every grid: in each sample, P comes
    from INNER replicates drawn inside it, and the cheapest admissible configuration is kept (cost +inf
    when none is admissible). The cost of every configuration in every sample is kept too."""
    rng = np.random.default_rng([SEED, 2])
    outer = {c: bootstrap_weights(w[c].shape[1], OUTER, rng) for c in w}
    result = {}
    for used, grid in grids.items():
        cost, costs = np.full(OUTER, np.inf), np.empty((OUTER, len(grid.configs)))
        for o in range(OUTER):
            r = np.random.default_rng([SEED, 3, o])
            inner = {c: r.multinomial(int(outer[c][o].sum()), outer[c][o] / outer[c][o].sum(), size=INNER).astype(float) for c in w}
            sample = {c: outer[c][[o]] for c in w}
            costs[o] = grid.cost(sample)[0]
            b = grid.cheapest(grid.probability(inner), sample)
            if b >= 0:
                cost[o] = costs[o, b]
        result[used] = {"cost": cost, "costs": costs}
    return result


# --------------------------------------------------------------------------- #
# Frozen rules on the test campaigns (RQ-E-3.6)
# --------------------------------------------------------------------------- #
def test(platforms: dict) -> dict:
    ctxs = {c: context(p, TEST, reference=TRAIN) for c, p in platforms.items()}
    rng = np.random.default_rng(SEED + 1)
    w = {c: bootstrap_weights(int(x.workload.max()) + 1, B, rng) for c, x in ctxs.items()}
    point = {c: np.ones((1, v.shape[1])) for c, v in w.items()}
    n_max = FROZEN["n_max"]
    rules = {"figee": _cfg(FROZEN["sms+"]["alpha"], FROZEN["sms+"]["s"], n_max, FROZEN["sms+"]["conditions"]),
             "c0": _cfg(FROZEN["sms0"]["alpha"], FROZEN["sms0"]["s"], n_max, FROZEN["sms0"]["conditions"]),
             "fixe_nmax": _cfg(0, 2, n_max, ()), "fixe_2000": _cfg(0, 2, 2000, ())}
    keys = list(rules)
    steps = {c: np.array([simulate(x.series, **r) for r in rules.values()], dtype=np.int16) for c, x in ctxs.items()}
    outs = {c: [x.outcome(st, r["n_max"]) for st, r in zip(steps[c], rules.values())] for c, x in ctxs.items()}
    export = [{"Clé": k, **{f"N* {c}": float(outs[c][i]["n"].mean()) for c in ctxs}} for i, k in enumerate(keys)]
    for c, x in ctxs.items():
        for label, mask in x.strata().items():
            name, tot = f"{c} {label}", totals(x, steps[c], mask)
            boot, fail = tot.failures(w[c]), tot.failures(point[c])[0]
            excess = boot - boot[:, [keys.index("fixe_2000")]]
            for i, row in enumerate(export):
                gap_low, gap_high = np.percentile(boot[:, 0] - boot[:, i], [2.5, 97.5])
                row.update({f"Excès {name} (pp)": float(fail[i] - fail[-1]), f"U95 {name} (pp)": float(np.percentile(excess[:, i], NI_LEVEL)),
                            f"Échecs {name} (%)": float(fail[i]), f"Figée moins règle {name} (pp)": float(fail[0] - fail[i]),
                            f"Figée moins règle {name} IC bas": float(gap_low), f"Figée moins règle {name} IC haut": float(gap_high)})
    paired = paired_tests([(label, c, x, outs[c][0], outs[c][keys.index(b)]) for label, b in
                           (("figée - C0 seule", "c0"), (f"figée - N fixe = {n_max}", "fixe_nmax")) for c, x in ctxs.items()])
    return {"test": pd.DataFrame(export), "test_paired": paired}


def run() -> dict:
    platforms = {c: load_platform(c) for c in D.PLATFORMS}
    print("RQ-E-3.3 to 3.5: design on the training campaigns")
    res = design(platforms)
    print("RQ-E-3.6: frozen rules on the test campaigns")
    res.update(test(platforms))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in res.items():
        if name == "decisions":
            (OUT / "decisions.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            value.to_csv(OUT / f"{name}.csv", index=False)
    print(f"  {OUT}/")
    return res


def load() -> dict:
    """The values written by run()."""
    res = {p.stem: pd.read_csv(p) for p in OUT.glob("*.csv")}
    res["decisions"] = json.loads((OUT / "decisions.json").read_text(encoding="utf-8"))
    return res
