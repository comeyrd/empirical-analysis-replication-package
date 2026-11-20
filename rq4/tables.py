"""Tables of RQ-E-4 in LaTeX, named and laid out as in the thesis (outputs/tables/*.tex)."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from common import latex as L
from common.stats import holm, resamples, spearman_boot, wilcoxon_hl
from rq4 import data as D

CORRELATIONS = {"bruit": ("bruit_rcv_oqad", "n_star"), "bruit_sans_plafond": ("bruit_rcv_oqad", "hors_plafond"),
                "duree": ("duree_ms", "n_star")}


def n_star_below_cap(t: pd.DataFrame, c: pd.DataFrame, strategy: str) -> np.ndarray:
    """N* of each cell of c over its traces stopped before the cap only (NaN when all reached it)."""
    s = t[(t["critere"] == strategy) & ~t["au_plafond"]].groupby(D.CELL, as_index=False)["n_star"].median()
    return c[D.CELL].merge(s, on=D.CELL, how="left", validate="one_to_one")["n_star"].to_numpy(float)


def adaptation(t: pd.DataFrame, c: pd.DataFrame) -> dict:
    """Spearman rho, per dynamic strategy, of N* with the noise of the kernel (all cells, and without the
    traces stopped at the cap) and with its duration; CI by workload bootstrap."""
    names, w = D.workload_draws(c["workload"].unique())
    out = {}
    for s in D.DYNAMIC:
        cs = D.by_strategy(c, s)
        reps = resamples(cs["workload"].map({n: i for i, n in enumerate(names)}).to_numpy(), w)
        ys = {"n_star": cs["n_star"].to_numpy(float), "hors_plafond": n_star_below_cap(t, cs, s)}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for name, (x, y) in CORRELATIONS.items():
                out[(s, name)] = spearman_boot(cs[x].to_numpy(float), ys[y], reps)
    return out


def adaptation_table(adapts: dict) -> str:
    rows = []
    for plat, s in ((p, s) for p in adapts for s in D.DYNAMIC):
        r = {k: adapts[plat][(s, k)] for k in CORRELATIONS}
        rho = lambda k: L.ci(r[k]["rho"], r[k]["ci_low"], r[k]["ci_high"], 2, sign=False)  # noqa: E731
        rows.append([plat, D.STRATEGIES[s], rho("bruit"), rho("bruit_sans_plafond"), L.val(r["bruit_sans_plafond"]["n"], 0), rho("duree")])
    head = [L.header(["Plateforme", "Stratégie", r"$\rho(N^*, \mathrm{RCV}_{\mathrm{OQAD}})$ [IC]", "Idem, sans plafond [IC]",
                      "Cellules retenues", r"$\rho(N^*, m)$ [IC]"])]
    return L.table(r"Corrélation de Spearman entre $N^*$ et le bruit ($\mathrm{RCV}_{\mathrm{OQAD}}$) ou la durée médiane ($m$) du "
                   r"\textit{kernel}, par stratégie dynamique [IC à $95\,\%$].", "rq4_adaptation", "llcccc", head, L.grouped_rows(rows, 1))


def dm_tests(c: pd.DataFrame) -> dict:
    """Delta(Delta m*) = SMS+ - each other strategy, paired by cell; Holm over the 6 comparisons."""
    a = D.by_strategy(c, D.RULE)
    tests = {s: wilcoxon_hl((lambda p: p["dm_pct_a"] - p["dm_pct_b"])(D.pair(a, D.by_strategy(c, s), D.CELL, ["dm_pct"]))) for s in D.OTHERS}
    for s, p in zip(tests, holm([r["p"] for r in tests.values()])):
        tests[s]["p_holm"] = p
    return tests


def repro_table(pfs: dict) -> str:
    rows = []
    for plat, (_, c) in pfs.items():
        tests = dm_tests(c)
        for s in D.STRATEGIES:
            cs, r = D.by_strategy(c, s), tests.get(s)
            rows.append([plat, D.STRATEGIES[s], L.val(cs["dN_pct"].median(), 1) if s in D.DYNAMIC else L.NA,
                         L.val(cs["dm_pct"].median(), 3), L.ci(r["hl"], r["ci_low"], r["ci_high"], 3) if r else L.NA])
    head = [L.header(["Plateforme", "Stratégie", r"$\Delta N^*$ médian (\%)", r"$\Delta m^*$ médian (\%)", r"$\Delta(\Delta m^*)$ (pp) [IC]"])]
    return L.table(r"Reproductibilité de la décision d'arrêt ($\Delta N^*$) et de la mesure ($\Delta m^*$) par stratégie, et écart de "
                   r"$\Delta m^*$ de \smsp à chacune (HL [IC à $95\,\%$]).", "rq4_repro", "llccc", head, L.grouped_rows(rows, 1))


def harness_table(pfs: dict) -> str:
    """Per strategy and harness, clocks pooled: mean N*, share at the cap, median Delta N*, share of failures."""
    rows = []
    for plat, s in ((p, s) for p in pfs for s in D.STRATEGIES):
        t, c = pfs[plat]
        dyn = s in D.DYNAMIC
        cs, ts = D.by_strategy(c, s), t[t["critere"] == s]
        hs = [(cs[cs["harnais"] == h], ts[ts["harnais"] == h]) for h in D.HARNESS]
        rows.append([plat, D.STRATEGIES[s]] + [L.val(x["n_star"].mean(), 0) for x, _ in hs]
                    + [L.val(x["part_plafond"].mean() * 100, 1) if dyn else L.NA for x, _ in hs]
                    + [L.val(x["dN_pct"].median(), 1) if dyn else L.NA for x, _ in hs]
                    + [L.val(y["echec"].mean() * 100, 2) for _, y in hs])
    head = L.grouped_header([r"\textbf{Plateforme}", r"\textbf{Stratégie}"],
                            [r"\textbf{$N^*$ moyen}", r"\textbf{Au plafond (\%)}", r"\textbf{$\Delta N^*$ médian (\%)}", r"\textbf{Échecs (\%)}"],
                            [r"\texttt{Minimal}", r"\texttt{Complet}"])
    return L.table(r"Coût, part au plafond, reproductibilité de la décision ($\Delta N^*$) et part d'échecs par stratégie, selon le harnais.",
                   "rq4_harnais", "llcccccccc", head, L.grouped_rows(rows, 1))


def make_all(pfs: dict, out) -> None:
    """pfs: {platform: (traces, cells)}, one block of rows per platform."""
    out.mkdir(parents=True, exist_ok=True)
    for name, text in (("RQ-E-4.3-rq4_adaptation-tabl", adaptation_table({p: adaptation(t, c) for p, (t, c) in pfs.items()})),
                       ("RQ-E-4.4-rq4_repro-tabl", repro_table(pfs)),
                       ("RQ-E-4.5-rq4_harnais-tabl", harness_table(pfs))):
        (out / f"{name}.tex").write_text(text, encoding="utf-8")
        print(f"  {out / name}.tex")
