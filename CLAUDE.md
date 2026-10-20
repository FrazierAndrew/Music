# CLAUDE.md: operating manual for making music with this repo

This repo is how Claude makes music for Andrew. `taste/` says what he likes, `craft/` says how we make it,
`engine/` + `recipes/` do it, `tracks/` and `renders/` record what was done. Read this file first, then the
files it points to for the task at hand.

## Read before making anything

1. [`taste/profile.md`](taste/profile.md): standing preferences. Non-negotiables are marked.
2. The latest entries of [`taste/feedback-log.md`](taste/feedback-log.md): what he said about the last renders.
3. If the request involves an existing track: [`tracks/<track>/README.md`](tracks/) (tempo, key, harmony,
   what makes it special) and its `analysis_log.txt`.
4. [`craft/styles.md`](craft/styles.md) to pick the closest existing style engine as a starting point.

## Ground rules (from Andrew; see taste/profile.md for sources)

- Write with no emojis and no em dashes (in docs, code, commits, messages).
- Never modify source audio; work on copies (`src/` is input only).
- Style emulation only: never reproduce another artist's melodies, lyrics, samples or recordings. Name
  artist-inspired renders `<track>_<artist>_style` (e.g. `ddd2_flume_style`), never "(Artist Remix)".
- His listening is authoritative. Claude cannot hear audio: say so, rely on the objective checks
  ([`craft/verification.md`](craft/verification.md)), and ask for timestamped reactions.
- Remixes must change timbre and texture, not only drums ("way more creative change", 2026-10-19).
- Avoid audible pumping and flattened, over-limited masters unless a style calls for pump on purpose.

## Environment

Python 3 with numpy, scipy, matplotlib; ffmpeg with librubberband and libmp3lame. Nothing else: no pip installs
beyond `requirements.txt`, no DAW, no Suno. Everything is synthesized in code or derived from the source audio.
Run every command from the repo root.

## Workflow: request to delivered render

1. **Clarify only if it changes the build** (style direction, length, which track). Otherwise start and ask
   alongside the first result.
2. **Set up the track** (once per source):
   ```
   mkdir -p src work tracks/<t> && cp <source> src/<t>.wav
   python3 engine/separate.py src/<t>.wav work/<t>                       # work/<t>_harm.npy, work/<t>_perc.npy
   python3 engine/analyze.py src/<t>.wav tracks/<t> work/<t>_harm.npy > tracks/<t>/analysis_log.txt
   ```
   Read `analysis_log.txt` (tempo, grid mode, key, per-bar bass and chroma, sections) and `analysis.png`.
   Write `tracks/<t>/README.md` with the facts and what makes the track special (see `tracks/ddd2/README.md`).
   Write a harmony map (see `recipes/ddd2/ddd2_harmony.py`): chord per source bar, voicings, chord tones.
3. **Choose a style engine** from `craft/styles.md` and copy its recipe to `recipes/<t>/<t>_<style>.py`.
4. **Write the recipe** (anatomy in [`recipes/README.md`](recipes/README.md)): `SECTIONS` (remix bar →
   source bar), bar sets for each part, layer functions, `TARGETS` (stem LUFS), `MASTER_REGION`,
   `MASTER_TARGET`, and the check hooks (`BASS_BARS`, `CHORD_STEMS`, ...).
5. **Render**: `python3 engine/render.py recipes/<t>/<recipe>.py` → `out/<TAG>.wav/.mp3/_check.png` + checks.
   Use `--skip-mix` to re-master without rebuilding stems.
6. **Verify**: read the printed checks against `craft/verification.md` and look at `_check.png` (the loudness
   arc should match the intended shape; the climax is the loudest section). Fix and re-render until clean.
7. **Deliver** the MP3 (listening) and WAV (master) with timestamps of the key moments.
8. **Record**: add a row to `renders/README.md`, attach the audio to a GitHub Release, and log Andrew's
   reaction in `taste/feedback-log.md` when it comes (promote durable patterns into `taste/profile.md`).

## Conventions

- **Grid**: `engine.Session` holds a strict grid. `ses.pos(bar, beat)` gives samples; bars and beats are
  remix positions. Source bars are placed with `ses.assemble(layer, MAPPING)`. `stretch` time-stretches the
  source (0.5 = half speed, 1.25 = 136 → 170 BPM) with pitch kept.
- **Automation**: `ses.auto(default).set(b0, b1, v0, v1, shape)` writes curves in bars. Always `.smooth()`
  gain curves; always pass cutoff curves through `sd.smooth_curve()` before `fx.tv_filter` (jumps click or
  spike; see verification.md).
- **Mixing**: every stem gets a short-term LUFS target over reference bars (`Mixer`). Section dynamics come
  from a mix-bus `section` curve. FX stems are set by peak.
- **Mastering**: loudness is targeted over `MASTER_REGION` (the climax), not integrated, so quiet sections keep
  their contrast. Club styles: -8.5 to -9 LUFS over the climax; ambient: -11.5. Ceiling -1.3 dBTP (for
  release masters see the Spotify note in verification.md).
- **Randomness** is seeded everywhere, so a render is reproducible bit for bit from the source WAV.
- **Naming**: track ids are short (`ddd2`, `2_5`); recipe files `<track>_<style>.py`; `TAG` = the delivered
  file name = the Release asset name. The first seven renders were renamed at delivery (map in
  `recipes/README.md`).

## Pitfalls already paid for (details in craft/verification.md)

Generated audio drifts in tempo (use the tracked grid); DAW tracks are constant (the analyzer picks this
automatically). Bass detection is biased by sidechain pumping. Pitch of retriggered notes must be measured
inside one note. Kick-onset detection fails on time-stretched audio. Cutoff jumps spike block filters. Gain
steps click. LUFS calibration undoes low-pass "darkening". Chroma correlation flags emphasis, not clashes.

## Keeping the repo useful

- New durable preference or reaction → `taste/`.
- New technique, tool, style or lesson → `craft/` (and the code in `engine/`).
- New source track → `tracks/<t>/`. New remix → `recipes/<t>/` + `renders/README.md` + a Release.
- Keep docs short and factual so the next session can act on them.
