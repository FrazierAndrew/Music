# Toolkit: everything in engine/, by purpose

All functions take and return numpy arrays at 48 kHz (`dsp.SR`). Mono is shape (n,), stereo (2, n); most
effects accept either. Pitches are MIDI numbers unless a name says Hz. Every random source takes a seed.
Read a function's docstring before relying on a parameter.

## Andrew's own moves, and where they are

| His move | Function |
|---|---|
| Tape slowdown | `fx.tape_stop` (to a halt), `fx.rubberband(tempo=)` (half speed, pitch kept), `engine.wobble` (wow) |
| Filter bloom | `fx.tv_filter` with an envelope cutoff (`bloom_env` in `ddd2_flume.py`) |
| Hall reverb | `fx.make_ir(rt60=3-8)` + `fx.reverb` |
| Granular shimmer | `sd.granular`, `sd.shimmer` |
| Vinyl crackle | `engine.lofi_texture` |
| Paulstretch ending | `sd.paulstretch` |

## engine.py: session, arrangement, mixing

| Name | What it does |
|---|---|
| `Session(name, analysis, harm, perc, total_bars, stretch, seed)` | Strict grid + source layers; see `pipeline.md` |
| `ses.pos(bar, beat)`, `ses.span(b0, b1)` | Grid position in samples; slice between bars |
| `ses.stem()` | Empty stereo stem (float32, session length) |
| `ses.add(dst, snd, at, gain, pan)` | Mix a sound into a stem at a sample position (mono sounds are panned) |
| `ses.hits(dst, sound, bars, steps, gain, vel, pan, swing, rand, mute, jitter_ms, late_ms)` | Pattern placement on 16th steps; returns trigger samples |
| `ses.assemble(layer, mapping)` | Source bars to remix bars with click-free crossfades |
| `ses.root(S)` | Majority bass root of source bar S, snapped to the key |
| `ses.auto(default).set(b0, b1, v0, v1, shape).smooth(ms)` | Automation curve in bars (`shape`: "lin", "exp", or an exponent) |
| `Mixer(ses, targets, tag)`, `m.add(name, x, gain_db)`, `m.save()` | LUFS-calibrated stems, saved and summed |
| `duck(ses, triggers, depth_db, release, attack)` | Sidechain gain curve; depth may be an `Auto` |
| `bed_chain(...)` | Blur, HPF/LPF automation, two-band sidechain, width, gain, reverb send (A/B/C recipes) |
| `snare_roll(ses, dst, sound, b0, bars)` | Quarters to 32nds roll with rising pitch |
| `reverse_swell(ses, dst, bed_raw, bar, ir)` | Reversed reverb of the next chord, swelling into the bar |
| `chop(ses, bed_raw, bar, beat, semitones)` | Short pitched slice of the bed with a pluck envelope |
| `wobble(x, depth_cents, rate_hz)` | Tape wow, length kept |
| `lofi_texture(n)` | Vinyl crackle and soft hiss |
| `scale_pcs(key_name)` | Pitch classes of a key from `key_rank` |

## sounddesign.py (`sd`): voices, textures, colour

Oscillators and voices:

| Name | What it does |
|---|---|
| `saw(freq, n)` | Band-limited PolyBLEP saw; `freq` may be a per-sample array |
| `detuned_stack(notes, n, voices, detune, drift, scoop, drift_rates)` | Stereo supersaw chord with slow two-LFO drift and pitch scoops (the wonky chord) |
| `fm_pluck(f, length, ratio, index, ring, ring_mix)` | Metallic FM pluck with ring mod |
| `fm_bell(f, length, ratio, index, decay)` | FM bell or chime |
| `piano_note(m, length, vel, B)` | Additive piano with inharmonic partials |
| `brass(notes, length, attack, cut0, cut1, after, vib_hz, vib_cents)` | CS-80-style brass swell with aftertouch brightening and vibrato |
| `strings_pad(notes, length, attack, release, cutoff)` | Slow detuned string pad |
| `vocal_chop(f, length, vowel, shift, q, breath, vib)` | Formant vocal chop without a singer (vowels in `VOWELS`) |
| `vowel_noise(n, vowels, seg)` + `vocoder(carrier, modulator, bands)` | Vowel-shaped noise as a vocoder modulator: the ghost voice |
| `marching_snare`, `shaker`, `snap`, `rim_click`, `wood` | Organic and drumline percussion |

Time and texture:

| Name | What it does |
|---|---|
| `paulstretch(x, stretch, window_s)` | Extreme time-stretch into a drone (x6 to x20 used) |
| `granular(src, n_out, regions, density, grain, pitches, weights)` | Grain cloud from source regions; region = (out_start, out_end, src_start, src_end[, density]) |
| `rain`, `creek`, `birds`, `thunder`, `tape_hiss`, `room_tone`, `pink`, `brown` | Synthesized field recordings and noise beds |

Colour and dynamics:

