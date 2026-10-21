# Engines

An engine is a recipe whose approach can be reused on another track: copy it, swap in the track's analysis,
harmony map and section choices, and keep its moves. Timestamps and numbers for each render live in
`renders/README.md`; reactions are quoted in `taste/feedback-log.md`.

## Overview

| Engine (recipe) | Render | Pulse | Character | His reaction |
|---|---|---|---|---|
| Re-edit (`recipes/2_5/remix.py`) | `2_5_remix` | 127.5, four on the floor | his bars reordered, new drums, rolling bass, chops, shimmer | garbage (with all of the first seven) |
| Tidal (`ddd2_tidal.py`) | `ddd2_remix_A_tidal` | 136, four on the floor | melodic techno, rolling bass and rumble | "just drum / beat changes", then garbage |
| Halftime (`ddd2_halftime.py`) | `ddd2_remix_B_halftime` | 136, half-time | future bass, re-pumped chords, pitched chord chops | same |
| Liquid (`ddd2_liquid.py`) | `ddd2_remix_C_liquid` | 170 (x1.25) | liquid drum and bass, two-step, reese | same |
| Flume-style (`ddd2_flume.py`) | `ddd2_flume_style` | 136, half-time | re-synthesized wonky chords, metallic plucks, weather | preferred over ODESZA-style, then garbage |
| ODESZA-style (`ddd2_odesza.py`) | `ddd2_odesza_style` | 124 (x0.912) | vocal-chop hook, brass, drumline | not picked, then garbage |
| Flume-style ambient (`ddd2_flume_ambient.py`) | `ddd2_flume_ambient` | 68 (x0.5), no drums | the Flume-style palette slowed into drones and weather | garbage |
| Resonance (`ddd2_glass_tide.py`) | `ddd2_glass_tide` | 136, half-time | tuned resonators and plucked strings rung in the key of his chords | pending |
| Spectral (`ddd2_aurora.py`) | `ddd2_aurora` | 122, four on the floor | his chords' spectra frozen, morphing and pulsing | pending |
| Sampler (`ddd2_undertow.py`) | `ddd2_undertow` | 136, two-step | stabs, chops and sub notes cut from his own stems | pending |

Three generations so far:

1. **Re-arrange and re-drum** (2_5, Tidal, Halftime, Liquid): his audio reordered on a strict grid with new
   drums, bass, chops and risers. Rejected as "just drum / beat changes".
2. **Re-synthesize and design** (Flume-style, ODESZA-style, ambient): his harmony replayed by numpy synths,
   new parts from his chord tones, designed textures. Preferred to generation 1, then called garbage with it.
3. **Neural stems plus one engine per remix** (Resonance, Spectral, Sampler): clean instrument stems
   (`engine/separate_mdx.py`), the old sidechain divided out of his pad, a kit recovered from his drums,
   designed reverbs, and every new tonal sound tuned to his chords. Awaiting his reaction.

## Generation 3 (current)

**Resonance** (`ddd2_glass_tide.py`). Banks of two-pole resonators with octave-only modes, struck by tiny
noise clicks in an arpeggio and, in the drops, by the transients of his original drums. Karplus-Strong plucked
strings play a motif built from his pad's top line (D#6 sighing to C#6), with FM bell sparkle an octave up. An
additive pad with independently drifting partials, grains of his pad an octave and more up, and his last chord
paulstretched as the coda. Half-time drums from his own kick and snare. His wave twice, first alone.

**Spectral** (`ddd2_aurora.py`, source stretched to 122 BPM). Each chord's median spectrum, taken from his
de-pumped pad, is resynthesized with fresh random phases every frame (`spectral.freeze`). The result glides
into each chord change (`morph_frames`) and brightens toward the climax (`tilt`), with an octave halo on top.
In the peaks, six frequency bands are gated to different rhythms (`band_gate`). A bell and string motif runs
through a per-bin spectral delay, and one bar of frozen time precedes the wave. The pulse is four on the
floor, and his bass is gated into eighths in the first peak.

**Sampler** (`ddd2_undertow.py`). One-shots cut from his pad on the first beat of an E, a B and the D#m bar,
with sampler amp and filter envelopes and an octave layer, played in garage patterns. Eighth-note chops of his
top voice are sped up an octave. His own E1 and B1 bass notes replay a rolling two-step line, and his real bass
stem returns under the wave. Shuffled hats, rim ghosts, a shaker, vinyl, and tape slowdowns.

## Generations 1 and 2 (rejected, kept for reference)

**Re-edit and Tidal, Halftime, Liquid.** Source bars chosen from the harmony map (chord movement for
breakdowns, the strongest runs for drops, the wave for the climax). The bed went through a chain of blur,
filter sweeps and a two-band sidechain. Synthesized drums, rolling and growl basses, octave chops, shimmer,
risers, snare rolls, tape stops. Halftime rebuilt the wave as a synth sub (`synth.wave_bass`); Liquid
stretched the source x1.25.

**Flume-style.** Half-time drums: a clipped kick, a late snare with a crushed copy and a clean rim, jittered
hats, and Tri-style drive on the drum bus. His chords as 9-voice detuned stacks with drift, pitch scoops,
filter blooms and a deep pump. Millisecond-timed metallic FM plucks through OTT, a pitch-scooped amp-driven
horn motif, a 1/8 wobble bass, and a vocoded vowel ghost. Synthesized rain, creek, birds and thunder, plus
granular clouds. A reversed, bitcrushed, ring-modulated break and a wavefolded wave with stutter gates.

**ODESZA-style.** Tempo eased to 124. A formant vocal-chop hook from his chord tones with tape-delay throws,
CS-80-style brass with chord changes pushed an eighth early, additive piano and FM chimes. Organic half-time
percussion and marching-snare builds with flams. Decapitator-style grit, an exciter ramped into the drops, and
a crushed reverb return.

**Flume-style ambient.** The Flume-style palette at half speed with no drums. Paulstretch drones (the intro
pad x6, the Flume-style drop x10, the final chord x20), weather, a heartbeat under the wave, and a long tape
slowdown.

Background on the Flume and ODESZA moves: `craft/research/flume-and-odesza.md`.

## Reusing an engine on a new track

1. Set up the track and its stem prep (`CLAUDE.md`, workflow step 2).
2. Copy the recipe to `recipes/<t>/<t>_<engine>.py`. Change `TAG`, the `Session` paths, `SECTIONS` (chord
   movement for breaks, the strongest runs for drops, the track's signature moment for the climax), the bar
   sets, motifs and voicings (from the new harmony map), and the `TARGETS` reference bars.
3. Render and read the checks before delivering.
