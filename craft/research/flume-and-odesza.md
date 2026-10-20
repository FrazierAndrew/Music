# Research: how Flume and ODESZA transform a track

Summary, in our own words, of a web research report run on 2026-10-19 to design the two style engines
(`recipes/ddd2/ddd2_flume.py`, `recipes/ddd2/ddd2_odesza.py`). Artist interviews name tools and attitudes
but almost never parameter values: every number below comes from third-party recreations or is our own
engineering default, and is labelled "inference" where that matters. How either artist would treat ddd2 is
inference too, from their stated philosophy and documented remixes.

The core finding, which matches Andrew's feedback: the two engines should differ in timbre and texture far
more than in drums. Most of the "creative change" comes from re-synthesizing the harmony and adding
designed texture layers.

## Remix evidence (tempo and key, from Spotify-derived databases and Beatport)

Databases often disagree by 1-2 BPM or by a relative major/minor flip, so treat these as rough.

| Remix | Change |
|---|---|
| Lorde "Tennis Court" (Flume) | tempo about the same (90 to 93-94), reframed in the relative minor, much longer |
| Disclosure "You & Me" (Flume) | same key, 130 to 75 BPM: a full half-time feel change |
| Hermitude "HyperParadise" (Flume) | key kept, tempo kept or slightly up (sources disagree on the original) |
| Hayden James "Something About You" (ODESZA) | about 9% slower (115 to 105) |
| ZHU "Faded" (ODESZA) | tempo unchanged (125), possibly leaning to the relative major |
| Pretty Lights "Lost and Found" (ODESZA) | about the same tempo, relative-major lean (disputed) |

Pattern: Flume either keeps the tempo and re-feels the groove or goes half-time. ODESZA stays within about
-9% to +2% of the source tempo but changes the genre feel completely; in interviews they describe the goal
of a remix as making something entirely different from the original. Both often land on the relative key.

## Flume: what the sources support

- Tools he names: Sylenth1 as his long-time synth, Audio Damage Tri as his favourite distortion, Black Box
  HG-2 tube saturation, Guitar Rig amps on vocals even when little distortion is wanted, Turnado for
  stutters and glitches, The Glue as bus compressor, Ableton reverb (Valhalla occasionally).
- Drums go through clipping or tape saturation (his description).
- He values imperfection and building from rough material, and off-grid "random chaos" in the spirit of
  J Dilla and Flying Lotus so beats feel less machine-made.
- From the Skin era: more sound design and strange textures that stay melodic; alien but with a heartbeat.
- Field recordings around his property during storms (birds, creek, rain); combining granular sounds with
  pop vocals.
- A metallic effect he described: a factory Serum pluck through Ableton's OTT preset, MIDI drawn by hand.
- Reviewers of the "You & Me" remix describe LFO movement, heavy arpeggiated chords and vocoders building a
  "twinkly" pitch rise, a laid-back heavy synthetic bass, a recurring distorted horn figure, and ghostly
  vocals.
- Restraint: if he really likes a part, he leaves it alone.

## ODESZA: what the sources support

- Saturation is central to their sound: Soundtoys Decapitator and Devil-Loc on vocal chops, drums, and
  tracks with big reverb.
- "Air" from Gem Dopamine as a top-end exciter; they avoid OTT on stems because it adds noise and thins the
  low end (the opposite of Flume, who uses OTT on plucks).
- Chops played by hand on Maschine, not tightly on the grid, for a human feel; a hip-hop approach to
  chopping over house and four-on-the-floor beats; Stutter Edit-style chopping.
- Layering: analog-style bass under a synth line with a bright digital top.
- Big brassy synth sweeps in a Blade Runner vein (CS-80 style), with Deckard's Dream and other polysynths.
- Film-score dynamics: intimate moments made more intimate and big moments bigger; surprise, depth, tension.
- Workflow: build a lot, then strip away everything that is not essential.
- Remix philosophy: build a new world around the source, or give a strong piece a gentle touch that makes it
  feel bigger and more open.
