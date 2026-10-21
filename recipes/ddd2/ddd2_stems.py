"""ddd2 stem prep for the neural-stem recipes (glass_tide, aurora, undertow): run once after separate_mdx.py.

Writes to $REMIX_WORK (default work/):
  ddd2_bed_dp.npy      your pad (other + vocals stems) with the old quarter-note sidechain dip divided out
  ddd2_kit_kick_1.npy  your kick on beat 1, ddd2_kit_kick_2.npy your kick on beat 2 (the cleanest),
  ddd2_kit_snare_3.npy your snare on beat 3: each the median of 28 onset-aligned hits from your drum stem
Usage (repo root): python3 recipes/ddd2/ddd2_stems.py
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "engine"))
import stems  # noqa: E402

W = os.environ.get("REMIX_WORK", "work")
HITS = [("kick_1", 0, 0.42), ("kick_2", 4, 0.42), ("snare_3", 8, 0.5)]  # (name, 16th step, length s)
BARS = [(20, 44), (76, 108)]  # source bars where ddd2's groove plays unchanged


def main():
    an = json.load(open("tracks/ddd2/analysis.json"))
    beats = np.array(an["beats"])
    S = stems.load(f"{W}/ddd2", ("drums", "other", "vocals"))
    bed = np.asarray(S["other"], dtype=np.float64) + np.asarray(S["vocals"], dtype=np.float64)
    np.save(f"{W}/ddd2_bed_dp.npy", stems.depump(bed, beats).astype(np.float32))
    bar_t = beats[an["downbeat_phase"]::4]
    spb = float(np.median(np.diff(beats)))
    for name, step, post in HITS:
        times = [bar_t[s] + step * spb / 4 for a, b in BARS for s in range(a, b)]
        hit, corr, n = stems.extract_hit(S["drums"], times, post=post)
        np.save(f"{W}/ddd2_kit_{name}.npy", hit.astype(np.float32))
        print(f"{name}: {n} hits kept, correlation {corr:.2f}")


if __name__ == "__main__":
    main()
