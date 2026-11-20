#!/usr/bin/env bash
# Archive of the derived data of both experiments, without the raw reports: enough to reproduce every
# output. Unpack it at the root of the repository: tar xzf derived-data.tar.gz
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-derived-data.tar.gz}"
tar czf "$OUT" --exclude=raw rq1_rq3/data rq4/data
echo "$OUT: $(du -h "$OUT" | cut -f1)"
