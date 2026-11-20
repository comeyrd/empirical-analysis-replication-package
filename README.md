# Empirical study of GPU benchmarking methodology: reproduction package

Data processing and outputs of the empirical chapter of the master's thesis (chapter 4, _Étude empirique de
la méthodologie de benchmarking GPU_). GEMM kernels of [blas-baseliner](https://github.com/comeyrd/blas-baseliner-benchmark)
are measured with Baseliner 1.0 on an NVIDIA V100 (CUDA) and an AMD MI210 (HIP).

Two experiments, one folder each:

| Folder     | Experiment                                                                                      | Thesis                                                                                                |
| :--------- | :---------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| `rq1_rq3/` | Main corpus: 10 campaigns of 10,000 launches per cell (workload x work size x clocks x harness) | RQ-E-1 distributions and estimators, RQ-E-2 experimental control, RQ-E-3 stopping criterion (offline) |
| `rq4/`     | SMS experiment: 7 stopping strategies decided online, 10 campaigns, plus a control run          | RQ-E-4 online evaluation of the stopping criteria (MI210 only)                                        |

Each pipeline writes the thesis figures and tables, named as the thesis includes them, and `results.md`:
every value the text quotes that is not read off a figure or a table, with the statistical test behind it.

## Layout

```text
common/                 shared code: report reader, statistics, LaTeX tables, plot style, results report,
                        clock locking scripts
CMakeLists.txt          build of the two benchmark binaries into bin/ (presets in CMakePresets.json)
bin/                    the two benchmark binaries, once built (git-ignored)
pack-data.sh            archive of the derived data (no raw reports)
rq1_rq3/
  experiment/           run scripts, Baseliner protocols, CMakeLists.txt of the binary
  data/<v100|mi210>/    raw/*.json reports and the derived files (git-ignored)
  outputs/              figures/*.pdf, tables/*.tex, criterion/ (values of the RQ-E-3 tables), results.md
  postprocess.py        raw reports -> derived files
  criterion.py          offline study of the stopping criterion (RQ-E-3.3 to 3.6)
  figures.py tables.py results.py
rq4/
  experiment/           run scripts, protocols (and their generator), CMakeLists.txt of the binary
  stopping_criterion/   C++ of the two SMS rules, compiled into the benchmark binary
  data/<mi210>/         raw/*.json, control/raw/*.json and the derived files (git-ignored)
  outputs/              figures/*.pdf, tables/*.tex, results.md
  extract.py            raw reports -> derived files
  figures.py tables.py results.py
```

## Setup

With Python 3.13 :

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

## Get the data

Either unpack the archive of the derived data at the root of the repository:

```bash
tar xzf derived-data.tar.gz        # creates rq1_rq3/data/<platform>/ and rq4/data/<platform>/
```

/!\ This archive only contains the derived data, not the raw execution times.
/!\ Due to an outage on the V100 machine, the raw execution times archive is currently unavailable.

or put raw Baseliner reports in `rq1_rq3/data/<platform>/raw/` and `rq4/data/<platform>/raw/` (the run scripts
below write them there) and derive the files:

```bash
./.venv/bin/python -m rq1_rq3 postprocess MI210    # about 3 min per platform
./.venv/bin/python -m rq4 extract MI210             # about 30 s
```

A report name must contain `locked` or `unlocked`: Baseliner does not record the clock regime, the run scripts
put it in the file name. The V100 raw report of the main corpus is truncated: its derived files only exist in
the archive.

## Reproduce the outputs

```bash
./.venv/bin/python -m rq1_rq3      # about 2 min (the criterion study), then figures, tables, results
./.venv/bin/python -m rq4          # about 30 s; RQ-E-4.6 also reads rq1_rq3/data/
```

One step at a time: `python -m rq1_rq3 criterion|figures|tables|results`, `python -m rq4 figures|tables|results`.
To update the thesis, copy `*/outputs/figures/*.pdf` to its `plots/` folder and `*/outputs/tables/*.tex` to its
`tableaux/` folder: the files have the names, captions and labels that the thesis includes.

The outputs in the repository are those of the thesis: every table is byte-identical to the thesis version and
every figure is drawn from the same data with the same code.

| Thesis                        | Figures                                                                   | Tables                           | `results.md`                           |
| :---------------------------- | :------------------------------------------------------------------------ | :------------------------------- | :------------------------------------- |
| RQ-E-1.1 Normality            |                                                                           |                                  | rejection rates, skewness, kurtosis    |
| RQ-E-1.2 Geometry             | `rq-e-1_2_ecdf_gemms`, `rq-e-1_2_geometry`                                |                                  |                                        |
| RQ-E-1.3 Lower tail           |                                                                           | `RQ-E-1.3-mi210_left_tail`       | means per work size, head vs rest test |
| RQ-E-1.4 Location             | `rq-e-1_4_estimateur_loc`                                                 |                                  | Delta mu vs Delta m                    |
| RQ-E-1.5 Dispersion           | `rq-e-1_5_estimateur_disp`, `rq-e-1_5_disp_delta`                         |                                  | CV vs RCV_OQAD drift                   |
| RQ-E-1.6 Degeneration         | `rq-e-1_6_degeneration_v100`                                              | `RQ-E-1.6-seuils-quantification` | MAD vs OQAD                            |
| RQ-E-2.1, 2.2 Clocks, harness | `rq-e-2_1_clocks`, `rq-e-2_2_setup`                                       |                                  | factor effects                         |
| RQ-E-2.3, 2.4 Reproducibility |                                                                           | `RQ-E-2.3-...`, `RQ-E-2.4-...`   | factor effects on the drifts           |
| RQ-E-2.5 Cost                 |                                                                           | `RQ-E-2.5-rq2_cout_temporel`     | total hours                            |
| RQ-E-3.1, 3.2 Convergence     | `rq-e-3_batch_evolution`, `rq-e-3_convergence_profiles`                   |                                  |                                        |
| RQ-E-3.3 to 3.6 Criterion     |                                                                           | `RQ-E-3.3` to `RQ-E-3.6`         | SMS+ vs fixed budgets                  |
| RQ-E-4.1, 4.2 Cost, guarantee | `rq-e-4_1_cout`, `rq-e-4_2_echecs`                                        |                                  | paired cost, non-inferiority           |
| RQ-E-4.3 to 4.5               |                                                                           | `RQ-E-4.3` to `RQ-E-4.5`         | targeted tests                         |
| RQ-E-4.6 Online measurement   | `rq-e-4_6_batch_evolution_sms_corpus`, `rq-e-4_6_acceleration_sms_corpus` |                                  | acceleration tests, control run        |

## Run the experiments

Requirements: CMake 3.15 or later, clang++ and lld, and ROCm (rocBLAS, amd-smi) or CUDA 12 (cuBLAS). One build
gives the binaries of both experiments in `bin/`:

```bash
cmake --preset release-hip && cmake --build build/release-hip      # NVIDIA: release-cuda
```

| Binary                       | Experiment     | Source                                                                            |
| :--------------------------- | :------------- | :-------------------------------------------------------------------------------- |
| `bin/baseliner-blas-rq1_rq3` | main corpus    | blas-baseliner branch `w-option`, Baseliner 1.0                                   |
| `bin/baseliner-blas-rq4`     | SMS experiment | blas-baseliner branch `dev-exp` and the SMS criteria of `rq4/stopping_criterion/` |

Each binary is built from the exact commits used for the thesis, pinned in `<experiment>/experiment/CMakeLists.txt`.
Then run from the root of the repository (locking the clocks needs `sudo`):

```bash
./rq1_rq3/experiment/amd-experiment.sh    # main corpus: 10 locked then 10 unlocked runs  -> rq1_rq3/data/mi210/raw/
./rq4/experiment/amd-sms-experiment.sh    # SMS experiment: 10 interleaved pairs          -> rq4/data/mi210/raw/
./rq4/experiment/amd-control.sh           # control run of RQ-E-4.6                       -> rq4/data/mi210/control/raw/
```

The NVIDIA scripts are the `nvidia-*` counterparts (no control run). `BIN=<binary>` before a script runs another
binary. The SMS protocol is generated from the defaults compiled in the binary by
`rq4/experiment/make_sms_protocol.py` (usage in its header).

On another GPU, name the platform folder after it (`data/<gpu>/`) and add the GPU to `PLATFORMS` in
`rq1_rq3/data.py` or `rq4/data.py` (and to `CARD_NICKNAME` in `rq1_rq3/postprocess.py`).

## Statistical methods

`common/stats.py`. Paired comparisons: two-sided Wilcoxon signed-rank test with the Hodges-Lehmann estimate of
the difference and its distribution-free 95 % CI, Holm correction within a family. Guarantee of a stopping
rule: share of traces more than 2 % away from the reference, workload bootstrap (B = 2,000), non-inferiority
when the one-sided 95 % bound of the excess stays below 1 pp. Associations: Spearman correlation with a
workload-bootstrap CI. Every seed is fixed: the outputs are deterministic.
