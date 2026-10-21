# Roadmap

Where the system stands, why the first version failed, and the next steps toward music Andrew is obsessed
with. Updated 2026-10-21.

## Why the first system failed (teardown, 2026-10-20)

Andrew called all seven first renders garbage. The engineering was not the bottleneck: renders were
reproducible, checked and cleanly mastered. The inputs and the loop were.

1. **Weak raw material.** HPSS left 2.6-4.2 dB of the original's beat pumping in the pad. Every new sound was
   a from-scratch numpy model: no samples, no plugins.
2. **A blind loop.** Three reactions across seven renders, each render changing dozens of things at once; no
   timestamps, no reference tracks.
3. **Monolithic recipes.** 218-380 lines and 439-810 hand-set numbers per remix, tied to bar numbers; one
   idea cost a full render and a full listen.
4. **Random melodies.** Most new notes were random chord tones.
5. **Taste as prose.** Most of the profile came from earlier chats, not listening, and no code reads it.
6. **The wrong place.** A cloud sandbox: no speakers, no pip, no plugins, none of his files.

The full teardown is a private doc (linked in `taste/feedback-log.md`). The three remixes of 2026-10-20
fixed part of (1): neural stems, de-pumping, a kit from his own drums, designed reverbs, and tuned physical,
spectral and sampled sounds. Points (2) to (6) are open.

## Keep

Reproducibility (bit-exact renders), the defect checks, the mastering chain, the analysis, protecting each
track's emotional core, and never copying another artist's material.

## Next steps (smallest first)

0. **Reactions.** Andrew ranks Glass Tide, Aurora and Undertow, with a timestamp each where it worked and
   where it didn't.
1. **Move to the Mac.** Clone this repo, run Claude Code locally, fetch the models. Upgrade separation to
   BS-RoFormer (python-audio-separator). Smoke-test Surge XT, Vital, Dexed and any plugins he owns through
   Pedalboard or DawDreamer. Rebuild one remix with real instruments; it succeeds if he prefers it blind.
2. **The loop.** A local A/B page plays loudness-matched 8-30 s clips around one moment (usually the drop),
   with one variable changed per pair. It logs choice, confidence, replays and timestamped notes into `taste/`.
3. **Taste data.** 10-20 tracks he's obsessed with, with timestamped moments. Measure their break routines
   (breakdown, build, drop) and use them as target ranges.
4. **Specs.** Replace monolithic recipes with a declarative spec (sections, layers, clips, effect chains,
   automation) and a per-layer render cache, so variants cost seconds instead of minutes.
5. **Musical intelligence.** Transcribe his stems (Basic Pitch), develop his motifs, take groove templates
   from his drums. Generative models only if Andrew decides to allow them.
6. **Preference model.** Turn the A/B data into per-parameter win rates first, then a small model that
   proposes the next experiment.

Tools, numbers and sources behind these steps: [`craft/research/local-mac-system.md`](craft/research/local-mac-system.md).

## What Andrew can do, in order of impact

1. Stems or project exports of his tracks: they beat any separator.
2. 10-20 tracks he's obsessed with, each with 1-3 timestamps and a sentence on the moment.
3. His Mac's chip, RAM and free disk.
4. The plugins and sample packs he owns or would buy.
5. 20-30 minutes a few times a week of A/B listening on one setup (name the headphones or monitors).
6. Decisions: which generators are allowed (none, samples only, inpainting), whether commercial release
   matters (it changes which licences are usable), and whether the repo stays public (it decides where audio
   can live).
7. Reactions in the moment: "worse at 0:12" teaches more than a verdict on the whole track.
