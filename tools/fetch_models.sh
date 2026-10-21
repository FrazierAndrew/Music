#!/usr/bin/env bash
# Download the four KUIELab MDX-Net ONNX stem models used by engine/separate_mdx.py into models/ (about 110 MB).
# Source: GitHub release "all_public_uvr_models" of TRvlvr/model_repo (the UVR model repository).
# The weights are not stored in this repo; check their license before any commercial release.
# Usage (repo root): bash tools/fetch_models.sh
set -euo pipefail
mkdir -p models
BASE=https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models
for s in bass drums other vocals; do
  f=models/kuielab_b_$s.onnx
  if [ -s "$f" ]; then echo "have $f"; continue; fi
  curl -fL --retry 2 -o "$f" "$BASE/kuielab_b_$s.onnx"
  echo "got $f"
done
