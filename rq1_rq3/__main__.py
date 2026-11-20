"""Reproduce RQ-E-1 to RQ-E-3 from rq1_rq3/data/ into rq1_rq3/outputs/.

    ./.venv/bin/python -m rq1_rq3                  # criterion study, figures, tables, results
    ./.venv/bin/python -m rq1_rq3 postprocess MI210  # rebuild the derived files of a platform from raw/
    ./.venv/bin/python -m rq1_rq3 figures|tables|results|criterion
"""
import sys

from rq1_rq3 import criterion, data as D, figures, postprocess, results, tables


def main(argv: list[str]) -> None:
    step = argv[0] if argv else "all"
    if step == "postprocess":
        for plat in argv[1:] or D.PLATFORMS:
            postprocess.run(plat)
        return
    if step in ("all", "criterion"):
        crit = criterion.run()
    else:
        crit = criterion.load() if (criterion.OUT / "decisions.json").exists() else None
    if step in ("all", "figures"):
        for plat in D.available():
            figures.make_all(plat, D.OUT / "figures")
    if step in ("all", "tables"):
        tables.make_all(D.OUT / "tables", crit)
    if step in ("all", "results"):
        results.make(crit).write(D.OUT)


if __name__ == "__main__":
    main(sys.argv[1:])
