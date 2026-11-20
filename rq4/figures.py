"""Figures of RQ-E-4, one PDF per platform: outputs/figures/rq-e-4_<rq>_<name>_<platform>.pdf.

RQ-E-4.6 compares the SMS experiment with the main corpus of the same platform (rq1_rq3/data/).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import seaborn as sns

from common import plots as P
from common.stats import tukey_summary
from rq1_rq3 import data as corpus
from rq4 import data as D

EM_DASH = "|"     # cmr10 (OT1 encoding) draws the em dash at '|'
LABELS = {"sms": "SMS+", "sms-c0": r"SMS$_0$", "fixed-600": r"$N \geq 600$", "fixed-2000": r"$N \geq 2\,000$",
          "primbench": "PrimBench", "nvbench-stdrel": r"NVBench $\mathtt{stdrel}$", "nvbench-entropy": r"NVBench $\mathtt{entropy}$"}
COLORS = P.STRATEGY_COLORS
SERIES = {"corpus": ("Corpus principal (statistiques de base)", P.CORPUS_COLOR),
          "sms": (r"Experience SMS, $N \geq 2\,000$ (statistiques SMS)", COLORS[D.REFERENCE])}
EARLY, LATE = (200, 400), (1500, 2000)     # acceleration = m(1,500-2,000) / m(200-400) - 1
LAUNCHES, BATCH = 2000, 25


def _pct(v: float) -> str:
    return EM_DASH if not np.isfinite(v) else f"{v:.1f}".replace(".", ",") + " %"


def _thousands(v, _pos=None) -> str:
    return f"${v:,.0f}$".replace(",", r"\,")


def _log_bounds(v, margin: float = 0.06):
    lo, hi = np.log10(np.nanmin(v)), np.log10(np.nanmax(v))
    return 10 ** (lo - (hi - lo) * margin), 10 ** (hi + (hi - lo) * margin)


def cost(c: pd.DataFrame, t: pd.DataFrame, xlim, xlim_time):
    """RQ-E-4.1: N* per cell (boxes, log x) with the share of traces at the cap, and the wall time of one
    campaign (sum over the cells of their median wall time)."""
    order = list(D.STRATEGIES)
    ceiling = {s: c.loc[c["critere"] == s, "part_plafond"].mean() * 100 if s in D.DYNAMIC else np.nan for s in order}
    wall = {s: c.loc[c["critere"] == s, "t_cpu_ms"].sum() / 1000 for s in order}
    fig, (ax, ax_t) = plt.subplots(1, 2, figsize=(9.6, 3.5), sharey=True, width_ratios=(3, 2))
    P.boxplot(ax, c[["critere", "n_star"]], "n_star", "critere", hue="critere", order=order, hue_order=order, palette=COLORS,
              legend=False, log_scale=True)
    pos = np.arange(len(order))
    ax.set_xlim(*xlim)
    ax.set_yticks(pos, [LABELS[s] for s in order], fontsize=9)
    ax.set_ylabel("")
    ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel(r"Nombre d'executions a l'arret $N^*$ (cellules, echelle log)", fontsize=9.5)
    margin = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    for y, s in zip(pos, order):
        ax.text(1.03, y, _pct(ceiling[s]), transform=margin, ha="left", va="center", fontsize=9)
    ax.text(1.03, 1.01, "Au plafond", transform=ax.transAxes, ha="left", va="bottom", fontsize=9)
    boxes = ax.patches[:len(order)]      # same fill and edge as the boxes
    ax_t.set_xscale("log")
    ax_t.barh(pos, [wall[s] - xlim_time[0] for s in order], left=xlim_time[0], height=0.8, color=[b.get_facecolor() for b in boxes],
              edgecolor=P.EDGE, linewidth=boxes[0].get_linewidth())
    ax_t.set_xlim(*xlim_time)
    for a in (ax, ax_t):
        a.xaxis.set_major_formatter(ticker.FuncFormatter(_thousands))
    ax_t.tick_params(axis="x", labelsize=9)
    ax_t.tick_params(axis="y", length=0)
    ax_t.set_xlabel("Temps mur cumule sur une campagne (s, echelle log)", fontsize=9.5)
    fig.tight_layout()
    return ax


def failures(t: pd.DataFrame, xlim):
    """RQ-E-4.2: share of failed traces per strategy, one panel per clock regime."""
    order = list(D.STRATEGIES)
    faces = [P.fill(COLORS[s]) for s in order]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5), sharex=True, sharey=True)
    pos = np.arange(len(order))
    for ax, h in zip(axes, ("unlocked", "locked")):
        share = t[t["horloges"] == h].groupby("critere")["echec"].mean() * 100
        ax.barh(pos, [share[s] for s in order], height=0.8, color=faces, edgecolor=P.EDGE,
                linewidth=plt.rcParams["patch.linewidth"])
        ax.set_xlim(*xlim)
        ax.tick_params(axis="x", labelsize=9)
        ax.tick_params(axis="y", length=0)
        ax.set_title(P.CLOCK_LABELS[h], fontsize=9.5)
    axes[0].set_yticks(pos, [LABELS[s] for s in order], fontsize=9)
    axes[0].set_ylim(len(order) - 0.5, -0.5)
    fig.supxlabel("Part des traces en echec (%)", fontsize=9.5)
    fig.tight_layout()
    return axes


# --------------------------------------------------------------------------- #
# RQ-E-4.6: SMS experiment vs main corpus
# --------------------------------------------------------------------------- #
def corpus_traces(plat: str) -> pd.DataFrame:
    """Main corpus traces, cell keys renamed as in D.CELL, with the medians of launches 0-2,000 and of
    the acceleration windows."""
    pp = corpus.load(plat)[["run_id", "clocks", "setup", "workload", "worksize"]]
    pp = pp.rename(columns={"clocks": "horloges", "worksize": "work_size"}).assign(harnais=pp["setup"].str.lower())
    rows = []
    for rid, rg in corpus.traces(plat, ("run_id", "run_ix", "time")):
        ix, tm = rg["run_ix"].to_numpy(), rg["time"].to_numpy()
        rows.append((rid, np.median(tm[ix < LAUNCHES]), np.median(tm[(ix >= EARLY[0]) & (ix < EARLY[1])]),
                     np.median(tm[(ix >= LATE[0]) & (ix < LATE[1])])))
    return pp.merge(pd.DataFrame(rows, columns=["run_id", "m_0_2000", "m_200_400", "m_1500_2000"]), on="run_id")


def acceleration(series: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per (series, cell): medians over the campaigns of m(0-2,000) and of the acceleration (%)."""
    both = pd.concat([df.assign(serie=name) for name, df in series.items()], ignore_index=True)
    both["acceleration_pct"] = (both["m_1500_2000"] / both["m_200_400"] - 1) * 100
    return both.groupby(["serie", *D.CELL]).agg(median_ms=("m_0_2000", "median"), acceleration_pct=("acceleration_pct", "median")).reset_index()


