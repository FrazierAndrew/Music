# CLAUDE.md: operating manual

This repo is how Claude makes music for Andrew. `taste/` says how he hears music, `craft/` says how we make
it, `engine/` and `recipes/` do it, `tracks/` and `renders/` record what was done, `ROADMAP.md` says where it
goes next. Read this file first, then what it points to.

## Read before making anything

1. [`taste/profile.md`](taste/profile.md): standing preferences.
2. The latest entries of [`taste/feedback-log.md`](taste/feedback-log.md): his last requests and reactions.
3. [`ROADMAP.md`](ROADMAP.md): where the system stands and the agreed direction.
4. For a track: `tracks/<t>/README.md` (facts, structure, what he loves) and its `analysis_log.txt`.
5. [`craft/engines.md`](craft/engines.md): every engine so far and how he reacted to it.

## Ground rules

- No emojis and no em dashes anywhere: docs, code, commits, messages.
- Electronic music only; lyrics never matter. Vocal-like sounds are texture.
- Never modify source audio (`src/` is input only). Audio never goes into git: the repo is public.
- Style emulation only: never reproduce another artist's melodies, samples or recordings. Name
  artist-inspired renders `<track>_<artist>_style`, never "(Artist Remix)".
- Claude cannot hear. Say so, rely on the checks ([`craft/verification.md`](craft/verification.md)), label
  confidence, and never call something good or bad without evidence. His ears decide.
- Change sound design and texture, not only drums ("way more creative change", 2026-10-19). Keep the track's
  emotional core; for ddd2 that is the last-drop tidal wave.
- Write melodies with intent from the track's own chord tones and motifs, never random notes.
- No pumping or flattening as side effects. The climax is the loudest section; breakdowns sit well below it.

## Environment

Python 3 with numpy, scipy, matplotlib and onnxruntime; ffmpeg with librubberband and libmp3lame. Stem models:
`bash tools/fetch_models.sh`. Run everything from the repo root; intermediates go to `work/` (`$REMIX_WORK`).
The current code was built in a cloud sandbox without pip, plugins or sample libraries; on Andrew's Mac those
limits go away (see `ROADMAP.md`).

## Workflow: request to delivered render

1. **Clarify only what changes the build** (track, direction, length). Otherwise start, and ask alongside the
   first result.
2. **Set up the track** (once per source):
   ```
   mkdir -p src work tracks/<t> && cp <source> src/<t>.wav
   python3 engine/separate.py src/<t>.wav work/<t>          # HPSS layers (the analysis reads these)
   python3 engine/analyze.py src/<t>.wav tracks/<t> work/<t>_harm.npy > tracks/<t>/analysis_log.txt
   python3 engine/separate_mdx.py src/<t>.wav work/<t>      # neural stems: drums, bass, other, vocals
   ```
   Then write `tracks/<t>/README.md`, the harmony map `recipes/<t>/<t>_harmony.py` (chord per source bar,
   voicings, chord tones) and the stem prep `recipes/<t>/<t>_stems.py` (de-pumped pad and a kit recovered
   from his drums; copy ddd2's and set the bars and steps from the analysis).
3. **Choose an engine** from `craft/engines.md` and copy its recipe to `recipes/<t>/<t>_<name>.py`.
4. **Write the recipe** (anatomy and template: [`recipes/README.md`](recipes/README.md)).
5. **Render**: `python3 engine/render.py recipes/<t>/<recipe>.py` (`--skip-mix` re-masters only).
6. **Verify**: read the printed checks and look at `out/<TAG>_check.png`; fix and re-render until clean.
7. **Deliver** MP3 and WAV, one remix at a time when there are several, each with a short doc: what Claude
   thinks he will like and won't (tied to his stated preferences), timestamps, questions.
8. **Record**: a row and a details entry in `renders/README.md`; his request and reaction in
   `taste/feedback-log.md`, quoted. Promote repeated patterns into `taste/profile.md`.

## Conventions

- **Grid**: `engine.Session` is a strict grid. `ses.pos(bar, beat)` gives samples; remix bars (R) are placed
  from source bars (S, counted from the first downbeat) with `ses.assemble(layer, MAPPING)`; `stretch`
  changes tempo with pitch kept.
- **Material**: use the neural stems and the track's prep (`work/<t>_bed_dp.npy`, `work/<t>_kit_*.npy`).
  The HPSS layers leave the original kick and sidechain pump in the pad (measured 2.6-4.2 dB on ddd2).
- **Automation**: `ses.auto(default).set(b0, b1, v0, v1, shape)`; `.smooth()` every gain curve and pass every
  cutoff curve through `sd.smooth_curve()` (jumps click or spike).
- **Mixing**: `Mixer` calibrates each stem to a LUFS target over reference bars; dynamics come from the
  mix-bus `section` curve, applied after calibration.
- **Mastering**: loudness targeted over `MASTER_REGION` (the climax), about -10 to -10.5 LUFS, with
  `MASTER_CEILING = -1.9` (-2 dBTP, Spotify's guidance for loud masters). Limiter p99 under about 2 dB.
- **Tonal resonators** use octave-only modes (`voices.TUNED`); inharmonic modes put energy off-chord.
- **Randomness** is seeded everywhere, so renders reproduce bit for bit.
- **Naming**: track ids are short (`ddd2`, `2_5`); `TAG` = the delivered file name.
- **One fact, one place**: render timestamps and numbers live only in `renders/README.md`.

## Pitfalls already paid for (details in craft/verification.md)

HPSS bleed and baked-in pumping; tempo drift in generated audio versus constant DAW grids; bass detection
biased by pumping; kick onsets smeared by time-stretch; cutoff jumps spiking block filters; gain steps
clicking; LUFS calibration undoing pre-calibration darkening; chroma correlation flagging emphasis instead of
clashes; inharmonic resonator modes; flat loudness arcs when sustained layers fill every section.

## Keeping the repo useful

- New preference or reaction → `taste/`. New technique, engine or lesson → `craft/` (code in `engine/`).
- New source track → `tracks/<t>/` and `recipes/<t>/`. New render → `renders/README.md`.
- Keep docs short and factual so the next session can act on them.
