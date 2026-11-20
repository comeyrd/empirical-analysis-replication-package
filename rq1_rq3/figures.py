"""Figures of RQ-E-1 to RQ-E-3, one PDF per platform: outputs/figures/rq-e-<rq>_<name>_<platform>.pdf."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from common import plots as P
from common.stats import tukey_summary
from rq1_rq3 import data as D

LABEL_P = r"Marge au plancher $\mathcal{P}$ (%)"
LABEL_C = r"Marge au coude $\mathcal{C}$ (%)"
LABEL_T = r"Traine superieure $\mathcal{T}$ (%)"
DISPERSION = {"cv": r"\mathrm{CV}", "RCV_MAD": r"\mathrm{RCV}_{\mathrm{MAD}}", "RCV_IQR": r"\mathrm{RCV}_{\mathrm{IQR}}",
              "RCV_QAD": r"\mathrm{RCV}_{\mathrm{OQAD}}"}
ECDF_TRACE = {"workload": "Gemms", "experiment": 2, "setup": "Full", "clocks": "locked", "worksizes": (8, 512)}


def _label(ax, label: str) -> None:
    ax.set_xlabel(P.LABEL_WORKSIZE, fontsize=11)
    ax.set_ylabel(label, fontsize=11)
    ax.set_title(label, fontsize=11)


def _worksizes(df):
    ws = sorted(df["worksize"].unique())
    return ws, P.worksize_palette(ws)


def ecdf_gemms(plat: str, df: pd.DataFrame):
    """RQ-E-1.2: ECDF of one trace at the smallest and largest work size, with the P, C, T regions."""
    sel = ECDF_TRACE
    fig, axes = plt.subplots(1, len(sel["worksizes"]), figsize=(11.5, 4.5))
    rows = df[(df["workload"] == sel["workload"]) & (df["clocks"] == sel["clocks"]) & (df["setup"] == sel["setup"])
              & (df["experiment"] == sel["experiment"])].set_index("worksize")
    times = D.trace_times(plat, [rows.loc[ws, "run_id"] for ws in sel["worksizes"]])
    for ax, ws in zip(axes, sel["worksizes"]):
        row = rows.loc[ws]
        t = times[row["run_id"]]
        med, knee, t_min = float(row["median"]), float(row["median"] + row["bulk_horizon_abs"]), float(t.min())
        P.ecdf(ax, t, linewidth=2.0)
        x_right = max(knee + (knee - t_min) * 0.40, float(np.percentile(t, 99)) * 1.002)
        span = x_right - t_min
        xlim = (t_min - span * 0.06, x_right + span * 0.06)
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.02, 1.02)
        region = P.REGION_COLORS
        ax.axvspan(t_min, med, color=region["P"], alpha=0.18, label=r"$\mathcal{P}$")
        ax.axvspan(med, knee, color=region["C"], alpha=0.18, label=r"$\mathcal{C}$")
        ax.axvspan(knee, xlim[1] * 2, color=region["T"], alpha=0.18, label=r"$\mathcal{T}$")
        ax.axvline(t_min, color=region["P"], linestyle=":", linewidth=1.6, alpha=0.85)
        ax.axvline(med, color=P.INK, linestyle="--", linewidth=1.6, alpha=0.85)
        ax.axvline(knee, color=region["T"], linestyle="-.", linewidth=1.6, alpha=0.85)
        ax.set_xlabel("Temps d'execution (ms)", fontsize=11)
        ax.set_ylabel("Probabilite cumulee", fontsize=11)
        ax.set_title(f"{P.LABEL_WORKSIZE} {ws}", fontsize=12)
        ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
    fig.tight_layout()
    return axes


def geometry(df: pd.DataFrame):
    """RQ-E-1.2: P, C and T per work size, one value per trace."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    ws, pal = _worksizes(df)
    for ax, (col, label) in zip(axes, (("floor_gap_rel", LABEL_P), ("bulk_horizon_rel", LABEL_C), ("tail_mass_rel", LABEL_T))):
        P.boxplot(ax, df, "worksize", col, order=ws, palette=pal)
        _label(ax, label)
    fig.tight_layout()
    return axes


def location_estimators(df: pd.DataFrame):
    """RQ-E-1.4: Delta mu and Delta m per cell (% of the median), bias beta = (mu - m) / m per trace."""
    drift = D.cell_drift(df, {"delta_mean_rel": "mean", "delta_median_rel": "median"}, relative_to="median")
    trace = df.assign(beta=(df["mean"] - df["median"]) / df["median"] * 100.0)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    ws, pal = _worksizes(trace)
    panels = [(drift, "delta_mean_rel", r"$\Delta \mu$ (% de $\bar{m}$)"),
              (drift, "delta_median_rel", r"$\Delta m$ (% de $\bar{m}$)"), (trace, "beta", r"$\beta_{\mu - m}$ (%)")]
    for ax, (d, col, label) in zip(axes, panels):
        P.boxplot(ax, d, "worksize", col, order=ws, palette=pal, hline=0.0)
        _label(ax, label)
    fig.tight_layout()
    return axes


