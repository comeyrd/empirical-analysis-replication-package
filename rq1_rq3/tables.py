"""Tables of RQ-E-1 to RQ-E-3, in LaTeX, named and laid out as in the thesis (outputs/tables/*.tex).

The RQ-E-3.3 to 3.6 tables format the values of criterion.py (outputs/criterion/).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import latex as L
from rq1_rq3 import data as D

CONFIG_ROWS = [("locked", "Full"), ("locked", "Minimal"), ("unlocked", "Full"), ("unlocked", "Minimal")]
FR = {"locked": "Verrouillées", "unlocked": "Libres", "Full": "Complet", "Minimal": "Minimal"}


def _fr(v: float, digits: int) -> str:
    """Number in math mode inside a $...$ cell of the RQ-E-1 and 2 tables: '3{,}16'."""
    return f"{v:.{digits}f}".replace(".", "{,}")


def _align(rows: list[list[str]]) -> list[list[str]]:
    widths = [max(len(c) for c in col) for col in zip(*rows)]
    return [[c.ljust(w) for c, w in zip(row, widths)] for row in rows]


def _fill(template: str, **slots: list[str]) -> str:
    for slot, lines in slots.items():
        template = template.replace(f"<<{slot}>>", "\n        ".join(lines))
    return template.replace("<<SP>>", " ")


def _config_rows(cells: dict, harness: str = "%s") -> list[str]:
    """One row per (clocks, harness) of a platform, the values already formatted."""
    return [f"& {FR[c]:<12} & {harness % FR[s]}  & " + " & ".join(f"${v}$" for v in cells[(c, s)]) + r" \\"
            for c, s in CONFIG_ROWS]


def _head(caption: str, label: str, cols: str, header: str, extra: str = "") -> str:
    return (r"\begin{table}[htb]" "\n    \\centering\n    \\small\n"
            f"    \\caption{{{caption}}}\n    \\label{{tab:{label}}}\n    \\renewcommand{{\\arraystretch}}{{1.25}}\n"
            f"    \\begin{{tabular}}{{{cols}}}\n        \\toprule\n{header}        \\midrule\n")


def _platform_blocks(head: str, rows: dict[str, list[str]], vspace: bool = True) -> str:
    body = "        \\midrule\n".join(f"        \\multirow{{4}}{{*}}{{\\textbf{{{p}}}}} \n        " + "\n        ".join(rows[p]) + "\n"
                                       for p in D.PLATFORMS)
    return head + body + "        \\bottomrule\n    \\end{tabular}\n" + ("    \\vspace{0.15cm}\n" if vspace else "") + "\\end{table}\n"


# --------------------------------------------------------------------------- #
# RQ-E-1 and RQ-E-2
# --------------------------------------------------------------------------- #
def lower_tail(df: pd.DataFrame) -> str:
    """RQ-E-1.3 (MI210): floor margin P and share of launches at least 2 % and 3 % faster than the trace
    median, medians over the traces of each work size."""
    med = df.set_index("run_id")["median"]
    rows = []
    for rid, rg in D.traces("MI210", ("run_id", "time")):
        faster = (med[rid] - rg["time"].to_numpy()) / med[rid] * 100.0
        rows.append({"run_id": rid, "mass_2": np.mean(faster >= 2.0) * 100.0, "mass_3": np.mean(faster >= 3.0) * 100.0})
    t = pd.DataFrame(rows).merge(df[["run_id", "worksize", "floor_gap_rel"]], on="run_id")
    s = t.groupby("worksize")[["floor_gap_rel", "mass_2", "mass_3"]].median()
    cells = _align([[rf"\textbf{{{ws}}}"] + [rf"${_fr(v, 2)}\,\%$" for v in r] for ws, r in s.iterrows()])
    header = (r"        \textbf{\texttt{work\_size}} & \textbf{Marge au plancher $\mathcal{P}$} & \textbf{Traîne inférieure ($\ge 2\,\%$)} & \textbf{Traîne inférieure ($\ge 3\,\%$)} \\" "\n")
    caption = (r"Marge au plancher ($\mathcal{P}$) et masse de la traîne inférieure (observations plus rapides que la "
               r"médiane d'au moins $2\,\%$ et $3\,\%$) sur AMD MI210 par taille de travail.")
    return (_head(caption, "mi210_left_tail", "cccc", header) + "".join(f"        {' & '.join(r)} \\\\\n" for r in cells)
            + "        \\bottomrule\n    \\end{tabular}\n\\end{table}\n")


def quantization(data: dict[str, pd.DataFrame]) -> str:
    """RQ-E-1.6: timer step (relative, absolute), distinct values and ties with the median, medians over traces."""
    rows, plats = [], []
    for p in D.PLATFORMS:
        for ws, sub in data[p].groupby("worksize"):
            rows.append([str(ws), _fr(sub["timer_step_rel"].median(), 3), _fr(sub["timer_step_abs"].median() * 1000.0, 3),
                         f"{sub['unique_values_n'].median():.0f}", _fr(sub["pct_at_median_rel"].median(), 2)])
            plats.append(p)
    lines = {p: [] for p in D.PLATFORMS}
    for p, row in zip(plats, _align(rows)):
        lines[p].append(("& " if lines[p] else "") + " & ".join(row) + r" \\")
    return (r"""\begin{table}[htb]
    \centering
    \small
    \caption{Résolution temporelle des chronomètres matériels et proportion d'observations ex æquo avec la médiane par plateforme et taille de travail.}
    \label{tab:seuils-quantification}
    \renewcommand{\arraystretch}{1.25}
    \begin{tabular}{llrrrr}
        \toprule
        \textbf{Plateforme} & \textbf{\texttt{work\_size}} & \textbf{Pas rel. (\%)} & \textbf{Pas abs. ($\mu$s)} & \textbf{Paliers} & \textbf{Ex æquo $m$ (\%)} \\
        \midrule
        \multirow{4}{*}{\textbf{V100}}  & """ + "\n        ".join(lines["V100"]) + r"""
        \midrule
        \multirow{4}{*}{\textbf{MI210}} & """ + "\n        ".join(lines["MI210"]) + r"""
        \bottomrule
    \end{tabular}
\end{table}
""")


def drifts(df: pd.DataFrame) -> pd.DataFrame:
    """Per cell: mean intra-trace RCV_OQAD, and the inter-campaign drifts of m (%), RCV_OQAD, P, C, T (pp)."""
    cells = D.cell_drift(df, {"delta_m": "median"}, relative_to="median")
    cells = cells.merge(D.cell_drift(df, {"delta_rcv": "RCV_QAD_rel", "delta_p": "floor_gap_rel", "delta_c": "bulk_horizon_rel",
                                          "delta_t": "tail_mass_rel"}).drop(columns="K"), on=D.CELL)
    return cells.merge(df.groupby(D.CELL)["RCV_QAD_rel"].mean().rename("intra_rcv").reset_index(), on=D.CELL)


def reproducibility(data: dict[str, pd.DataFrame], which: str) -> str:
    """RQ-E-2.3 (geometry: Delta P, C, T) or RQ-E-2.4 (intra RCV_OQAD, Delta m, Delta RCV_OQAD): medians over the cells."""
    spec = {"geometry": [("delta_p", 3), ("delta_c", 3), ("delta_t", 3)],
            "location": [("intra_rcv", 2), ("delta_m", 2), ("delta_rcv", 3)]}[which]
    rows = {}
    for p in D.PLATFORMS:
        cells = drifts(data[p])
        rows[p] = _config_rows({(c, s): [_fr(cells.loc[(cells["clocks"] == c) & (cells["setup"] == s), col].median(), d)
                                         for col, d in spec] for c, s in CONFIG_ROWS})
    if which == "geometry":
        caption, label = "Reproductibilité de la géométrie interne de la distribution sur NVIDIA V100 et AMD MI210.", "rq2_geometry_reproducibilite"
        cols = [r"\textbf{$\Delta\mathcal{P}$ (pp)}", r"\textbf{$\Delta\mathcal{C}$ (pp)}", r"\textbf{$\Delta\mathcal{T}$ (pp)}"]
    else:
        caption = (r"Reproductibilité de la localisation et de la dispersion : comparaison de l'instabilité intra-trace "
                   r"($\mathrm{RCV}_{\mathrm{OQAD}}$) et de la dérive inter-campagnes sur NVIDIA V100 et AMD MI210 selon les "
                   r"régimes d'horloge et la configuration du harnais.")
        label = "rq2_location_dispersion"
        cols = [r"\textbf{Intra $\mathrm{RCV}_{\mathrm{OQAD}}$ (\%)}", r"\textbf{$\Delta m$ (\%)}",
                r"\textbf{$\Delta \mathrm{RCV}_{\mathrm{OQAD}}$ (pp)}"]
    header = "        \\textbf{Plateforme} & \\textbf{Horloges} & \\textbf{Harnais} & \n" + " & \n".join(f"        {c}" for c in cols) + " \\\\\n"
    return _platform_blocks(_head(caption, label, "lllccc", header), rows)


def temporal_cost(data: dict[str, pd.DataFrame]) -> str:
    """RQ-E-2.5: median wall time of a trace per work size (s), cumulative time (h) and its ratio to Libres / Minimal."""
    rows = {}
    for p in D.PLATFORMS:
        df = data[p]
        hours = lambda c, s: df.loc[(df["clocks"] == c) & (df["setup"] == s), "benchmark_time"].sum() / 3.6e6  # noqa: E731
        cells = {}
        for c, s in CONFIG_ROWS:
            sub = df[(df["clocks"] == c) & (df["setup"] == s)]
            cells[(c, s)] = ([_fr(sub.loc[sub["worksize"] == ws, "benchmark_time"].median() / 1000.0, 2) for ws in sorted(df["worksize"].unique())]
                             + [_fr(hours(c, s), 2) + r"\,\text{h}", r"\times " + _fr(hours(c, s) / hours("unlocked", "Minimal"), 2)])
        rows[p] = _config_rows(cells, harness=r"\texttt{%s}")
    caption = (r"Coût temporel d'une trace de 10\,000 répétitions par taille de travail (\texttt{work\_size}), durée cumulée "
               r"par configuration et facteur de surcoût relatif à la configuration \texttt{Libres / Minimal}.")
    header = ("        \\textbf{Plateforme} & \\textbf{Horloges} & \\textbf{Harnais} & \n"
              "        \\textbf{\\texttt{8} (s)} & \\textbf{\\texttt{32} (s)} & \n"
              "        \\textbf{\\texttt{128} (s)} & \\textbf{\\texttt{512} (s)} & \n"
              "        \\textbf{Cumulé (h)} & \\textbf{Surcoût} \\\\\n")
    return _platform_blocks(_head(caption, "rq2_cout_temporel", "lllcccccc", header), rows)


# --------------------------------------------------------------------------- #
# RQ-E-3.3 to RQ-E-3.6
# --------------------------------------------------------------------------- #
def _short(stratum: str) -> str:
    card, clocks = stratum.split(" ", 1)
    return f"{card} {'verr.' if clocks == 'verrouillées' else clocks}"


def _three_groups(first: str, k: int, start: int) -> list[str]:
    """Header of N* moyen (2 columns), Au plafond (2) and Excès (k), starting at column `start`."""
    return [first + r"\multicolumn{2}{c}{\textbf{$N^*$ moyen}} & \multicolumn{2}{c}{\textbf{Au plafond (\%)}} & "
            + rf"\multicolumn{{{k}}}{{c}}{{\textbf{{Excès (pp)}}}} & \\",
            rf"\cmidrule(lr){{{start}-{start + 1}}}\cmidrule(lr){{{start + 2}-{start + 3}}}\cmidrule(lr){{{start + 4}-{start + 3 + k}}}"]


def nmax(res: dict) -> str:
    dec, raw = res["decisions"], res["nmax"]
    budgets = [n for n in (dec["n_max"] - 100, dec["n_max"] - 50, dec["n_max"], dec["n_max"] + 50)]
    rows = []
    for name, g in raw.groupby("Strate", sort=False):
        card, clocks = name.split(" ", 1)
        label = FR["locked" if clocks == "verrouillées" else "unlocked"] + ("" if g["Stable"].iloc[0] else " (non contrainte)")
        rows.append([card, label, L.val(g["p(2000) (%)"].iloc[0], 2)]
                    + [L.excess(r["Delta (pp)"], r["U95 (pp)"]) for n in budgets for _, r in g[g["N"] == n].iterrows()])
    head = [L.header(["Plateforme", "Horloges", r"$p(2\,000)$ (\%)"] + [f"$N = {n}$" for n in budgets])]
    return L.table(r"Choix de $N_{\max}$ : excès d'échecs d'un budget fixe face à $N = 2\,000$, en pp, et $U_{95}$ entre parenthèses.",
                   "rq3_nmax", "llc" + "c" * len(budgets), head, L.grouped_rows(rows, 1), tabcolsep=None)


def _design_cells(r, stable: list[str]) -> list[str]:
    return ([L.val(r[f"N* {c}"], 0) for c in D.PLATFORMS] + [L.val(r[f"Au plafond {c} (%)"], 1) for c in D.PLATFORMS]
            + [L.val(r[f"Excès {n} (pp)"], 2, True) for n in stable] + [L.val(r["P (%)"], 1)])


def frontier(res: dict) -> str:
    dec, fr = res["decisions"], res["frontier"]
    rows = []
    for _, r in fr[(fr["S"] >= dec["s"] - 4) & (fr["S"] <= dec["s"] + 2)].iterrows():
        alpha = L.num(r["alpha"], 2)
        cells = [f"${int(r['S'])}$", f"${alpha}$" if r["Admissible"] else f"$({alpha})$"] + _design_cells(r, dec["stable"])
        chosen = int(r["S"]) == dec["s"] and np.isclose(r["alpha"], dec["alpha"])
        rows.append(" & ".join(L.bold(c) if chosen else c for c in cells) + r" \\")
    stable = [_short(n) for n in dec["stable"]]
    head = _three_groups(" & & ", len(stable), 3) + [L.header(["$S$", r"$\alpha$", "V100", "MI210", "V100", "MI210"] + stable + [r"$P$ (\%)"])]
    return L.table(r"Paramétrage de $\alpha$ et $S$ : pour chaque $S$, le $\alpha$ admissible le moins coûteux (entre parenthèses : "
                   r"aucun admissible ; en gras : \smsp{}).", "rq3_frontier", "c" * 10, head, rows, tabcolsep="4pt")


def factorial(res: dict) -> str:
    dec, fac = res["decisions"], res["factorial"].set_index("Clé")
    groups = [[("C0", "C0"), ("C0+C1", "C0 + C1 (sans C2)"), ("C0+C1+C2", r"\smsp{} (C0 + C1 + C2)")],
              [("C1+C2", "C1 + C2 (sans C0)"), ("C0+C2", "C0 + C2 (sans C1)")],
              [("C1", "C1 seule"), ("C2", "C2 seule")], [("aucune", f"Aucune : $N$ fixe $= {dec['n_max']}$")]]
    rows = []
    for i, group in enumerate(groups):
        rows += [r"\midrule"] if i else []
        rows += [" & ".join([label] + _design_cells(fac.loc[key], dec["stable"])) + r" \\" for key, label in group]
    stable = [_short(n) for n in dec["stable"]]
    head = _three_groups(" & ", len(stable), 2) + [L.header(["Conditions", "V100", "MI210", "V100", "MI210"] + stable + [r"$P$ (\%)"])]
    return L.table(rf"Combinaisons de C0, C1 et C2 à $\alpha = {L.num(dec['alpha'], 2)},\ S = {dec['s']}$ fixés.", "rq3_factorial",
                   "lcccccccc", head, rows, tabcolsep="4pt")


def components(res: dict) -> str:
    dec, comp = res["decisions"], res["components"].set_index("Composante")
    rows = []
    for i, (prefix, title, label) in enumerate((("Sans elle", "Re-paramétrée sans elle", "Sans {j}"),
                                                ("Seule", "Re-paramétrée seule", "{j} seule"))):
        rows += ([r"\midrule"] if i else []) + [rf"\multicolumn{{6}}{{l}}{{\textit{{{title}}}}} \\"]
        for j, r in comp.iterrows():
            rows.append(" & ".join([rf"\quad {label.format(j=j)}", f"$({L.num(r[f'{prefix}, alpha'], 2)} ; {int(r[f'{prefix}, S'])})$",
                                    L.ci(r[f"{prefix}, surcoût"], r[f"{prefix}, IC bas"], r[f"{prefix}, IC haut"], 1)]
                                   + [L.val(r[f"{prefix}, Excès {n} (pp)"], 2, True) for n in dec["stable"]]) + r" \\")
    stable = [_short(n) for n in dec["stable"]]
    head = [r" & & & \multicolumn{3}{c}{\textbf{Excès (pp)}} \\", r"\cmidrule(lr){4-6}",
            L.header(["", r"Optimum ($\alpha$ ; $S$)", r"Surcoût $N^*$ [IC à $95\,\%$]"] + stable)]
    return L.table("Apport de chaque condition, règles réduites re-paramétrées.", "rq3_components", "lccccc", head, rows, tabcolsep="4pt")


def test(res: dict) -> str:
    dec, t, paired = res["decisions"], res["test"].set_index("Clé"), res["test_paired"]
    fixed = f"$N$ fixe $= {dec['n_max']}$"
    rule = lambda a, s: rf"($\alpha = {L.num(a, 2)}$, $S = {s}$)"  # noqa: E731
    rows = []
    for key, label in (("figee", r"\smsp{} " + rule(dec["alpha"], dec["s"])),
                       ("c0", r"\smsz{} " + rule(dec["c0_only"]["alpha"], dec["c0_only"]["s"])), ("fixe_nmax", fixed)):
        r = t.loc[key]
        rows.append(" & ".join([label] + [L.val(r[f"N* {c}"], 0) for c in D.PLATFORMS]
                               + [L.excess(r[f"Excès {n} (pp)"], r[f"U95 {n} (pp)"]) for n in dec["stable"]]) + r" \\")
    rows.append(r"\midrule")
    for key, other, label in (("c0", "C0 seule", r"\smsz{}"), ("fixe_nmax", f"N fixe = {dec['n_max']}", fixed)):
        cells = [rf"Écart \smsp{{}} $-$ {label} [IC à 95 \%]"]
        for c in D.PLATFORMS:
            h = paired[(paired["label"] == f"figée - {other}") & (paired["card"] == c) & (paired["metric"] == "N*")].iloc[0]
            cells.append(L.ci(h["hl"], h["ci_low"], h["ci_high"], 0))
        r = t.loc[key]
        cells += [L.ci(r[f"Figée moins règle {n} (pp)"], r[f"Figée moins règle {n} IC bas"], r[f"Figée moins règle {n} IC haut"], 2)
                  for n in dec["stable"]]
        rows.append(" & ".join(cells) + r" \\")
    stable = [_short(n) for n in dec["stable"]]
    head = [r" & \multicolumn{2}{c}{\textbf{$N^*$ moyen}} & " + rf"\multicolumn{{{len(stable)}}}{{c}}{{\textbf{{Excès ($U_{{95}}$), pp}}}} \\",
            rf"\cmidrule(lr){{2-3}}\cmidrule(lr){{4-{3 + len(stable)}}}", L.header(["Règle", "V100", "MI210"] + stable)]
    shares = " / ".join(L.num(t.loc["fixe_2000", f"Échecs {n} (%)"], 2) for n in dec["stable"])
    camps = [str(c) for c in dec["test_campaigns"]]
    caption = (rf"\smsp{{}}, \smsz{{}} et budget fixe $N = {dec['n_max']}$ sur les campagnes de test {', '.join(camps[:-1])} et {camps[-1]} "
               rf"(écarts de $N^*$ : HL apparié par cellule). Parts d'échecs de $N = 2\,000$ : ${shares}\,\%$ ({' / '.join(stable)}).")
    return L.table(caption, "rq3_test", "lccccc", head, rows, tabcolsep="4pt")


def make_all(out, criterion_values: dict | None) -> None:
    data = {p: D.load(p) for p in D.PLATFORMS}
    tables = {
        "RQ-E-1.3-mi210_left_tail-tabl": lambda: lower_tail(data["MI210"]),
        "RQ-E-1.6-seuils-quantification-tabl": lambda: quantization(data),
        "RQ-E-2.3-rq2_geometry_reproducibilite-tabl": lambda: reproducibility(data, "geometry"),
        "RQ-E-2.4-rq2_location_dispersion-tabl": lambda: reproducibility(data, "location"),
        "RQ-E-2.5-rq2_cout_temporel-tabl": lambda: temporal_cost(data),
    }
    if criterion_values is not None:
        tables.update({
            "RQ-E-3.3-rq3_nmax-tabl": lambda: nmax(criterion_values),
            "RQ-E-3.4-rq3_frontier-tabl": lambda: frontier(criterion_values),
            "RQ-E-3.5-rq3_factorial-tabl": lambda: factorial(criterion_values),
            "RQ-E-3.5-rq3_components-tabl": lambda: components(criterion_values),
            "RQ-E-3.6-rq3_test-tabl": lambda: test(criterion_values),
        })
    out.mkdir(parents=True, exist_ok=True)
    for name, build in tables.items():
        (out / f"{name}.tex").write_text(build(), encoding="utf-8")
        print(f"  {out / name}.tex")
