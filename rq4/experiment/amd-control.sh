#!/usr/bin/env bash
# Control run of RQ-E-4.6 (fixed budgets, corpus vs SMS statistics), clocks unlocked.
set -euo pipefail

BIN="${BIN:-./bin/baseliner-blas-rq4}"
PROTOCOL="rq4/experiment/amd-control-protocol.json"
OUTDIR="rq4/data/mi210/control/raw"

mkdir -p "$OUTDIR"
outfile="${OUTDIR}/$(date +%Y%m%d_%H%M%S)_unlocked.json"
echo ">>> Control run -> $outfile"
"$BIN" run -pf "$PROTOCOL" --output-file "$outfile"