def acceleration_plot(points: pd.DataFrame, xlim):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    labels = {k: lab for k, (lab, _) in SERIES.items()}
    P.scatter(ax, points.assign(serie=points["serie"].map(labels)), "median_ms", "acceleration_pct", "serie",
              [lab for lab, _ in SERIES.values()], {lab: col for lab, col in SERIES.values()}, s=12, xscale="log", hline=0)
    ax.set_xlim(*xlim)
    ticks = [k * 10.0 ** e for e in range(int(np.floor(np.log10(xlim[0]))), int(np.ceil(np.log10(xlim[1]))) + 1)
             for k in (1, 2, 5) if xlim[0] <= k * 10.0 ** e <= xlim[1]]
    ax.xaxis.set_major_locator(ticker.FixedLocator(ticks))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _pos: f"{v:g}"))
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.tick_params(axis="both", labelsize=9)
    ax.set_xlabel("Temps median de la cellule (ms, echelle log)", fontsize=9.5)
    window = lambda a, b: "$-$".join(f"{v:,}".replace(",", r"\,") for v in (a, b))  # noqa: E731
    ax.set_ylabel(rf"Acceleration $m({window(*LATE)})\,/\,m({window(*EARLY)}) - 1$ (%)", fontsize=9.5)
    sns.move_legend(ax, "upper right", title=None, fontsize=8.5)
    fig.tight_layout()
    return ax


def _loo(df: pd.DataFrame, col: str) -> pd.Series:
    """Mean of col over the other traces of the same cell."""
    g = df.groupby(D.CELL)[col]
    return (g.transform("sum") - df[col]) / (g.transform("count") - 1)


