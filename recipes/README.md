# recipes/: one file per remix

A recipe is a Python module that turns one source track into one render. It holds everything specific to
that render: the arrangement, which parts play where, the sounds, and the mix targets. Shared code lives in
`engine/`; render any recipe with `python3 engine/render.py recipes/<track>/<recipe>.py`.

## Index

| Recipe | Output TAG | Delivered as | Style |
|---|---|---|---|
| `2_5/remix.py` (+ `verify.py`, `run.sh`) | `2_5_remix_<version>` | `2_5_remix` | progressive re-edit (first engine, standalone) |
| `ddd2/ddd2_tidal.py` | `ddd2_tidal` | `ddd2_remix_A_tidal` | melodic techno |
| `ddd2/ddd2_halftime.py` | `ddd2_halftime` | `ddd2_remix_B_halftime` | half-time future bass |
| `ddd2/ddd2_liquid.py` | `ddd2_liquid` | `ddd2_remix_C_liquid` | liquid drum and bass |
| `ddd2/ddd2_flume.py` | `ddd2_flume` | `ddd2_flume_style` | Flume-style sound design |
| `ddd2/ddd2_odesza.py` | `ddd2_odesza` | `ddd2_odesza_style` | ODESZA-style sound design |
| `ddd2/ddd2_flume_ambient.py` | `ddd2_flume_ambient` | `ddd2_flume_ambient` | ambient, from the Flume-style one |
| `ddd2/ddd2_glass_tide.py` | `ddd2_glass_tide` | same | resonance engine (neural stems) |
| `ddd2/ddd2_aurora.py` | `ddd2_aurora` | same | spectral engine (neural stems, 122 BPM) |
| `ddd2/ddd2_undertow.py` | `ddd2_undertow` | same | sampler engine (neural stems, two-step) |

The first renders were renamed at delivery. From now on: TAG = delivered name = Release asset name, and an
artist-inspired style ends in `_style` (never "(Artist Remix)").

`ddd2/ddd2_harmony.py` is not a recipe: it is the track's harmony map (chords per source bar, voicings,
chord tones) plus small helpers. `ddd2/run.sh` rebuilds everything for the track from the source WAV.

Dependency: `ddd2_flume_ambient.py` imports `ddd2_flume.py` (its horn motif and grid) and reads the
Flume-style stems from `work/`, so render `ddd2_flume` first.

## Anatomy

What `engine/render.py` reads from a recipe module:

| Name | Required | Meaning |
|---|---|---|
| `TAG` | yes | Output name: `out/<TAG>.wav`, `work/<TAG>_stem_<name>.npy` |
| `ses` | yes | `engine.Session(...)`: grid, source layers, tempo stretch, seed |
| `SECTIONS` | yes | `[(name, first_remix_bar, n_bars, first_source_bar_or_None), ...]` (labels the checks) |
| `MASTER_REGION` | yes | `(bar0, bar1)` of the climax; loudness is targeted there |
| `main()` | yes | Builds the stems, writes `work/<TAG>_mix.npy` via `Mixer.save()` |
| `MASTER_TARGET` | no | LUFS over `MASTER_REGION` (default -9.0) |
| `BASS_BARS`, `BASS_STEMS`, `SRC_OF` | no | Bass check: which remix bars, which stems, remix bar to source bar |
| `CHORD_STEMS`, `HARMONY_REF`, `CHORD_BARS` | no | Harmony check: re-synthesized stems vs reference stems over these bars |

Conventions inside recipes:

- `MAPPING = [(R, S), ...]` expanded from `SECTIONS`; `SRC_OF = dict(MAPPING)`.
- Bar sets per part (`DRUMS = bars((8, 27), (28, 44))`) say where each part plays; ranges are half-open.
- `MUTE = {(bar, beat), ...}` silences pattern hits (the breath before a drop).
- `CHORD = {R: chord_of_source_bar(S)}` from the harmony map; `blocks(CHORD, bar_set)` groups same-chord bars.
- `TARGETS = {stem: (lufs, (bar0, bar1))}` for `Mixer`.
- Every random generator gets an explicit seed.

## Starting a new recipe

1. Pick the closest engine in `craft/styles.md` and copy it to `recipes/<t>/<t>_<style>.py`.
2. Change the header docstring: what the recipe does to the track, in plain words (future sessions read it).
3. Set `TAG`, the `Session` paths (`tracks/<t>/analysis.json`, `work/<t>_harm.npy`, ...), `stretch`, `seed`.
4. Rewrite `SECTIONS` from `tracks/<t>/analysis_log.txt`, then the bar sets, `MUTE`, `TARGETS`,
   `MASTER_REGION`, and the check hooks.
5. Re-voice melodic parts from `recipes/<t>/<t>_harmony.py`.
6. Render, read the checks (`craft/verification.md`), iterate.
7. Add the recipe to the index above and the render to `renders/README.md`.

Minimal shape:

```python
"""<track>, <style>: what this does to the track, in a few lines.
Usage (repo root): python3 engine/render.py recipes/<t>/<t>_<style>.py
"""
import numpy as np
import dsp, fx, synth, engine
import sounddesign as sd
from engine import Session, Mixer

W = engine.WORK
TAG = "<t>_<style>"
SECTIONS = [("intro", 0, 8, 0), ("drop", 8, 16, 20)]
END = 24
ses = Session("<t>", "tracks/<t>/analysis.json", f"{W}/<t>_harm.npy", f"{W}/<t>_perc.npy", END + 2, seed=1)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]
TARGETS = {"bed": (-16.0, (8, 24)), "kick": (-17.0, (8, 24))}
MASTER_REGION = (8, 24)


def main():
    bed = ses.assemble(ses.harm, MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    kick = ses.stem()
    trig = ses.hits(kick, synth.kick(), set(range(8, 24)), [0, 4, 8, 12])
    m.add("kick", kick)
    m.add("bed", np.asarray(bed) * engine.duck(ses, trig, 3.0))
    m.mix *= dsp.undb(ses.auto(0.0).set(0, 8, -4.0).smooth().v)  # section dynamics
    m.save()
```
