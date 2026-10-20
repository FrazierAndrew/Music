# Style engines

A style engine is a recipe whose moves can be reused on another track: copy the recipe, swap the track's
analysis, harmony map and section choices, keep the moves. Timestamps are in the delivered render.
Reactions are quoted in `taste/feedback-log.md`.

## Overview

| Engine (recipe) | Render | Tempo, feel | Character | His reaction |
|---|---|---|---|---|
| `recipes/2_5/remix.py` | `2_5_remix` | 127.5, four on the floor | progressive re-edit: new drums, rolling bass, chops, shimmer | none recorded |
| `ddd2_tidal.py` | `ddd2_remix_A_tidal` | 136, four on the floor | melodic techno, rolling bass and rumble | "just drum / beat changes" (A/B/C) |
| `ddd2_halftime.py` | `ddd2_remix_B_halftime` | 136, half-time | future bass, re-pumped chords, pitched chord chops | same |
| `ddd2_liquid.py` | `ddd2_remix_C_liquid` | 170 (x1.25) | liquid drum and bass, two-step, reese | same |
| `ddd2_flume.py` | `ddd2_flume_style` | 136, half-time | deconstruct and dirty: re-synthesized wonky chords, metallic plucks, weather | **picked over ODESZA-style** |
| `ddd2_odesza.py` | `ddd2_odesza_style` | 124 (x0.912) | recontextualize and enlarge: vocal chops, brass, drumline | not picked |
| `ddd2_flume_ambient.py` | `ddd2_flume_ambient` | 68 (x0.5), no drums | the Flume-style palette slowed into weather and drones | pending |

Two generations so far:

1. **Re-arrange and re-drum** (2_5, A, B, C): his audio, reordered on a strict grid, with new drums, bass,
   chops, risers and automation. Clean and on-grid, but timbre mostly unchanged: rejected as "just drum /
   beat changes".
2. **Re-synthesize and design** (Flume-style, ODESZA-style, ambient): his harmony re-played by new
   instruments (from `ddd2_harmony.py`), new melodies from his chord tones, designed textures, and heavy
   transformation of the source. This is the direction to build on.

## Re-arrange and re-drum

**2_5 progressive re-edit** (`recipes/2_5/remix.py`, the first engine, standalone script). Source bars chosen
from the harmony map: a D/G groove into a pre-drop gap, the strongest G/Bm run for drop 1, the only real
chord movement (D, G, Bm, Em) for the breakdown, D/G drive for drop 2 and outro. New kick, clap, hats, ride,
perc; rolling and growl bass; octave chord chops; shimmer; risers, rolls, impacts; tape stop and stutter
into the bridge; de-pumped, low-passed pads opening the intro. Map: intro 0:00, groove 0:30, build 1:00,
drop 1 1:15, bridge 1:45, breakdown 2:00, drop 2 2:30 (glitch fill 3:01), outro 3:15.

**A, Tidal** (`ddd2_tidal.py`): melodic techno at 136. Rolling bass and rumble drive the first half (bed
through `bed_chain`: blur, filter sweeps, two-band sidechain). A teasing pre-wave, then the rolling bass
stops and his original last-drop wave carries the low end, twice: bare at 2:21, with full drums and octave
chops at 2:35. Shimmer from blurred, octave-up pads.

**B, Halftime** (`ddd2_halftime.py`): half-time future bass on the 136 grid. Chords de-pumped (spectral
blur) then re-pumped by a half-time kick and snare; a wonky pitched chord-chop melody (chops of each bar's
own chord, tape wobble); swung hats with rolls; lo-fi texture; the wave rebuilt as a clean synth sub
(`synth.wave_bass`, same pitch and 4-bar recession as his drop) with a reese crest. Waves at 2:07 and 2:21.

**C, Liquid** (`ddd2_liquid.py`): 170 BPM, source stretched x1.25 with pitch kept. Two-step breakbeat,
rolling legato sub and a moving reese in the first drop; then a 32-bar wave drop where each chord lands as a
sustained tidal sub under a filtered reese crest (1:30 to 2:15).

## Re-synthesize and design

**Flume-style** (`ddd2_flume.py`), the one he picked. Moves, all new material written from his chords:

