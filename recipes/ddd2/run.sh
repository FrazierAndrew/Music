#!/usr/bin/env bash
# Rebuild ddd2 renders from the source WAV: separate -> analyze -> render each recipe (each masters + self-checks).
# Usage (repo root): bash recipes/ddd2/run.sh [path/to/ddd2.wav] [recipe ...]
#   e.g. bash recipes/ddd2/run.sh src/ddd2.wav ddd2_flume ddd2_flume_ambient
# ddd2_flume_ambient reuses ddd2_flume's stems from work/, so render ddd2_flume first.
set -euo pipefail
SRC=${1:-src/ddd2.wav}
shift || true
RECIPES=${*:-"ddd2_tidal ddd2_halftime ddd2_liquid ddd2_flume ddd2_odesza ddd2_flume_ambient"}
export REMIX_WORK=${REMIX_WORK:-work}
mkdir -p "$REMIX_WORK" out tracks/ddd2 src
[ "$SRC" = "src/ddd2.wav" ] || cp "$SRC" src/ddd2.wav

python3 engine/separate.py src/ddd2.wav "$REMIX_WORK/ddd2"
python3 engine/analyze.py src/ddd2.wav tracks/ddd2 "$REMIX_WORK/ddd2_harm.npy" > tracks/ddd2/analysis_log.txt
for r in $RECIPES; do
  python3 engine/render.py "recipes/ddd2/$r.py" | tee "out/${r}_check.txt"
done
