# Music

Andrew and Claude's music generator: the repository Claude reads before making music with Andrew. It answers
two questions and grows around them:

1. **How Andrew hears music** → [`taste/`](taste/): his stated preferences and every reaction to every render.
2. **What Claude does to make it** → [`craft/`](craft/): methods, engines, checks and research, with the code
   in [`engine/`](engine/) and one file per remix in [`recipes/`](recipes/).

Electronic music only. No DAW and no cloud music generator: Python (numpy, scipy), ffmpeg and onnxruntime turn
a source track into finished, mastered remixes. The goal is music Andrew is obsessed with; the plan for
getting there is in [`ROADMAP.md`](ROADMAP.md).

## Status (2026-10-21)

- Ten renders of two source tracks. Andrew judged the first seven garbage. Three newer ones (resonance,
  spectral and sampler engines built on neural stems) are waiting for his reaction.
- Next: move the system to Andrew's MacBook (real plugins, samples, better separation) and build a fast A/B
  listening loop.

## Layout

| Path | What it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Claude's operating manual: read first |
| [`ROADMAP.md`](ROADMAP.md) | Why the first system failed, what to keep, the next steps, what Andrew can contribute |
| [`taste/`](taste/) | `profile.md` (standing preferences) and `feedback-log.md` (every request and reaction, dated) |
| [`craft/`](craft/) | `pipeline.md` (render stages), `engines.md` (every engine and how it landed), `toolkit.md` (code reference), `verification.md` (checks and lessons), `research/` |
| [`engine/`](engine/) | Shared code: separation, analysis, synthesis, effects, mixing, mastering, rendering |
| [`recipes/<track>/`](recipes/) | One Python file per remix, plus the track's harmony map, stem prep and `run.sh` |
| [`tracks/<track>/`](tracks/) | Analysis data and a fact sheet per source track |
| [`renders/`](renders/) | Catalog of every render: settings, timestamps, reactions |
| [`tools/`](tools/) | `fetch_models.sh` (stem-separation models) |

## Quick start (macOS or Linux)

```
pip install -r requirements.txt        # numpy, scipy, matplotlib, onnxruntime
ffmpeg -filters | grep rubberband      # ffmpeg needs librubberband (and libmp3lame for MP3s)
bash tools/fetch_models.sh             # stem models into models/ (about 110 MB, not in git)
mkdir -p src && cp /path/to/ddd2.wav src/ddd2.wav
bash recipes/ddd2/run.sh               # separation, analysis, stem prep, then the three newest remixes
```

Each render writes `out/<TAG>.wav` (24-bit), `out/<TAG>.mp3` (320k), `out/<TAG>_check.png` and prints its
checks. Large intermediates go to `work/` (or `$REMIX_WORK`).

## Audio

This repository is public and Andrew's source tracks are unreleased, so no audio is committed or attached.
Renders are delivered privately; any of them can be rebuilt bit for bit from the source WAV with its recipe.
If the repository becomes private, renders can be attached to Releases (see
[`renders/README.md`](renders/README.md)).