- Vocal chops function as the melody instrument (EDMProd's analysis of "Say My Name"); that analysis also
  notes progressions that avoid the tonic, chord changes pushed an 1/8 early in variations, and the same
  progression moved to a new instrument between sections.
- Documented remix moves: vocals pitched up so they read as another singer; deliberately fuzzy, crunchy,
  muffled versions; short strip-downs to beat, vocal and a wisp of synth for a few bars; artificial strings.
- Live shows with a marching drumline.

## Signature checklist as implemented (parameters are inference unless stated)

Flume-style (`ddd2_flume.py`):

| Move | Our parameters |
|---|---|
| Feel | keep 136 grid, half-time drums |
| Chords | 9-voice detuned stacks, +-25 cents, two-LFO drift (0.13 / 0.31 Hz), -120 cent scoop on attacks; low-pass bloom 900 Hz to 3.2 kHz per half bar; bright layer high-passed at 2.5 kHz |
| Pump | sidechain duck 8 dB in verses, 12 dB in drops, 220 ms release |
| Metallic plucks | FM index 6 to 0 over about 400 ms from an operator two octaves up, plus ring mod; arp timed in ms (110/170/95/230), not tempo-synced; OTT after |
| Drums | clipped kick, snare late by 15 ms with a crushed copy and a clean rim, hats jittered 8 ms and swung; Tri-style 3-band drive on the drum bus |
| Pre-drop | 1/32 hat ratchets rising an octave, then a silent last beat |
| Textures | synthesized rain, creek, birds, thunder, tape hiss; granular clouds of his harmony; vocoded vowel "ghost" |
| Horn stab | -150 cent scoop, saws plus square, amp-sim drive, new motif from chord tones |
| Break | bars reversed, 8-bit crush, ring mod, tape stop out |
| Tidal wave | his original sub kept, plus wavefolded 80-400 Hz harmonics; stutter gate on the last half bar of each wave |
| Ending | last chord time-stretched x4 and low-passed |

ODESZA-style (`ddd2_odesza.py`):

| Move | Our parameters |
|---|---|
| Feel | 136 to 124 BPM (-8.8%) with pitch kept; half-time organic pocket |
| Vocal chops | glottal saw through vowel formant resonators (ah/oh/ee), formants shifted +20%, breath transient; new melody from his chord tones; tape-delay throws on phrase ends |
| Brass | two saws per note +-7 cents, 250 ms attack, low-pass 600 Hz to 3 kHz, "aftertouch" brightening and vibrato; chord changes pushed 1/8 early in builds |
| Intimacy | additive piano (inharmonicity B = 0.0004), FM chimes at ratio 3.5 |
| Colour | Decapitator-style parallel drive, Dopamine-style exciter ramped into drops, Devil-Loc-crushed reverb return |
| Drums | saturated clap and snap, swung shakers, toms; marching-snare drumline builds with flams |
| Memory bed | synthesized tape hiss and room tone |
| Sidechain | gentler than Flume-style (2-6 dB per stem) |
| Tidal wave | his sub kept whole with 2nd-harmonic saturation so it translates |

Shared opportunity found in the research: ddd2 rolls off steeply above 3 kHz, so new elements (rims,
shakers, breaths, FM ticks, rain, exciter) should live mostly at 3-12 kHz.

## Do not copy

Emulate processing and attitude, never motifs or recordings:

- Flume: the "Tennis Court" remix lead or hook rhythm, the "You & Me" remix string figure or horn melody,
  the "Never Be Like You" chimes, any Skin or Palaces topline, his actual field recordings, named presets
  used as fixed sound identities.
- ODESZA: the "Say My Name" chop melody or its loop treatment, the "A Moment Apart", "Loyal" or "Bloom" horn
  lines, their drumline cadences, any real vocal samples, their home-video audio.

Write every melody from Andrew's own chord tones (`recipes/<track>/<track>_harmony.py`).

## Disagreements and caveats in the sources

- "Something About You": reviewers say the vocal was pitched up; one outlet says it was re-sung by another
  vocalist.
- "Faded": one outlet calls the remix slower; databases list both at 125 BPM (probably a half-time feel).
- Several tempo and key entries disagree (HyperParadise original tempo, You & Me remix tempo, relative
  major/minor flips).
- Tutorials recreate Flume in Serum or Massive, but his own stated synth is Sylenth1; plugin names in
  tutorials are the authors' choices, not confirmed chains.
- The ODESZA brass quote does not clearly name the synth; CS-80 style is an inference.

## Sources

Artist interviews and features:
- [MusicRadar: Flume interview](https://www.musicradar.com/news/flume-interview)
- [MusicRadar: In pictures, Flume's Sydney studio](https://www.musicradar.com/news/tech/in-pictures-flumes-sydney-studio-597256)
- [WeRaveYou: Flume studio secrets from his Reddit AMA](https://weraveyou.com/tech/flume-studio-secrets-reddit-ama/)
- [Wikipedia: Hi This Is Flume](https://en.wikipedia.org/wiki/Hi_This_Is_Flume)
- [Interview Magazine: Flume](https://www.interviewmagazine.com/music/flume)
- [Complex: Flume interview on Skin](https://complex.com/music/2016/05/flume-interview-skin)
- [VICE: Flume on making beats](https://www.vice.com/en/article/from-the-bedroom-to-the-stadium-aussie-electro-producer-flume-talks-making-beats/)
- [Soundtoys: ODESZA](https://www.soundtoys.com/artist/odesza/)
- [Synth History: interview with ODESZA](https://www.synthhistory.com/post/interview-with-odesza)
- [MusicTech: ODESZA on The Last Goodbye](https://musictech.com/features/interviews/odesza-new-song-the-last-goodbye/)
- [MusicRadar: ODESZA interview](https://www.musicradar.com/news/odesza-interview)
- [SLUG Magazine: interview with ODESZA](https://www.slugmag.com/music/interviews/music-interviews/how-did-i-get-here-an-interview-with-odesza/)
- [Mix: ODESZA's A Moment Apart](https://www.mixonline.com/recording/odesza-s-moment-apart-430648)

Analyses, reviews and recreations:
- [EDMProd: track breakdown of Say My Name](https://www.edmprod.com/track-breakdown-7-odesza-say-name/)
- [EDM Identity: Flume's You & Me remix](https://edmidentity.com/2019/10/03/tbt-flume-disclosure-you-me/)
- [Complex: You & Me (Flume remix)](https://www.complex.com/music/a/khrisd/disclosure-you-me-flume-remix)
- [Earmilk: You & Me (Flume remix)](https://earmilk.com/2013/06/11/disclosure-you-me-flume-remix/)
- [Dancing Astronaut: Something About You (ODESZA remix)](https://dancingastronaut.com/2015/07/hayden-james-something-odesza-remix/)
- [EDMTunes: Something About You (ODESZA remix)](https://www.edmtunes.com/2015/07/27/something-about-you-odesza/)
- [Howl & Echoes: Something About You (ODESZA remix)](https://howlandechoes.com/2015/07/odesza-remix-hayden-james-something-about-you/)
- [Stereofox: Something About You (ODESZA remix)](https://www.stereofox.com/hayden-james-something-about-you-odesza-remix/)
- [Complex: Something About You premiere](https://www.complex.com/music/a/edwin-ortiz/hayden-james-new-song-premiere-something-about-you-odesza-remix)
- [Indie Shuffle: Faded (ODESZA remix)](https://www.indieshuffle.com/zhu-faded-odesza-remix/)
- [Hypebeast: Faded (ODESZA remix)](https://hypebeast.com/2014/6/zhu-faded-odesza-remix)
- [Relentless Beats: five ODESZA remixes](https://relentlessbeats.com/2016/02/5-remixes-by-odesza-that-you-have-to-blast-immediately/)
- [Production Music Live: Flume synth with Sylenth1 (Tennis Court)](https://www.productionmusiclive.com/blogs/news/flume-synth-with-sylenth1-designing-the-sound-from-lorde-tennis-court-flume-remix)
- [SynthCtrl: Never Be Like You breakdown](https://synthctrl.com/blogs/blog/flume-never-be-like-you-feat-kai-breakdown)
- [SynthCtrl: Insane breakdown](https://synthctrl.com/blogs/blog/flume-insane-feat-moon-holiday-breakdown)
- [MusicTech: heavy beats and gritty synths like Flume](https://musictech.com/guides/essential-guide/how-to-create-heavy-beats-gritty-synths-like-flume/)
- [Reverb: the synth sounds of Blade Runner](https://reverb.com/news/the-synth-sounds-of-blade-runner)
- [Equipboard: Flume](https://equipboard.com/pros/flume)
- [Equipboard: ODESZA](https://equipboard.com/pros/odesza)
- [WhoSampled: You & Me (Flume remix)](https://www.whosampled.com/Disclosure/You-&-Me-(Flume-Remix)/)

Tempo and key data:
- [Tunebat: Tennis Court (Flume remix)](https://tunebat.com/Info/Tennis-Court-Flume-Remix-Lorde-Flume/4fnBNNoBiRqDgTTk3ZQo3E)
- [Beatport: You & Me (Flume remix)](https://www.beatport.com/track/you-and-me-feat-eliza-doolittle-flume-remix/8287889)
- [Tunebat: HyperParadise (Flume remix)](https://tunebat.com/Info/HyperParadise-Flume-Remix-Hermitude/1LQiF6aZfnNgxerxWJRbxw)
- [SongBPM: Something About You (ODESZA remix)](https://songbpm.com/@hayden-james/something-about-you---odesza-remix)
- [SongBPM: Faded (ODESZA remix)](https://songbpm.com/@zhu/faded---odesza-remix-1c4d8d8f-6e73-40d2-9add-fbb7431a8647)
- [Beatport: Pretty Lights tracks](https://www.beatport.com/artist/pretty-lights/127456/tracks)
- [Songdata: Say My Name](https://songdata.io/track/1LeItUMezKA1HdCHxYICed/Say-My-Name-by-ODESZA-Zyra)
