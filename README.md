# music-generator

Andrew and Claude's music generator. No DAW and no AI music generator: Python (numpy, scipy, matplotlib) and
ffmpeg turn a source track into finished, mastered remixes. The repo answers two questions, and it will grow
around them:

1. **How Andrew hears music** → [`taste/`](taste/): what he likes and dislikes, with dated evidence from his
   own reactions to renders.
2. **What we do to make it** → [`craft/`](craft/) (methods, tools, style engines, checks), with the code in
   [`engine/`](engine/) and one file per remix in [`recipes/`](recipes/).

When asked to make music, Claude starts with [`CLAUDE.md`](CLAUDE.md): it is the operating manual for going
from a request to a delivered, verified render with this repo.

## Layout

| Path | What it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Operating manual: workflow, conventions, checklists, pitfalls |
| [`taste/`](taste/) | `profile.md` (standing preferences) and `feedback-log.md` (every reaction, dated) |
| [`craft/`](craft/) | `pipeline.md`, `toolkit.md`, `styles.md`, `verification.md`, `research/` |
| [`engine/`](engine/) | Shared code: separation, analysis, beat grids, synthesis, effects, mixing, mastering, rendering |
| [`recipes/<track>/`](recipes/) | One Python file per remix: which source bars go where, which layers play, mix targets |
| [`tracks/<track>/`](tracks/) | Facts about each source track: analysis data and plot, harmony, what makes it special |
| [`renders/`](renders/) | Catalog of every render (settings, loudness, feedback); the audio is attached to GitHub Releases |

Audio is never committed. Source tracks go in `src/` (gitignored); renders are uploaded as Release assets and
listed in [`renders/README.md`](renders/README.md).

## Quick start

```
pip install -r requirements.txt            # and ffmpeg built with librubberband + libmp3lame
mkdir -p src && cp /path/to/ddd2.wav src/ddd2.wav
bash recipes/ddd2/run.sh src/ddd2.wav ddd2_flume ddd2_flume_ambient
```

Outputs land in `out/`: `<TAG>.wav` (24-bit), `<TAG>.mp3` (320k), `<TAG>_check.png` (loudness arc +
spectrogram), and the printed checks. Large intermediates (separated layers, stems) go to `work/`
(override with `REMIX_WORK=/some/path`).

## Catalog so far

| Track | Remix | Style | Feedback |
|---|---|---|---|
| 2_5 | `2_5_remix` | progressive re-edit, new drums and rolling bass | none yet |
| ddd2 (tame gentle) | `ddd2_remix_A_tidal` | melodic techno | "just drum / beat changes" (set A/B/C) |
| ddd2 | `ddd2_remix_B_halftime` | halftime future bass | same |
| ddd2 | `ddd2_remix_C_liquid` | liquid drum and bass, 170 | same |
| ddd2 | `ddd2_flume_style` | Flume-style sound design | **liked**: "I like the flume one" |
| ddd2 | `ddd2_odesza_style` | ODESZA-style sound design | not chosen |
| ddd2 | `ddd2_flume_ambient` | ambient, built from the Flume-style one | pending |

Details, numbers and download links: [`renders/README.md`](renders/README.md).
