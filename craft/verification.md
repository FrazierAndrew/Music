# Verification: reading the checks, and bugs already paid for

Claude cannot listen. `engine/render.py` prints objective checks after every render; they catch defects
(clicks, wrong notes, holes, squashing), not taste. Andrew's listening decides whether it is good.

## The checks, and what passing looks like

Values in brackets are from the delivered renders.

| Printed line | Meaning | Pass |
|---|---|---|
| `length ... LUFS ... TP ... DC ... clipped` | Whole-file integrated loudness, true peak, DC offset, samples at full scale | TP at -1.30 dBTP, DC under 0.001, clipped 0 |
| `mp3: TP` | True peak of the decoded MP3 | Encoding overshoot is normal (-0.76 to -1.23 dBTP); fine for listening copies, see open items |
| `section ... LUFS` | Integrated loudness per section | Follows the plan: climax loudest, breaks and intros clearly lower (Flume-style: drop -8.7, wave 2 -8.5, break -13.1, dissolve -17.0) |
| Master report (`glue_gr_*`, `limiter_gr_*`) | Gain reduction of the glue compressor and of soft clip plus limiter | Glue p95 about 1-2 dB; limiter p99 under about 1.5 dB (Flume-style 1.22, ambient 0.0). Higher means the climax is squashed: lower `MASTER_TARGET` or fix the mix |
| `bass follows original bass line: N/M bars` | Pitch class of the synthesized bass, measured 80 ms inside one note mid-bar, against the original bar's root | All bars match (Flume-style 35/35). A mismatch means a wrong chord in the harmony map or a wrong `SRC_OF` |
| `re-synth harmony vs original` | Chroma of `CHORD_STEMS` against `HARMONY_REF` per bar; "energy on pitch classes the original isn't playing" (outside its top 5) | Median under 10% (5-7% so far). Listed bars above 25% deserve a look; so far they were the doubled bass root or a chord change inside the bar. Chroma correlation alone is not a clash test |
| `splice clicks` | 8 kHz+ burst at each bar boundary against its surroundings, versus the same measure at mid-bar | Boundary median about 0 dB, boundary max not above the mid-bar max (Flume-style: +3.2 vs +7.2). A boundary max several dB above the mid-bar reference is a click |
| `octave bands vs own 250-2k` | Tonal balance of original and remix, 25 Hz to 12.8 kHz | No target: read it for surprises. ddd2 rolls off steeply above 3 kHz, so a lifted top end is intended; a missing sub (25-50 Hz well below the original in a drop-led style) is a problem |
| `out/<TAG>_check.png` | Short-term loudness arc with section labels, spectrogram | The arc matches the intended shape; no unplanned holes (below about -25 LUFS short-term) or spikes; no stray full-band lines in the spectrogram (clicks) |

`recipes/2_5/verify.py` (the first engine) also checks kick and bed alignment to the grid.

Reproducibility: re-rendering from the source WAV must give identical audio. The repo layout was tested on
2026-10-20: `ddd2_flume_style` and `ddd2_flume_ambient` came out bit-exact against the delivered files,
`2_5_remix` identical after the first 0.5 s (the limiter fix below changed the first samples), and both
`analysis.json` files identical.

## Bugs and pitfalls, with where they were found

Analysis and grid:

- **Tempo drift in generated audio** (2_5): beats drift tens of ms from a straight grid, so drums placed on
  a straight grid flam against the bed. Fix: drift-following grid (`beats.track`).
- **Tracker jitter on a DAW track** (ddd2): the drift-following grid wobbled on a constant-tempo track.
  Fix: also fit a straight grid, keep whichever makes the averaged kick more coherent, align it to the
  kick onset. 2_5 picks "tracked" (coherence 0.141 vs 0.008), ddd2 "constant" (0.057 vs 0.005).
- **SIGPIPE** (2_5): `analyze.py ... | head` killed the script before it wrote the JSON. Redirect the log to
  a file instead.
