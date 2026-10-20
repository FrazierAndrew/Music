# Pipeline: source WAV to delivered master

Everything runs at 48 kHz, float, stereo arrays of shape (2, n). Large intermediates go to `work/` (or
`$REMIX_WORK`); outputs to `out/`. Commands run from the repo root.

```
src/<t>.wav
  -> engine/separate.py   work/<t>_harm.npy, work/<t>_perc.npy
  -> engine/analyze.py    tracks/<t>/analysis.json, analysis.png, analysis_log.txt
  -> recipe (engine/render.py runs recipe.main())
       Session: grid + source layers (time-stretched if asked)
       assemble source bars -> layers -> Mixer (LUFS per stem) -> mix-bus edits and section curve
                          work/<TAG>_stem_<name>.npy, work/<TAG>_mix.npy
  -> engine/master.py     (called by render.py)
  -> out/<TAG>.wav (24-bit), out/<TAG>.mp3 (320k), out/<TAG>_check.png, checks on stdout
```

## 1. Separate (`engine/separate.py`)

Median-filter HPSS (Fitzgerald 2010): STFT n_fft 4096, hop 1024; harmonic = median along time (31 frames),
percussive = median along frequency (31 bins); soft mask with power 2. `perc = input - harm`, so the two
layers always sum back to the original. The harmonic layer carries chords, pads and sub; the percussive
layer carries the original drums and transients. It is DSP separation, not a neural stem model: expect some
bleed. Real stems from Andrew would be cleaner.

## 2. Analyze (`engine/analyze.py`, `engine/beats.py`)

- **Tempo and beats.** Onset envelope, a dynamic-programming beat tracker (Ellis 2007), then refinement:
  each beat moved onto the attack, robust local smoothing, and alignment to the averaged high-frequency
  transient of neighbouring beats. Edges outside the reliable span are extrapolated.
- **Grid mode.** Generated audio drifts in tempo by tens of ms, so the default grid follows the drift.
  DAW-made tracks are constant: if a straight grid makes the averaged kick more coherent (by 5%), the
  analyzer uses the straight grid, shifted onto the kick onset. The log prints which one won.
- **Downbeat.** The beat phase (0-3) where chroma and bass changes concentrate.
- **Key.** Krumhansl profiles on the whole-track chroma; `key_rank` lists the best candidates.
- **Per beat:** bass pitch below 200 Hz on the full mix (`beat_bass_midi`) and on the harmonic layer
  (`beat_bass_harm_midi`, preferred: sidechain pumping biases the full-mix estimate).
- **Per bar:** time, length, RMS, band energies (sub, low, lowmid, mid, high, air), stereo width, bass per
  beat, chroma and top pitch classes.
- **Sections.** Novelty peaks over the bar features (checkerboard kernel, 8 bars).
- **Outputs.** `analysis.json` (keys: file, duration, lufs, bpm, beats, downbeat_phase, reliable_beats,
  key_rank, bars, sections, beat_bass_midi, beat_bass_harm_midi), `analysis.png`, and the printed log with a
  bar-by-bar harmony map (save it as `analysis_log.txt`; never pipe it through `head`, see verification.md).

From the log, write the track's harmony map by hand (`recipes/<t>/<t>_harmony.py`): which chord each
source bar plays, voicings for re-synthesis, and chord tones for new melodies.

## 3. Session (`engine.Session`)

`Session(name, analysis_json, harm_npy, perc_npy_or_None, total_bars, stretch=1.0, seed)`:

- The remix grid is strict: `bpm = source bpm x stretch`, `ses.pos(bar, beat)` returns a sample index,
  `ses.span(b0, b1)` a slice. Bars are remix bars (R); source bars (S) are indexed by `ses.src_bar_t[S]`.
- `stretch != 1` time-stretches the source layers once through ffmpeg rubberband (pitch kept) and caches
  them in `work/<name>_<layer>_x<stretch>.npy`. Constant-ratio stretching maps time linearly, so source beat
  times are simply divided by `stretch`.
