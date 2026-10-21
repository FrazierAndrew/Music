# Renders

Every render delivered to Andrew, kept even when he passed on it. This file is the catalog and the only place
render timestamps and numbers are kept. Reactions in full: `taste/feedback-log.md`.

All masters: 48 kHz, WAV 24-bit and MP3 320k. True peak -1.30 dBTP on the WAV up to `ddd2_flume_ambient`, -2.00 dBTP from `ddd2_glass_tide` on (Spotify's guidance for masters louder than -14 LUFS).

## Catalog

| Date | Render | Recipe | Tempo | Length | LUFS (int.) | Reaction |
|---|---|---|---|---|---|---|
| 2026-10-19 | `2_5_remix` | `recipes/2_5/remix.py` | 127.5 | 3:50 | -10.43 | none recorded |
| 2026-10-19 | `ddd2_remix_A_tidal` | `recipes/ddd2/ddd2_tidal.py` | 136 | 3:21 | -10.81 | A/B/C: "just drum / beat changes" |
| 2026-10-19 | `ddd2_remix_B_halftime` | `recipes/ddd2/ddd2_halftime.py` | 136 (half-time) | 2:53 | -10.96 | same |
| 2026-10-19 | `ddd2_remix_C_liquid` | `recipes/ddd2/ddd2_liquid.py` | 170 | 2:30 | -10.82 | same |
| 2026-10-20 | `ddd2_flume_style` | `recipes/ddd2/ddd2_flume.py` | 136 (half-time) | 2:39 | -10.75 | **liked**: "I like the flume one" |
| 2026-10-20 | `ddd2_odesza_style` | `recipes/ddd2/ddd2_odesza.py` | 124 | 3:02 | -11.65 | not picked |
| 2026-10-20 | `ddd2_flume_ambient` | `recipes/ddd2/ddd2_flume_ambient.py` | 68 grid, no drums | 5:04 | -15.20 | all seven above: "garbage" (2026-10-20) |
| 2026-10-20 | `ddd2_glass_tide` | `recipes/ddd2/ddd2_glass_tide.py` | 136 (half-time) | 2:32 | -12.80 | pending |
| 2026-10-20 | `ddd2_aurora` | `recipes/ddd2/ddd2_aurora.py` | 122, four on the floor | 2:53 | -13.86 | pending |
| 2026-10-20 | `ddd2_undertow` | `recipes/ddd2/ddd2_undertow.py` | 136, two-step | 2:32 (music ends 2:28) | -12.62 | pending |

## Where the audio is

Not in this repository: it is public and the source tracks are unreleased. Renders were delivered
privately in chat, and any render can be rebuilt bit for bit from its source WAV (`recipes/<t>/run.sh`).
If the repository goes private, attach `out/<TAG>.wav` and `.mp3` to Releases named `<date>-<batch>`.

## Details

Timestamps are where each section starts in the render.

**`2_5_remix`**: source `2_5`, bars re-arranged on the drift-following grid. Intro 0:00, groove 0:30, build
1:00, drop 1 1:15, bridge 1:45, breakdown 2:00, drop 2 2:30 (glitch fill 3:01), outro 3:15. Master: -9 LUFS
over the first 16 bars of drop 2. Made before the limiter edge fix (inaudible, under the fade-in).

**`ddd2_remix_A_tidal`**: intro 0:00, groove 0:28, build 1:11, drop 1:25, breakdown 1:53, pre-wave 2:07,
wave 2:21, wave 2 (full drums, chops) 2:35, outro 2:49. Master region: wave 2. Before the limiter fix.

**`ddd2_remix_B_halftime`**: intro 0:00, verse 0:14, build 0:42, drop 0:56, drop B 1:25, breakdown 1:39,
pre-wave 1:53, wave 2:07, wave 2 2:21, outro 2:35, coda 2:42. Master region: wave 2. Before the limiter fix.

**`ddd2_remix_C_liquid`**: source stretched x1.25. Intro 0:00, drop 0:23, breakdown 1:08, pre-wave 1:19,
wave 1:30, wave mid 1:42, wave end 2:04, outro 2:16, coda 2:21. Master region: wave mid. Before the
limiter fix.

**`ddd2_flume_style`**: storm 0:00, verse 0:14, pre-drop 0:42, drop 0:49, break 1:18, build 1:32, wave 1:46,
wave 2 2:00, outro 2:14, dissolve 2:21. Master: -8.5 LUFS over wave 2 (limiter p99 1.2 dB). Reproduced
bit-exact from this repo on 2026-10-20.

**`ddd2_odesza_style`**: source stretched to 124 BPM. Memory 0:00, verse 0:15, drumline 0:46, drop 1:02,
strip 1:33, breakdown 1:41, final build 1:56, wave 2:12, wave 2 2:27, outro 2:43, coda 2:50. Master: -9.0
LUFS over wave 2.

**`ddd2_flume_ambient`**: source at half speed, pitch kept. Rain 0:00, bloom 0:42, weather 1:39, return
2:07, tidal 2:35, tidal 2 3:04, ebb 3:32, dissolve 3:46. Master: -11.5 LUFS over tidal 2 (limiter p99
0.0 dB). Reproduced bit-exact from this repo on 2026-10-20.

**`ddd2_glass_tide`** (resonance engine, neural stems): dawn 0:00, verse 0:14 (drums 0:21, motif 0:28), rise 0:42, drop 0:49, deep 1:18, lift 1:32 (tape slowdown 1:38), wave 1:39, wave 2 1:53, ebb 2:07, glass coda 2:14. Master -10.0 LUFS over wave 2, limiter p99 1.4 dB. Doc: https://claude.ai/artifact/USahguJnU9EDLvkyAVbhQ9

**`ddd2_aurora`** (spectral engine, stems stretched to 122 BPM): aurora 0:00, pulse 0:31, peak 1:03, fall 1:34, inhale 1:50, freeze 1:56, wave 1:58, wave 2 2:14, afterglow 2:30, frozen 2:37. Master -10.5 LUFS over wave 2, limiter p99 1.4 dB. Doc: https://claude.ai/artifact/FwaK8ia17QzWKFp1TPdskM

**`ddd2_undertow`** (sampler engine): intro 0:00, groove 0:14, build 0:42, drop 0:49, drop B 1:18, break 1:32, lift 1:46, wave 1:53, wave 2 2:07, outro 2:21 (tape stop 2:27). Master -10.5 LUFS over wave 2, limiter p99 1.8 dB. Doc: https://claude.ai/artifact/8PKzvXmqe4h5sRL9CAyUka

## Adding a render

1. Render: `python3 engine/render.py recipes/<t>/<recipe>.py` (TAG = the name it will be delivered as).
2. Add a catalog row and a details entry here: date, recipe, tempo, length, LUFS, section timestamps,
   master settings, anything unusual.
3. Audio: deliver privately. Only if the repository is private, attach `out/<TAG>.wav` and `.mp3` to a
   Release named `<date>-<batch>` (`gh release create <date>-<batch> out/<TAG>.wav out/<TAG>.mp3`).
4. When Andrew reacts, fill the Reaction column and log it in `taste/feedback-log.md`.