def batch_evolution(plat: str, sms: pd.DataFrame, cor: pd.DataFrame):
    """Like RQ-E-3.1 over 2,000 launches: median of each batch of 25 / reference (%), the reference being
    the mean m(0-2,000) of the other campaigns of the cell; N >= 2,000 traces of the SMS experiment vs
    the main corpus, all cells."""
    b = pd.read_csv(D.folder(plat) / "batches.csv")
    ref = _loo(sms, "m_0_2000").set_axis(sms["trace_id"])
    lots = {"sms": b.assign(val=b["median_ms"] / b["trace_id"].map(ref) * 100).pivot(index="trace_id", columns="batch", values="val")}
    cb = pq.read_table(corpus.folder(plat) / "rq3_per_batch.parquet", columns=["run_id", "batch_ix", "median"],
                       filters=[("batch_ix", "<", LAUNCHES // BATCH)]).to_pandas()
    ref = _loo(cor, "m_0_2000").set_axis(cor["run_id"])
    lots["corpus"] = cb.assign(val=cb["median"] / cb["run_id"].map(ref) * 100).pivot(index="run_id", columns="batch_ix", values="val")
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    P.reference(ax, 100.0)
    x = (np.arange(LAUNCHES // BATCH) + 1) * BATCH
    for key, (label, color) in SERIES.items():
        s = tukey_summary(lots[key].to_numpy())
        ax.plot(x, s["median"], color=color, linewidth=1.8, label=label)
        ax.fill_between(x, s["q25"], s["q75"], color=color, alpha=0.18)
        ax.plot(x, s["w_high"], color=color, linestyle="--", linewidth=0.85, alpha=0.65)
        ax.plot(x, s["w_low"], color=color, linestyle="--", linewidth=0.85, alpha=0.65)
    ax.set_xlim(0, 2010)
    ax.set_xticks((0, 500, 1000, 1500, 2000), ["0", "500", "1000", "1500", "2000"], fontsize=9.5)
    ax.tick_params(axis="y", labelsize=9.5)
    ax.set_ylim(92.5, 105.0)
    P.grid(ax)
    ax.set_xlabel(r"Budget cumulatif $N$ (lancements)", fontsize=10.5)
    ax.set_ylabel("Mediane par lot relative (%)", fontsize=10.5)
    ax.legend(fontsize=8.5, loc="lower center", framealpha=0.92)
    fig.tight_layout()
    return ax


def make_all(pfs: dict, out) -> None:
    """pfs: {platform: (traces, cells)}. Axes are shared by all platforms."""
    xlim = _log_bounds(pd.concat([c["n_star"] for _, c in pfs.values()]))
    walls = [c.groupby("critere")["t_cpu_ms"].sum().values / 1000 for _, c in pfs.values()]
    lo, hi = np.floor(np.log10(np.min(walls))), np.log10(np.max(walls))
    xlim_time = (10 ** lo, 10 ** (hi + (hi - lo) * 0.06))
    xlim_fail = (0.0, max(t.groupby(["horloges", "critere"])["echec"].mean().max() * 100 for t, _ in pfs.values()) * 1.06)
    accel = {}
    for plat, (t, _) in pfs.items():
        if (corpus.folder(plat) / "full_run.parquet").exists():
            cor = corpus_traces(plat)
            sms = t[t["critere"] == D.REFERENCE]
            accel[plat] = (acceleration({"sms": sms, "corpus": cor}), sms, cor)
    xlim_accel = _log_bounds(pd.concat([a["median_ms"] for a, _, _ in accel.values()])) if accel else None
    for plat, (t, c) in pfs.items():
        s = plat.lower()
        P.save(cost(c, t, xlim, xlim_time), out / f"rq-e-4_1_cout_{s}.pdf")
        P.save(failures(t, xlim_fail), out / f"rq-e-4_2_echecs_{s}.pdf")
        if plat in accel:
            points, sms, cor = accel[plat]
            P.save(batch_evolution(plat, sms, cor), out / f"rq-e-4_6_batch_evolution_sms_corpus_{s}.pdf")
            P.save(acceleration_plot(points, xlim_accel), out / f"rq-e-4_6_acceleration_sms_corpus_{s}.pdf")
