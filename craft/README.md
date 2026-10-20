# craft/: what we do to make it

How a render gets made, what tools exist, which style engines exist, and how a render is checked. The code
is in `engine/` (shared) and `recipes/` (one file per remix); these docs explain it.

| File | Read it when |
|---|---|
| [`pipeline.md`](pipeline.md) | You need to know what happens between the source WAV and the delivered master, stage by stage |
| [`toolkit.md`](toolkit.md) | You are writing a recipe and need a sound, effect or helper (everything in `engine/`, by purpose) |
| [`styles.md`](styles.md) | Picking a starting point for a new remix: every style engine so far, its moves, and how it landed |
| [`verification.md`](verification.md) | Reading render checks, or debugging: what each check means, and the bugs already paid for |
| [`research/`](research/) | Background on producer techniques behind the style engines, with sources |

## Principles learned so far

1. **Change the sound, not just the drums.** Andrew's verdict on the first three ddd2 remixes was "just
   drum / beat changes". What changed the result: re-synthesizing his harmony with new instruments, building
   designed textures (weather, granular clouds, vocoded voices), and transforming the source itself
   (reversed, crushed, stretched, folded).
2. **Keep the emotional core.** Identify what he loves in a track (`tracks/<t>/README.md`) and carry it
   through every remix, either kept or rebuilt faithfully. For ddd2 that is the last-drop tidal wave.
3. **Write new parts from his chord tones.** Every melody, chop and stab is new and comes from the track's
   harmony map, never from another artist's work.
4. **Measure what cannot be heard here.** Claude cannot listen; every render gets objective checks, and
   his reaction is the final judge.
5. **Reproducible by default.** Seeded randomness, no hidden state: the same source WAV and recipe give the
   same render, bit for bit.