- Half-time drums on the 136 grid: clipped kick, snare 15 ms late with a crushed copy and a clean rim, hats
  jittered and swung, metallic FM ticks in chord tones; Tri-style 3-band drive blended on the drum bus.
- His chords re-synthesized as 9-voice detuned stacks with slow drift and pitch scoops, low-pass bloom every
  half bar, tube warmth, deep sidechain pump (8 dB, 12 dB in drops).
- Millisecond-timed metallic FM plucks through OTT; pitch-scooped, amp-driven horn stabs (a new motif);
  a 1/8 wobble bass; a vocoded vowel "ghost" voice; a twinkly arp rising an octave into the drop.
- Weather and grain: granular clouds of his harmony, synthesized rain, creek, birds, thunder, tape hiss.
- Source transformations: tape-wobbled intro, lo-fi bed, a break that is bar-reversed, bitcrushed and
  ring-modulated with a tape stop out, the original pad returning clean (with shimmer) for the build.
- The tidal wave kept as his original audio, plus wavefolded 80-400 Hz harmonics so it reads on small
  speakers, and a 1/16 stutter gate on the last half bar of each 4-bar wave.
- Silent last beat before each drop; the final chord stretched x4 and low-passed into a dissolve.

Map: storm 0:00, verse 0:14, pre-drop 0:42, drop 0:49, break 1:18, build 1:32, wave 1:46, wave 2 2:00,
outro 2:14, dissolve 2:21.

**ODESZA-style** (`ddd2_odesza.py`):

- Tempo eased 136 to 124 with pitch kept; a half-time organic pocket (saturated clap and snap, swung
  shakers, toms) and marching-snare drumline builds with flams.
- A new pitched-up formant vocal-chop hook from his chord tones, with breath transients and tape-delay
  throws; CS-80-style brass swells with aftertouch vibrato, chord changes pushed an 1/8 early in builds;
  additive piano and FM chimes for intimate parts; slow strings.
- Decapitator-style grit, an exciter ramped into the drops for air, a Devil-Loc-crushed reverb return
  pumping under; tape hiss and room tone as a "memory" bed; gentle sidechain.
- The tidal wave kept whole, with 2nd-harmonic warmth so it translates.

Map: memory 0:00, verse 0:15, drumline 0:46, drop 1:02, strip 1:33, breakdown 1:41, final build 1:56,
wave 2:12, wave 2 2:27, outro 2:43, coda 2:50.

**Flume-style ambient** (`ddd2_flume_ambient.py`), built from the Flume-style one at his request:

- Half speed with pitch kept (68 BPM grid, 3.53 s bars), no drums; a soft heartbeat (lub-dub every slow bar)
  under the wave.
- The same palette slowed: wonky chords with per-chord blooms over seconds, ghost voice one syllable per
  beat, plucks three times slower, the horn motif as long swells, a slow twinkle return with shimmer.
- Paulstretch drones: the intro pad x6 under the rain, the Flume-style drop (chords, horns, wobble, plucks,
  from that render's stems) x10 as a "memory" in the dissolve, and the final chord x20 as the ending.
- Weather: rain, creek, birds, distant thunder, vinyl; a reversed, crushed "weather" section ending in a long
  tape slowdown into near-silence; spray washes on each wave crest.

Map: rain 0:00, bloom 0:42, weather 1:39, return 2:07, tidal 2:35, tidal 2 3:04, ebb 3:32, dissolve 3:46.

## Reusing an engine on a new track

1. Analyze the track and write its harmony map (`pipeline.md` step 2).
2. Copy the recipe to `recipes/<t>/<t>_<style>.py`; change `TAG`, the `Session` paths, `SECTIONS` (pick
   source bars from the harmony map: chord movement for breaks, strongest runs for drops, the track's
   signature moment for the climax), the bar sets, kick tuning (`f_end` = the key's root around 45-62 Hz)
   and `TARGETS` reference bars.
3. Keep the moves; re-voice them from the new chord tones. Render and read the checks.

Ideas not built yet: a darker, more fringe/underground engine (he mentioned interest in underground EDM);
using his own stems instead of HPSS separation; a vocal engine if he wants vocals.
