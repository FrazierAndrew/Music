# Research: a local remix system on a MacBook

Summary, in our own words, of a web research report run on 2026-10-20 after Andrew asked what a much more
advanced system could look like if it is "just you, me and tooling that can run on my Macbook". Numbers come
from the cited sources; anything the report could not verify is marked as such.

## Conclusions

- The biggest gains come from better inputs and a faster loop, not smarter scripts. That means neural stem
  separation instead of HPSS, and real instruments, effects and samples instead of numpy synthesis. It also
  means a short-clip A/B loop instead of full renders with no feedback.
- No local model reliably predicts what one listener will love. In an independent 2026 test, Meta's
  Audiobox Aesthetics scored a degraded track almost like a polished one and clustered most music between
  7 and 8. Analysis tools tell Claude what is in the audio; Andrew's choices are the objective.
- Generative audio models are optional side tools for material (one-shots, risers, textures), never the
  author, and only if Andrew allows them.

## Components

| Need | Recommended | Notes |
|---|---|---|
| Stem separation | BS-RoFormer (the 6-stem "SW" checkpoint) via python-audio-separator; an MLX port reports about 2x speed | On the MVSep multisong benchmark: about 14.6 dB SDR on bass and 14.1 on drums, against about 12.1 and 11.2 for Demucs htdemucs_ft. The "other" stem stays weakest (about 9). Demucs was archived in January 2025 and lives on in a maintained fork. Community checkpoint licences are unverified. |
| Instruments and effects from code | Spotify Pedalboard (VST3 instruments and effects on macOS, Windows and Linux, Audio Units on macOS, plugin state via `raw_state`); DawDreamer (a Python DAW: plugin graph, automation, MIDI, Faust) | Both GPLv3. Surge XT, Vital and Dexed are free, open source and run on Apple Silicon. Compatibility with each host is unverified, so plan a smoke test. REAPER is a fallback renderer only. |
| Samples | Freesound filtered to CC0 and CC-BY, with an attribution ledger; commercial packs per their EULA; a local library searched by CLAP embeddings | Avoid CC-BY-NC material for anything released. |
| Notes from his tracks | Spotify Basic Pitch on separated stems (Apache-2.0, CoreML on macOS) | Works best on one instrument at a time. |
| Composition help | Anticipatory Music Transformer for infilling and accompaniment (Apache-2.0) | Evidence covers short clips only; Claude-written MIDI must win A/B tests. |
| Beats and structure | Beat This! (ISMIR 2024) | Supports non-CUDA accelerators since v1.1. |
| First-pass mastering | Matchering 2.0.6 (GPLv3) against a reference track | Matches level, spectrum and width; does not fix mixes. |

## Generators (optional, Andrew decides)

| Model | Good for | Licence | Risk of a black box writing the music |
|---|---|---|---|
| Stable Audio Open Small | one-shots and textures up to 11 s | Stability AI Community License | low |
| Stable Audio 3 Small and Medium (May 2026) | longer audio, inpainting, continuation | Community License: registration for commercial use, ends above $1M yearly revenue | medium to high |
| ACE-Step 1.5 (January 2026) | full-song sketches | MIT | high (Suno-like) |
| Magenta RealTime 2 (June 2026) | a playable texture instrument, native on Apple Silicon | Apache-2.0 code, CC BY 4.0 weights | medium |

## The loop

- Listener fatigue is the binding constraint for human-in-the-loop optimization (Takagi's 2001 survey of
  interactive evolutionary computation). Paired comparisons tire people less than ratings.
- The design: pairwise A/B of 8-30 s loudness-matched clips of the same moment, sides randomized, one variable
  changed per pair. Log the choice, confidence (1-3), replays and timestamped notes. Score variants
  Bradley-Terry style, and next ask about the pairs the model is least sure of.
- How fast a one-listener model becomes useful is unknown. A few hundred judgments over 2-4 weeks is a
  hypothesis, not a finding.

## Moments

In Solberg and Dibben (Music Perception, 2019), listeners credited the drop for their peak experiences with
EDM. Drops drew higher skin conductance than the breakdown and build-up around them. So each remix should
have one or two deliberately engineered break routines, with their parameters A/B tested: breakdown
sparseness, build length, pre-drop silence, drop density, low-end re-entry.

## Hardware (estimates from the report, not benchmarks)

| Mac | Works well | Limits |
|---|---|---|
| M1 or M2, 16 GB | separation (slowly), plugins, analysis, Basic Pitch, CLAP, Magenta RT 2 small | no large generators |
| M2 or M3 Pro, 32-36 GB | the above plus Stable Audio Open and 3 Small, smaller ACE-Step | |
| M3 or M4 Max, 64-128 GB | everything | budget 50-150 GB of disk for models, stems and caches |

## Sources

- [Demucs repository (archived)](https://github.com/facebookresearch/demucs) and [maintained fork](https://github.com/adefossez/demucs)
- [MVSep multisong leaderboard](https://mvsep.com/quality_checker/multisong_leaderboard?sort=bass) and [MVSep benchmark paper](https://arxiv.org/html/2305.07489v2)
- [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator), [mlx-audio-separator](https://github.com/ssmall256/mlx-audio-separator)
- [Pedalboard on PyPI](https://pypi.org/project/pedalboard/0.9.25/), [DawDreamer docs](https://dirt.design/DawDreamer/), [DawDreamer compatibility](https://dirt.design/DawDreamer/compatibility.html)
- [Surge XT](https://surge-synthesizer.github.io/), [Vital source](https://github.com/mtytel/vital), [Dexed](https://github.com/asb2m10/dexed)
- [Freesound licences FAQ](https://freesound.org/help/faq/), [LAION CLAP](https://github.com/LAION-AI/CLAP)
- [Basic Pitch](https://github.com/spotify/basic-pitch), [Anticipatory Music Transformer](https://github.com/jthickstun/anticipation), [Beat This!](https://github.com/CPJKU/beat_this/releases)
- [Matchering on PyPI](https://pypi.org/project/matchering/2.0.6/)
- [Cyanite review of Audiobox Aesthetics](https://cyanite.ai/blog/meta-audiobox-aesthetics-review/)
- [Stable Audio Open Small](https://huggingface.co/stabilityai/stable-audio-open-small), [Stable Audio 3 announcement](https://stability.ai/news-updates/meet-stable-audio-3-the-model-family-built-for-artistic-experimentation-with-open-weight-models)
- [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5), [Magenta RealTime](https://github.com/magenta/magenta-realtime)
- [Takagi 2001, interactive evolutionary computation](https://gpbib.pmacs.upenn.edu/gp-html/takagi_2001_ieee.html), [paired-comparison IEC](https://arxiv.org/pdf/0909.2091)
- [Solberg and Dibben 2019](https://eprints.whiterose.ac.uk/id/eprint/145911/)
- [Spotify loudness normalization](https://support.spotify.com/ca-en/artists/article/loudness-normalization/)
