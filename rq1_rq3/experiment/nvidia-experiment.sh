#!/usr/bin/env bash
set -euo pipefail

BIN="${BIN:-./bin/baseliner-blas-rq1_rq3}"
PROTOCOL="rq1_rq3/experiment/nvidia-experiment-protocol.json"
LOCK_SCRIPT="./common/lock-clocks-nvidia.sh"
OUTDIR="rq1_rq3/data/v100/raw"
RUNS=10
PAUSE_SECONDS=$((2 * 60))   # 2 minutes

mkdir -p "$OUTDIR"

TOTAL_RUNS=$((RUNS * 2))
CURRENT_RUN=0

run_once() {
    local locked="$1"   # "locked" or "unlocked"
    local i="$2"

    local ts
    ts=$(date +%Y%m%d_%H%M%S)

    local outfile="${OUTDIR}/${ts}_${locked}.json"

    echo ">>> Run $i ($locked) -> $outfile"

    if [[ "$locked" == "locked" ]]; then
        "$LOCK_SCRIPT" "$BIN" run -pf "$PROTOCOL" --output-file "$outfile"
    else
        "$BIN" run -pf "$PROTOCOL" --output-file "$outfile"
    fi

    CURRENT_RUN=$((CURRENT_RUN + 1))

    if [[ "$CURRENT_RUN" -lt "$TOTAL_RUNS" ]]; then
        echo ">>> Pausing ${PAUSE_SECONDS}s (10 min) before next run..."
        sleep "$PAUSE_SECONDS"
    fi
}

echo "=== Running $RUNS times WITH locked clocks ==="
for i in $(seq 1 "$RUNS"); do
    run_once "locked" "$i"
done

echo "=== Running $RUNS times WITHOUT locked clocks ==="
for i in $(seq 1 "$RUNS"); do
    run_once "unlocked" "$i"
done

echo "All runs complete. Results in $OUTDIR/"