| Name | What it does |
|---|---|
| `tri_distort(x, f1, f2, drive)` | 3-band distortion: tanh lows, hard-clip mids, wavefold highs |
| `tube(x, drive, bias)` | Even-harmonic tube saturation |
| `amp_sim(x, drive)` | Guitar amp and cab colour |
| `bitcrush(x, bits, hold)`, `wavefold(x, gain)` | Digital crush; wavefolding (makes a sub audible on small speakers) |
| `decapitator(x, drive_db, mix, tone_hz)` | Parallel vintage drive |
| `devil_loc(x, release)` | Level smasher, for crushed breathing reverb returns |
| `exciter(x, amount_db, hp)` | Top-end air |
| `ott(x, ...)` | Upward + downward multiband compression |
| `shimmer(x, ir, iterations, feedback)` | Octave-up feedback reverb |
| `tape_delay(x, delay_s, feedback, lp, taps, drive)` | Saturating tape echo throws |

Helpers: `fade(y, a, r)`, `pan(x, p)`, `midi_hz(m)`, `smooth_curve(c, ms)` (always use on cutoff curves).

## fx.py: filters, space, time, dynamics

| Name | What it does |
|---|---|
| `tv_filter(x, kind, cutoff, q, stages, block)` | Time-varying biquad (lowpass, highpass, bandpass); cutoff is a scalar or per-sample curve |
| `sweep(n, start, end, shape)` | Cutoff curve |
| `eq_shelf`, `eq_peak` | Static EQ |
| `make_ir(rt60, predelay, hi_damp, width, seed)` + `reverb(x, ir)` | Synthetic stereo reverb (wet only) |
| `pingpong(x, delay_s, feedback, taps, lp)` | Ping-pong delay (wet only) |
| `widen(x, amount)`, `mono_below(x, freq)` | Mid/side width; mono low end |
| `spectral_blur(x, seconds)` | Smears STFT magnitudes over time: removes pumping and transients, keeps chords |
| `rubberband(x, tempo, pitch)` | ffmpeg rubberband time-stretch or pitch-shift |
| `tape_stop(x)`, `stutter(x, start, slice_len, repeats)` | Tape stop; repeat stutter |
| `duck_curve`, `compress`, `soft_clip`, `limiter` | Dynamics (the master uses the last three) |

## synth.py: drums, bass, FX

`kick` (tune with `f_end` in Hz), `clap`, `snare`, `hat`, `open_hat`, `ride`, `rim`, `tom`, `crash`;
`bass_note` (rolling bass), `sub_drone`, `wave_bass` (the ddd2 tidal-wave sub: near-sine, fast attack,
recedes over the note), `reese`, `pluck`; `riser`, `downlifter`, `impact`, `reverse_swell`; `saw`, `midi_hz`.

## dsp.py: I/O and measurement

`load(path)` (any format through ffmpeg, to stereo float32), `save(path, x, codec)` (pcm_s24le or
libmp3lame), `stft`/`istft`/`stft_mag`, `chroma`, `estimate_key`, `sos_filter` (zero-phase Butterworth),
`sos_filter_causal`, `lufs` (BS.1770-4 integrated, gated), `true_peak_db` (4x oversampled), `db`, `undb`.

## Analysis and rendering

- `separate.py`: `hpss(x)` (CLI: `separate.py in.wav work/<t>`).
- `beats.py`: `track(x, bpm_guess)` and its steps; `kick_coherence` decides the grid mode.
- `analyze.py`: CLI `analyze.py in.wav tracks/<t> work/<t>_harm.npy > tracks/<t>/analysis_log.txt`.
- `master.py`: `master(mix, target_lufs, ceiling_db, region)` returns the master and a gain-reduction report.
- `render.py`: CLI `render.py recipes/<t>/<recipe>.py [--skip-mix] [--target LUFS]`.

## Added 2026-10-20 (the three new engines)

| Module | What it does |
|---|---|
| `separate_mdx.py` | Neural 4-stem separation (KUIELab MDX-Net ONNX models via onnxruntime): drums, bass, other, vocals, plus the residual |
| `stems.py` | `load`, `depump` (divides out the beat-synchronous sidechain dip), `extract_hit` (clean one-shots: onset-aligned medians of a retriggered drum), `beat_modulation` |
| `space.py` | `hall_ir` (early reflections, per-band decay, bloom), `convolve`, `send` (band-limited reverb send), `ensemble` (chorus), `width`, `haas` |
| `voices.py` | `ks_pluck` (Karplus-Strong, exact tuning), `resonate` (modal resonator banks: `TUNED`, `GLASS`, `BELL`, `HARMONIC`), `breath_pad` (additive, drifting partials), `fm_bell` |
| `spectral.py` | `chord_spectrum`, `morph_frames`, `freeze` (random-phase resynthesis), `shift`, `tilt`, `band_gate`, `gate_env`, `spectral_delay` |
| `sampler.py` | `capture`, `amp_env`, `filter_env`, `repitch` (by playback speed), `reverse`, `normalize` |

Track prep: `recipes/<t>/<t>_stems.py` (ddd2's is the template) writes the de-pumped bed and the kit.

Lesson from Glass Tide: inharmonic modes (`GLASS`, ratio 2.756) put 26% of the layer's energy off-chord;
octave-only `TUNED` modes brought it to 3%. Use inharmonic modes only for short percussion.

## Per-track helpers (currently in `recipes/ddd2/ddd2_harmony.py`)

`blocks(chord_by_bar, bars)` (group bars into same-chord blocks), `reverse_bars`, `gate_16ths` (stutter
gate), `silence` (pre-drop gaps). They are generic: move them into `engine/` when a second track needs them,
and keep only the chord map in the per-track harmony file.