- **Bass pitch biased by sidechain pumping** (2_5): pumping puts amplitude-modulation sidebands around the
  bass, and the full-mix estimate picked them. Fix: estimate on the harmonic layer, snap to the key
  (`Session.root`).
- **False pitch on retriggered notes** (ddd2 A/B/C): a train of retriggered bass notes has a comb spectrum,
  and a previous note's release overlaps the downbeat. Fix: measure 80 ms inside one note, mid-bar.
- **Wrong timing correction on stretched audio** (ddd2 C, ODESZA-style): an onset detector suggested
  stretched layers sat 28 ms late; it was wrong, because stretching smears kick transients. Rubberband's
  constant-ratio stretch maps time linearly (the bed's pumping dip sits at 23.4% of the beat before and
  after). Fix: removed the correction; scale beat times by the stretch.

Mixing and automation:

- **Filter-jump spike** (Flume-style): a high-pass cutoff jumping from 2000 Hz to 20 Hz at a downbeat made
  the block-wise time-varying filter spike to +6.7 dBFS. Fix: `sd.smooth_curve()` on every cutoff curve.
- **Gain-step clicks** (ODESZA-style): a gain that jumps on a sustained sound clicks (a 7.8 dB boundary
  burst in the bed). Fix: `.smooth()` on every gain curve.
- **LUFS calibration undoes darkening**: filtering a stem before `Mixer.add` does not make it quieter; the
  calibration gains it back to its target. Shape sections with the section curve or post-calibration
  automation.

Harmony:

- **Voicing clash** (Flume-style, ODESZA-style): the E brass voicing contained G#, which his E colour does
  not play. Fix: voicings built only from pitch classes in his chroma (`ddd2_harmony.py`).
- **Misleading chroma correlation**: correlation drops when both layers play the same chord with different
  emphasis. Fix: added the out-of-chord energy measure.

Mastering:

- **Limiter edge bug** (found 2026-10-20): reflect-mode edges in the limiter's gain-envelope filter applied
  about 80 dB of gain reduction over the first ~0.1 s of every master. Fix: constant-mode edges. Masters
  made before the fix (`2_5_remix`, A, B, C) carry it; it is inaudible behind their fade-ins.

Arrangement:

- **Half-speed holes** (ambient): source outro bars that are nearly silent, played at half speed, left a
  -25 LUFS hole. Fix: start the ending drone earlier (slow bar 58). The ending then sat near climax level:
  drone high-passed at 140 Hz, cut 5 dB, section gains lowered.

Generation 3 (2026-10-20):

- **Inharmonic resonators** (Glass Tide): glass-bar mode ratios (2.756, 5.404) put 26% of the glass layer's
  energy on pitch classes the pad wasn't playing, including A against his A#. Fix: octave-only modes
  (`voices.TUNED`), 3%.
- **Flat loudness arc** (Aurora, first pass): sustained frozen pads filled every section, so the intro measured
  -13.5 LUFS, the build equalled the peak, and the breakdown sat only 1.8 dB under it. Fix: a steeper section
  curve. The climax is now loudest, the breakdown 4.4 dB under the first peak, the intro at -18.3.
- **Harmony check noise:** harmonics of correct notes count as off-chord energy (a C#'s fifth harmonic is a
  G#). Before changing notes, measure each layer separately and look at which pitch classes are off.

## Open items

- **Spotify true peak.** Applied from `ddd2_glass_tide` on: `MASTER_CEILING = -1.9` gives -2.0 dBTP, Spotify's
  guidance for masters louder than -14 LUFS
  ([Spotify for Artists](https://support.spotify.com/ca-en/artists/article/loudness-normalization/)).
  Earlier renders stay at -1.3 dBTP.
- **Separation quality.** The ONNX MDX-Net models are about 3 dB SDR behind BS-RoFormer on drums and bass, and
  his own stems would beat both (`ROADMAP.md`).
- **No quality signal.** The checks catch defects only; preference has to come from Andrew's A/B choices.
