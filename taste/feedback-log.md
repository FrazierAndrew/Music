# Feedback log

Every request and reaction, newest last. Quotes are his words (typos fixed). "Read as" is our
interpretation; "Action" is what changed because of it. Render names match `renders/README.md`.

Template:

```
## YYYY-MM-DD: <render or request>
- Said: "<his words>"
- Read as: <our reading>
- Action: <what we changed>
```

## 2026-10-19: first request, track 2_5

- Said: "I wanna build custom workflows with you to make insanely cool electronic songs (I have a bunch
  already, so maybe more so remixes instead of starting from scratch). Given this audio file, respond back
  with an audio file that sounds even cooler"
- Action: built the first engine (separation, beat grid, analysis, new drums and bass, mastering) and
  delivered `2_5_remix`.
- Reaction: none recorded; he moved on to ddd2.

## 2026-10-19: brief for his track ddd2 (tame gentle)

- Said: "Make remixes of this song I made. I love the emotional intensity behind the sound. Especially the
  last drop (where that bass comes, it's like a soft tidal wave, so good)."
- Read as: the last-drop wave (source bars 100-107) is the heart of the track; every ddd2 remix must keep
  it or rebuild it faithfully.
- Action: `ddd2_remix_A_tidal`, `ddd2_remix_B_halftime`, `ddd2_remix_C_liquid`, each built around that wave.

## 2026-10-19: reaction to A, B, C

- Said: "ur previous remixes seem just drum / beat changes. I want sound design and noise change. Way more
  creative change"
- Read as: rearranging his audio under new drums is not a remix to him. Timbre, texture and noise must
  change: re-synthesize his harmony with new instruments, add designed textures, transform the source.
- Action: wrote `ddd2_harmony.py` (his chords as data), `engine/sounddesign.py` (new voices, textures,
  colour effects), and moved to style engines built from research.

## 2026-10-19: request for style engines

- Said: "Create two more remix engines, first one should act as if Flume remixed the song, the second as if
  Odesza remixed the song. Then remix the ddd2 tame file against them"
- Action: researched both producers' techniques (`craft/research/flume-and-odesza.md`), then built
  `ddd2_flume.py` and `ddd2_odesza.py`. Delivered as `ddd2_flume_style` and `ddd2_odesza_style`.

## 2026-10-20: reaction to the style engines

- Said: "I like the flume one. Make an ambient remix based on it."
- Read as: he prefers the Flume-style palette (wonky detuned chords, metallic plucks, dirt, off-grid timing,
  granular weather) over the ODESZA-style one. One comparison, so not a rule yet.
- Action: `ddd2_flume_ambient` (same palette at half speed, no drums, paulstretch drones and weather).

## 2026-10-20: ddd2_flume_ambient

- Reaction: pending.
