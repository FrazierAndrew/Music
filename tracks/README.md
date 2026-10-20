# tracks/: facts about each source track

One folder per source track, named by a short id. The audio itself lives in `src/<id>.wav` (gitignored).

| Track | Source | What it is |
|---|---|---|
| [`ddd2/`](ddd2/) | `ddd2_-_tame_gentle.wav`, Andrew's own song | 136 BPM, B major, 3:19; the last-drop "tidal wave" is what he loves |
| [`2_5/`](2_5/) | `2_5.wav` | 127.5 BPM (drifting), B minor / D major, 8:48 |

Each folder holds:

- `analysis.json`: the analyzer's output; recipes read it through `engine.Session` (field list in
  `craft/pipeline.md`).
- `analysis_log.txt`: the analyzer's printed summary with the bar-by-bar harmony map. Start here.
- `analysis.png`: the analyzer's plot.
- `README.md`: written by hand. Facts (duration, loudness, tempo, grid mode, key, harmony), structure with
  source bar numbers and times, what Andrew said about the track, and what every remix must keep.

Source bar numbers (S) in all docs and recipes count from the first downbeat the analyzer found (bar 0).
Times are positions in the source file.