def dispersion_estimators(df: pd.DataFrame):
    """RQ-E-1.5: CV and the three robust RCVs (%) per work size, one value per trace."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
    ws, pal = _worksizes(df)
    for i, (ax, (key, tex)) in enumerate(zip(axes, DISPERSION.items())):
        P.boxplot(ax, df, "worksize", f"{key}_rel", order=ws, palette=pal)
        ax.set_xlabel(P.LABEL_WORKSIZE, fontsize=11)
        ax.set_title(f"${tex}$", fontsize=11)
        ax.set_ylabel("Dispersion relative (%)" if i == 0 else "", fontsize=11)
    return axes


def dispersion_drift(df: pd.DataFrame):
    """RQ-E-1.5: inter-campaign drift Delta X (pp) of the four dispersion estimators, one value per cell."""
    drift = D.cell_drift(df, {k: f"{k}_rel" for k in DISPERSION})
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
    ws, pal = _worksizes(drift)
    for i, (ax, (key, tex)) in enumerate(zip(axes, DISPERSION.items())):
        P.boxplot(ax, drift, "worksize", key, order=ws, palette=pal)
        ax.set_xlabel(P.LABEL_WORKSIZE, fontsize=11)
        ax.set_title(rf"$\Delta {tex}$", fontsize=11)
        ax.set_ylabel("Ecart inter-campagnes (pp)" if i == 0 else "", fontsize=11)
    return axes


def degeneration(df: pd.DataFrame):
    """RQ-E-1.6: share of traces whose MAD, IQR or OQAD is exactly 0, per work size."""
    rates = pd.DataFrame({"worksize": df["worksize"], "MAD": df["mad"] == 0, "IQR": df["IQR"] == 0, "OQAD": df["QAD"] == 0})
    rates = (rates.groupby("worksize").mean() * 100.0).reset_index().melt(
        id_vars="worksize", var_name="estimator", value_name="failure_rate")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(data=rates, x="worksize", y="failure_rate", hue="estimator", palette=P.ESTIMATOR_COLORS,
                saturation=P.SATURATION, edgecolor=P.EDGE, linewidth=plt.rcParams["patch.linewidth"], ax=ax)
    ax.set_xlabel(P.LABEL_WORKSIZE, fontsize=11)
    ax.set_ylabel("Taux de degenerescence (%)", fontsize=11)
    ax.set_ylim(0, 100)
    P.grid(ax, axis="y")
    ax.legend(title="Estimateur de dispersion", loc="upper right")
    return ax


def factor(df: pd.DataFrame, fac: str, palette: dict, levels: dict, legend_title: str, delta_label: str):
    """RQ-E-2.1 and 2.2: P, delta_f m (one value per pair of cells), C and T, per level of the factor."""
    a, b = D.FACTOR_LEVELS[fac]
    effect = D.factor_effect(df, fac, {"delta_m": "median"}, relative=("delta_m",))
    ws = sorted(df["worksize"].unique())
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.5))
    for i, (col, label) in {0: ("floor_gap_rel", LABEL_P), 2: ("bulk_horizon_rel", LABEL_C), 3: ("tail_mass_rel", LABEL_T)}.items():
        P.boxplot(axes[i], df, "worksize", col, hue=fac, order=ws, hue_order=[a, b], palette=palette)
        _label(axes[i], label)
        handles, labels = axes[i].get_legend_handles_labels()
        axes[i].legend(handles, [levels[lab] for lab in labels], title=legend_title, loc="upper right")
    P.boxplot(axes[1], effect, "worksize", "delta_m", order=ws, palette=[palette[b]] * len(ws), hline=0.0)
    _label(axes[1], delta_label)
    fig.tight_layout()
    return axes


def _curves(ax, summary: dict, x, color: str, label: str, alpha_band: float, lw_whisker: float, alpha_whisker: float):
    ax.plot(x, summary["median"], color=color, linewidth=1.8, label=label)
    ax.fill_between(x, summary["q25"], summary["q75"], color=color, alpha=alpha_band)
    ax.plot(x, summary["w_high"], color=color, linestyle="--", linewidth=lw_whisker, alpha=alpha_whisker)
    ax.plot(x, summary["w_low"], color=color, linestyle="--", linewidth=lw_whisker, alpha=alpha_whisker)


def _log_x(ax) -> None:
    ax.set_xscale("log")
    ax.set_xlim(22, 10500)
    ax.set_xticks([25, 100, 500, 2500, 5000, 10000])
    ax.set_xticklabels(["25", "100", "500", "2500", "5000", "10000"], fontsize=9.5)


def _configs(meta: pd.DataFrame):
    for setup, clocks, label in D.CONFIGS:
        yield label, P.CONFIG_COLORS[(setup, clocks)], ((meta["setup"] == setup) & (meta["clocks"] == clocks)).values


def batch_evolution(plat: str, df: pd.DataFrame):
    """RQ-E-3.1: median of each batch of 25 launches / leave-one-out reference at 10,000 launches (%)."""
    mats, meta = D.evolution(plat, df, "rq3_per_batch.parquet", ["median"])
    vals = mats["median"] / np.abs(mats["ref"])[:, None] * 100.0
    x = (np.arange(vals.shape[1]) + 1) * D.STEP
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for label, color, mask in _configs(meta):
        _curves(ax, tukey_summary(vals[mask]), x, color, label, 0.18, 0.85, 0.65)
    _log_x(ax)
    ax.set_ylim(85, 110)
    P.grid(ax, which="both")
    ax.set_xlabel(r"Budget cumulatif $N$ (lancements)", fontsize=10.5)
    ax.set_ylabel(r"Mediane par lot relative(%)", fontsize=10.5)
    ax.legend(title="Configuration", fontsize=8.5, title_fontsize=9, loc="lower right", framealpha=0.92)
    fig.tight_layout()
    return ax


def convergence_profiles(plat: str, df: pd.DataFrame):
    """RQ-E-3.2: with N, error of the cumulative median to the leave-one-out reference at 10,000 (%),
    cumulative RCV_OQAD (%), and inter-campaign drift of the cumulative median Delta m (%)."""
    mats, meta = D.evolution(plat, df, "rq3_cumulative.parquet", ["median", "RCVOQAD"])
    med, ref = mats["median"], mats["ref"]
    cell = pd.factorize(meta[D.CELL].apply(tuple, axis=1))[0]
    sums, counts = np.zeros((cell.max() + 1, med.shape[1])), np.zeros((cell.max() + 1, 1))
    np.add.at(sums, cell, med)
    np.add.at(counts, cell, 1)
    loo = np.where(counts[cell] > 1, (sums[cell] - med) / (counts[cell] - 1), med)
    panels = {
        "median": (np.abs(med - ref[:, None]) / np.where(np.abs(ref) > 1e-12, np.abs(ref), 1.0)[:, None] * 100.0,
                   r"Erreur Relative LOO ($m$)", r"Erreur relative LOO $\frac{|m - \bar{m}_{\backslash k}|}{\bar{m}_{\backslash k}}$ (%)", 0.01),
        "RCVOQAD": (mats["RCVOQAD"], r"Dispersion ($\mathrm{RCV}_{\mathrm{OQAD}}$)", r"Dispersion $\mathrm{RCV}_{\mathrm{OQAD}}$ (%)", 0.1),
        "delta_m": (np.abs(med - loo) / np.where(np.abs(loo) > 1e-12, np.abs(loo), 1.0) * 100.0,
                    r"Reproductibilite LOO ($\Delta m$)", r"Derive LOO $\Delta m$ (%)", 0.01),
    }
    x = (np.arange(med.shape[1]) + 1) * D.STEP
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 3.8))
    for i, (ax, (err, title, ylabel, linthresh)) in enumerate(zip(axes, panels.values())):
        summaries = {(label, color): tukey_summary(err[mask], low_floor=0.0) for label, color, mask in _configs(meta)}
        for (label, color), s in summaries.items():
            _curves(ax, s, x, color, label, 0.22, 0.9, 0.75)
        _log_x(ax)
        ax.set_yscale("symlog", linthresh=linthresh, linscale=1.0)
        ax.set_ylim(-linthresh * 0.4, max(np.nanmax(s["w_high"]) for s in summaries.values()) * 1.35)
        ax.axhline(0, color=P.INK, linestyle="-", linewidth=0.6, alpha=0.5)
        P.grid(ax, which="both")
        ax.set_xlabel(r"Budget $N$ (lancements)", fontsize=10.5)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11)
        if i == 0:
            ax.legend(title="Configuration", fontsize=8.2, title_fontsize=8.5, loc="upper right", framealpha=0.92)
    fig.tight_layout()
    return axes


def make_all(plat: str, out) -> None:
    df = D.load(plat)
    s = plat.lower()
    figures = {
        f"rq-e-1_2_ecdf_gemms_{s}": lambda: ecdf_gemms(plat, df),
        f"rq-e-1_2_geometry_{s}": lambda: geometry(df),
        f"rq-e-1_4_estimateur_loc_{s}": lambda: location_estimators(df),
        f"rq-e-1_5_estimateur_disp_{s}": lambda: dispersion_estimators(df),
        f"rq-e-1_5_disp_delta_{s}": lambda: dispersion_drift(df),
        f"rq-e-2_1_clocks_{s}": lambda: factor(df, "clocks", P.CLOCK_COLORS, P.CLOCK_LABELS,
                                               "Regime d'horloge", r"$\delta_{\mathrm{clk}}m$ (%)"),
        f"rq-e-2_2_setup_{s}": lambda: factor(df, "setup", P.HARNESS_COLORS,
                                              {"Minimal": "Minimal", "Full": "Complet"}, "Recette", r"$\delta_{\mathrm{harn}}m$ (%)"),
        f"rq-e-3_batch_evolution_{s}": lambda: batch_evolution(plat, df),
        f"rq-e-3_convergence_profiles_{s}": lambda: convergence_profiles(plat, df),
    }
    if plat == "V100":     # the thesis shows the V100 degeneration only: MI210 never degenerates
        figures[f"rq-e-1_6_degeneration_{s}"] = lambda: degeneration(df)
    for name, build in figures.items():
        P.save(build(), out / f"{name}.pdf")
