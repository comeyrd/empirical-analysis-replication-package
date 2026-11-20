"""Registry of the values quoted in the thesis text.

Each entry names the thesis sub-question, what is computed, the value, and its source:
  - "test"  a statistical test (Wilcoxon + Hodges-Lehmann, bootstrap, Spearman, sign test);
  - "value" a descriptive number that only appears in the text.
Values that the text reads off a figure or a table are not repeated here: they come from that output.

write() renders results.md (one table per sub-question, for reading) and results.csv (one row per
entry with its raw numbers, for checking).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def num(v, digits: int = 2, sign: bool = False) -> str:
    """Plain number for the report: fixed decimals, scientific notation for tiny p-values."""
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{v:{'+' if sign else ''}.{digits}f}"


def pval(p) -> str:
    if p is None or not np.isfinite(p):
        return "n/a"
    return "0 (< 1e-300)" if p == 0 else (f"{p:.1e}" if p < 0.001 else f"{p:.3f}")


def hl_text(r: dict, digits: int = 2, unit: str = "", p_key: str = "p") -> str:
    """'HL = +0.71 pp [+0.63 ; +0.79], p = 1.4e-57, n = 576' from a wilcoxon_hl result."""
    u = f" {unit}" if unit else ""
    return (f"HL = {num(r['hl'], digits, True)}{u} [{num(r['ci_low'], digits, True)} ; {num(r['ci_high'], digits, True)}], "
            f"p = {pval(r[p_key])}, n = {r['n']}")


class Results:
    def __init__(self, title: str):
        self.title = title
        self.rows: list[dict] = []

    def add(self, rq: str, quantity: str, value: str, source: str = "value", method: str = "", **raw) -> None:
        clean = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v) for k, v in raw.items()}
        self.rows.append({"rq": rq, "quantity": quantity, "value": value, "source": source, "method": method,
                          "raw": json.dumps(clean, default=float, ensure_ascii=False)})

    def test(self, rq: str, quantity: str, r: dict, digits: int = 2, unit: str = "",
             method: str = "paired Wilcoxon + HL [95 % CI]", p_key: str = "p") -> None:
        """A paired Wilcoxon + HL result (dict of common.stats.wilcoxon_hl)."""
        raw = {("p_method" if k == "method" else k): v for k, v in r.items() if np.isscalar(v)}
        self.add(rq, quantity, hl_text(r, digits, unit, p_key), "test", method, **raw)

    def write(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.rows)
        df.to_csv(folder / "results.csv", index=False)
        lines = [f"# {self.title}", "",
                 "Values quoted in the thesis text, by sub-question. `test`: statistical test; "
                 "`value`: descriptive number. Values read off a figure or a table are not repeated here.", ""]
        for rq, block in df.groupby("rq", sort=False):
            lines += [f"## {rq}", "", "| Quantity | Value | Source | Method |", "| :--- | :--- | :---: | :--- |"]
            lines += [f"| {r.quantity} | {r.value} | {r.source} | {r.method} |" for r in block.itertuples()]
            lines.append("")
        (folder / "results.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"  {folder / 'results.md'} ({len(df)} values)")
