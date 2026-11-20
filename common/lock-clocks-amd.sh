#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <executable_with_args>"
    exit 1
fi

cleanup() {
    echo "Restoring GPU clocks..."
    sudo amd-smi reset -g 0 -d
}

trap cleanup EXIT

echo "Locking GPU clocks to Performance determinism mode @ 1500MHz..."
sudo amd-smi set -g 0 -d 1500

echo "Executing: $@"
"$@"