- `ses.rng` is seeded: placement jitter and velocity randomness are reproducible.

## 4. Arrange

A recipe lists `SECTIONS = [(name, first_remix_bar, n_bars, first_source_bar), ...]` and expands it into
`MAPPING = [(R, S), ...]`. `ses.assemble(layer, MAPPING)` places each source bar at its remix bar on the
strict grid with a 6 ms pre-roll crossfade (contiguous bars) or a 40 ms tail (jumps), so edits land on the
downbeat without clicks. The result (usually from the harmonic layer) is the "bed": his original sound,
re-arranged, before any treatment.

## 5. Layers

Each layer is a function returning a stereo stem the length of the session:

- **Drums and percussion:** `ses.hits(stem, sound, bars, steps, ...)` places a sound on 16th steps with
  swing, velocity, random gain, millisecond jitter and late pushes; returns trigger positions for ducking.
- **Re-synthesized harmony:** chords from the harmony map through `sounddesign` voices (detuned stacks,
  brass, piano, strings, vocoder), placed per chord block (`blocks()`).
- **New melodies:** chord tones only (plucks, horns, vocal chops, bells).
- **Source treatments:** the bed through tape wobble, filters, crushers, reversal, ring mod, blur,
  paulstretch, granular clouds, shimmer.
- **Textures:** synthesized weather and room (rain, creek, birds, thunder, hiss, room tone, vinyl).
- **FX:** risers, downlifters, impacts, reverse swells.

Automation is written in bars: `ses.auto(default).set(b0, b1, v0, v1, shape)`; call `.smooth()` on gain
curves and pass cutoff curves through `sd.smooth_curve()` (see verification.md for why).

## 6. Mix (`engine.Mixer`)

`Mixer(ses, TARGETS, TAG)`. `TARGETS[name] = (lufs, (bar0, bar1))`: each stem is gained so its loudness over
those reference bars hits the target, saved to `work/<TAG>_stem_<name>.npy`, and summed. Pass `gain_db=` to
bypass calibration (FX stems are set by peak). After all stems: mix-bus edits (tape stops, silences before
drops, stutter gates), then a `section` curve in dB for the arrangement's dynamics, then `m.save()`.

Calibration has a side effect: a filter applied before calibration does not make the stem quieter, the
calibration gains it back up. Darken or thin a section with the section curve or with automation applied
after calibration, or choose reference bars outside the treated region.

## 7. Master (`engine/master.py`, called by `render.py`)

1. High-pass 20 Hz (DC from kicks and impacts).
2. Mono below 120 Hz.
3. Glue compressor: threshold = 95th percentile of 400 ms RMS minus 2.5 dB, ratio 1.8, attack 20 ms,
   release 200 ms, 6 dB knee. Only the densest parts get 1-2 dB.
4. Input gain, soft clip at 0.85, look-ahead true-peak limiter with ceiling -1.3 dBTP.
5. The input gain is iterated until loudness over `MASTER_REGION` (the climax bars) is within 0.05 LU of
   `MASTER_TARGET`. Loudness is targeted on the climax, not integrated, so quiet sections keep their contrast.

Targets so far: club styles -8.5 to -9 LUFS over the climax (about -10.5 to -11.7 integrated); ambient -11.5
over the climax (-15.2 integrated). The printed report gives glue and limiter gain reduction; limiter p99
above about 2 dB means the climax is being squashed (lower the target or fix the mix).

## 8. Write and check (`engine/render.py`)

WAV 24-bit and MP3 320k, then the checks in `verification.md`, then `out/<TAG>_check.png` (short-term
loudness arc with section labels, and a spectrogram).

## The 2_5 exception

`recipes/2_5/` predates the engine: one script (`remix.py`) holds its own grid and arrangement, writes
`work/mix_<version>.npy`, and `engine/master.py` run as a script masters it over 2_5's drop (bars 80-96,
via `import remix`). `recipes/2_5/verify.py` has its own checks, including kick and bed grid alignment.
Run it with `bash recipes/2_5/run.sh`. New work should use the engine and `render.py`.
