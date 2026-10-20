#!/usr/bin/env bash
# Rebuild the 2_5 remix (the first, single-script engine): separate -> analyze -> remix -> master -> verify.
# Usage (repo root): bash recipes/2_5/run.sh [path/to/2_5.wav] [version]
set -euo pipefail
SRC=${1:-src/2_5.wav}
VER=${2:-final}
export REMIX_SRC=src/2_5.wav REMIX_WORK=${REMIX_WORK:-work} PYTHONPATH=engine:recipes/2_5
mkdir -p "$REMIX_WORK" out tracks/2_5 src
[ "$SRC" = "src/2_5.wav" ] || cp "$SRC" src/2_5.wav

python3 engine/separate.py src/2_5.wav "$REMIX_WORK/src"
python3 engine/analyze.py src/2_5.wav tracks/2_5 "$REMIX_WORK/src_harm.npy" > tracks/2_5/analysis_log.txt
python3 recipes/2_5/remix.py "$VER"
python3 engine/master.py "$REMIX_WORK/mix_$VER.npy" "out/2_5_remix_$VER" -9.0
python3 recipes/2_5/verify.py "out/2_5_remix_$VER.wav" "$VER" | tee "out/2_5_verify_$VER.txt"
