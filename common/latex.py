"""LaTeX tables in the style of the thesis: French numbers ({,} decimal comma, thin space every three
digits), booktabs rules, tables shrunk to the line width only when wider."""
from __future__ import annotations

import numpy as np

NA = "---"


def num(v: float, digits: int, sign: bool = False) -> str:
    """Number for math mode, without the $: '-1{,}23', '+0{,}00', '8\\,575'. Never '-0'."""
    v = float(v)
    if round(v, digits) == 0:
        v = 0.0
    whole, _, frac = f"{abs(v):.{digits}f}".partition(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    text = r"\,".join([whole] + groups) + (f"{{,}}{frac}" if frac else "")
    return ("-" if v < 0 else ("+" if sign else "")) + text


def finite(*values) -> bool:
    return all(v is not None and np.isfinite(v) for v in values)


def val(v, digits: int, sign: bool = False) -> str:
    return f"${num(v, digits, sign)}$" if finite(v) else NA


def ci(v, low, high, digits: int, sign: bool = True) -> str:
    """Estimate and 95 % CI: '$-146\\;[-158 ; -134]$'."""
    if not finite(v, low, high):
        return NA
    return rf"${num(v, digits, sign)}\;[{num(low, digits, sign)} ; {num(high, digits, sign)}]$"


def excess(v, u95, digits: int = 2) -> str:
    """Excess of failures and its one-sided bound: '$+0{,}23\\;(0{,}58)$'."""
    return rf"${num(v, digits, True)}\;({num(u95, digits)})$" if finite(v, u95) else NA


def bold(cell: str) -> str:
    """Bold a cell: math content goes in \\mathbf."""
    return rf"$\mathbf{{{cell[1:-1]}}}$" if cell.startswith("$") else rf"\textbf{{{cell}}}"


def header(cells: list[str]) -> str:
    return " & ".join(rf"\textbf{{{c}}}" if c else "" for c in cells) + r" \\"


def grouped_header(fixed: list[str], groups: list[str], sub: list[str]) -> list[str]:
    """Two-line header: `fixed` columns span both lines, each group spans len(sub) columns."""
    f, k = len(fixed), len(sub)
    first = [rf"\multirow{{2}}{{*}}{{{c}}}" for c in fixed] + [rf"\multicolumn{{{k}}}{{c}}{{{g}}}" for g in groups]
    rules = " ".join(rf"\cmidrule(lr){{{f + 1 + i * k}-{f + (i + 1) * k}}}" for i in range(len(groups)))
    return [" & ".join(first) + r" \\", rules, " & ".join([""] * f + sub * len(groups)) + r" \\"]


def grouped_rows(rows: list[list[str]], levels: int) -> list[str]:
    """The first `levels` cells of each row are group keys, written once as a \\multirow over their
    group; \\midrule between first-level groups, \\cmidrule between deeper groups."""
    ncol = len(rows[0])
    out = []
    for i, row in enumerate(rows):
        change = next((j for j in range(levels) if i == 0 or row[:j + 1] != rows[i - 1][:j + 1]), None)
        if i > 0 and change is not None:
            out.append(r"\midrule" if change == 0 else rf"\cmidrule(lr){{{change + 1}-{ncol}}}")
        cells = []
        for j in range(levels):
            if change is not None and j >= change:
                span = 1
                while i + span < len(rows) and rows[i + span][:j + 1] == row[:j + 1]:
                    span += 1
                cells.append(rf"\multirow{{{span}}}{{*}}{{{row[j]}}}")
            else:
                cells.append("")
        out.append(" & ".join(cells + row[levels:]) + r" \\")
    return out


def table(caption: str, label: str, cols: str, head: list[str], rows: list[str], tabcolsep: str | None = "3pt") -> str:
    lines = [r"\begin{table}[!htb]", r"    \centering", r"    \small", rf"    \caption{{{caption}}}",
             rf"    \label{{tab:{label}}}", r"    \renewcommand{\arraystretch}{1.25}"]
    if tabcolsep:
        lines.append(rf"    \setlength{{\tabcolsep}}{{{tabcolsep}}}")
    lines += [r"    \resizebox{\ifdim\width>\linewidth\linewidth\else\width\fi}{!}{%",
              rf"    \begin{{tabular}}{{{cols}}}", r"        \toprule"]
    lines += ["        " + h for h in head] + [r"        \midrule"]
    lines += ["        " + r for r in rows]
    lines += [r"        \bottomrule", r"    \end{tabular}}", r"\end{table}", ""]
    return "\n".join(lines)
