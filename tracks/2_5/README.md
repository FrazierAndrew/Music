# 2_5

Received 2026-10-19 as `2_5.wav`, the first track remixed in this project. Its origin was not stated; its
tempo drifts like generated audio. Put it at `src/2_5.wav` to render.

## Facts (from `analysis_log.txt`)

| | |
|---|---|
| Duration | 528.5 s (8:48), 48 kHz stereo |
| Loudness | -13.14 LUFS integrated, peak -1.20 dBFS |
| Tempo | 127.52 BPM median, drifting; grid mode "tracked" (kick coherence 0.141 vs 0.008 constant) |
| Bars | 279 (downbeat phase 2), reliable beats 0-1063 of 1122 |
| Key | B minor (0.90), D major close behind (0.81) |

## Harmony and structure

Mostly a G / D vamp (bass G1 and D2) with short B and E passages; energy is nearly flat (-13 to -15 dB RMS
for most of its length), so the remix had to create the contrast.

| Source bars | Time | Used in the remix as |
|---|---|---|
| S139-154 | 4:23 | Breakdown: the only real chord movement (D, G, Bm, Em) |
| S163-178 | 5:08 | Groove |
| S179-186 | 5:38 | Build; S186 is the original's pre-drop gap (sub nearly absent) |
| S187-202 | 5:54 | Drop 1: the strongest G / Bm run |
| S195-210 | 6:09 | Intro (de-pumped, low-passed) |
| S203-210 | 6:24 | Bridge |
| S211-234 | 6:39 | Drop 2: D / G drive |
| S235-250 | 7:24 | Outro |

Analyzer section boundaries: S23, S51, S83, S127, S143, S155, S179, S191, S210, S235, S251, S263.

## Notes

- The drifting tempo is why the analyzer's drift-following grid exists (`craft/verification.md`).
- No reaction from Andrew is recorded for this remix.
- Recipe: `recipes/2_5/` (the first, standalone engine; run with `bash recipes/2_5/run.sh`).
