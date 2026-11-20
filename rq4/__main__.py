"""Reproduce RQ-E-4 from rq4/data/ into rq4/outputs/ (RQ-E-4.6 also reads rq1_rq3/data/).

    ./.venv/bin/python -m rq4                    # figures, tables, results
    ./.venv/bin/python -m rq4 extract MI210      # rebuild traces.csv, batches.csv, control.csv from raw/
    ./.venv/bin/python -m rq4 figures|tables|results
"""
import sys

from rq4 import data as D, extract, figures, results, tables


def main(argv: list[str]) -> None:
    step = argv[0] if argv else "all"
    if step == "extract":
        for plat in argv[1:] or D.PLATFORMS:
            extract.run(plat)
        return
    pfs = {}
    for plat in D.available():
        t = D.traces(plat)
        pfs[plat] = (t, D.cells(t))
    if step in ("all", "figures"):
        figures.make_all(pfs, D.OUT / "figures")
    if step in ("all", "tables"):
        tables.make_all(pfs, D.OUT / "tables")
    if step in ("all", "results"):
        results.make(pfs).write(D.OUT)


if __name__ == "__main__":
    main(sys.argv[1:])
