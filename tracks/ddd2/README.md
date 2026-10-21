# ddd2 (tame gentle)

Andrew's own song, received 2026-10-19 as `ddd2_-_tame_gentle.wav`. Put it at `src/ddd2.wav` to render.

## Facts (from `analysis_log.txt`)

| | |
|---|---|
| Duration | 199.5 s (3:19), 48 kHz stereo |
| Loudness | -13.97 LUFS integrated, peak -1.03 dBFS |
| Tempo | 136.004 BPM, constant (DAW-made); grid mode "constant" (kick coherence 0.057 vs 0.005 tracked) |
| Bars | 112 (downbeat phase 3), bar = 1.765 s |
| Key | B major (0.84), D# minor close behind (0.78) |
| Spectrum | steep roll-off above 3 kHz: room for new top-end material |

## Harmony (`recipes/ddd2/ddd2_harmony.py`)

- **E**: bass E1, chroma D# F# B A#, no G#: Emaj9(#11) colour.
- **B**: bass B1, chroma B D# F# A#: Bmaj7(add9).
- **D#m**: S68-71, chroma D# F# A# C#, no bass: D#m7.
- From S20 the main sections alternate four bars of E and four bars of B.

## Structure

| Source bars | Time | What happens |
|---|---|---|
| S0-11 | 0:02 | Intro: B pad, B2 bass, very wide (width 1.3-1.4), quiet (about -20 dB RMS), little sub |
| S12-19 | 0:23 | Sub starts to enter on some bars, image narrows |
| S20-43 | 0:37 | First main section: E / B every 4 bars, full sub |
| S44-67 | 1:19 | Second main section, narrower image |
| S68-75 | 2:02 | Breakdown: D#m7 (S68-71) then B (S72-75), no sub |
| S76-91 | 2:16 | Drop: E / B, loudest so far (-11 dB RMS) |
| S92-99 | 2:44 | Pre-wave build on B, sub pulled back |
| **S100-107** | **2:58** | **The last drop, the "tidal wave"**: E1 for 4 bars, then B1 for 4 bars |
| S108-111 | 3:12 | Outro tail, fading |

Analyzer section boundaries: S12, S44, S68, S76, S103.

## What Andrew loves

"I love the emotional intensity behind the sound. Especially the last drop (where that bass comes, it's like
a soft tidal wave, so good)." (2026-10-19)

The wave (S100-107, measured on the source 2026-10-20): a near-sine sub on E1 (41.2 Hz) for four bars, then
B1 (61.7 Hz) for four bars. Each note recedes 11-12 dB over its four bars. On E1 the 2nd harmonic sits
15 dB and the 3rd 22 dB under the fundamental (B1 carries more, about -10 and -14 dB). Attack under 0.1 s,
nearly mono, the loudest sub of the track. `synth.wave_bass` defaults model the E1 note. "Soft" is the
point: it lands, then recedes, rather than punching.

## Rules for every ddd2 remix

- The wave is the climax. Keep his original wave audio, or rebuild it with `synth.wave_bass` at the same
  pitches and recession; never bury it under a new bass.
- Every remix so far plays it twice (S100-107 mapped to two consecutive 8-bar sections).
- Write new melodies from `CHORDS[...]["tones"]` in `ddd2_harmony.py`; re-voice chords from the same map.
- Use the empty top end (3-12 kHz) for new detail: ticks, rims, breaths, rain, air.
- Use the neural stems (`engine/separate_mdx.py`, then `recipes/ddd2/ddd2_stems.py`): the HPSS pad carries
  the old kick and a 2.6-4.2 dB beat pump.
- Recipes: `recipes/ddd2/`. Renders and reactions: `renders/README.md`, `taste/feedback-log.md`.
