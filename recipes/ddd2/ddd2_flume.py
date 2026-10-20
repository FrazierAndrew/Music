"""ddd2, Flume-style remix engine: deconstruct and dirty. Style emulation only; every melody, pattern
and sound here is new (synthesized or derived from your track).

Moves (from the research notes): half-time feel on the 136 grid; your chords re-synthesized as wonky
detuned stacks (pitch scoops, slow drift) with filter blooms and a deep pump; metallic FM/ring-mod plucks
on off-grid millisecond timing with OTT; clipped, multiband-distorted drums with late snares and a clean
rim; a granular 'storm' intro with synthesized rain, creek and birds; a vocoded ghost voice; a twinkly
pitch-rise; pitch-scooped amp-distorted horn stabs; a mangled break (bar-reversed, bitcrushed, ring-
modulated, thunder, tape stop); the original pad returning clean before the last drop; your tidal-wave sub
kept but wavefolded for small speakers and stutter-gated at each wave's end; a x4 time-stretched dissolve.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_flume.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
import sounddesign as sd
from engine import Session, Mixer, reverse_swell
from ddd2_harmony import CHORDS, chord_of_source_bar, blocks, reverse_bars, gate_16ths, silence

SR = dsp.SR
W = engine.WORK
TAG = "ddd2_flume"
SECTIONS = [
    ("storm", 0, 8, 0),
    ("verse", 8, 16, 20),
    ("predrop", 24, 4, 48),
    ("drop", 28, 16, 52),
    ("break", 44, 8, 68),
    ("build", 52, 8, 92),
    ("wave", 60, 8, 100),
    ("wave2", 68, 8, 100),
    ("outro", 76, 4, 108),
    ("dissolve", 80, 8, 104),  # S104-105 stretched x4, see dissolve()
]
END = 88
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_harm.npy", f"{W}/ddd2_perc.npy", END + 2, seed=21)
MAPPING = [(r0 + i, s0 + i) for name, r0, nb, s0 in SECTIONS if name != "dissolve" for i in range(nb)]
SRC_OF = dict(MAPPING)
CHORD = {R: chord_of_source_bar(S) for R, S in MAPPING}
CHORD.update({R: "B" for R in range(80, END + 2)})


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


DRUMS = bars((8, 27), (28, 44), (56, 59), (60, 78))
HATS = bars((12, 27), (28, 44), (56, 59), (60, 76))
CHORD_BARS = bars((8, 44), (60, 76))
PLUCK_BARS = bars((12, 24), (28, 44), (68, 76))
SUB_BARS = bars((8, 27), (28, 44))  # synth sub; the original sub carries the waves
WOBBLE_BARS = bars((28, 44))
HORN_BARS = bars((32, 44), (68, 76))
GHOST_BARS = bars((12, 24))
MUTE = {(27, 3), (43, 3), (59, 3), (77, 2), (77, 3)}
BASS_BARS, BASS_STEMS = SUB_BARS, ["sub"]
CHORD_STEMS, HARMONY_REF = ["chords"], ["bed", "orig"]

KICK = synth.kick(f_end=46.25, f_start=180, pitch_tau=0.013, body_tau=0.08, click=0.7, drive=2.2)  # F#1, clipped
SNARE = synth.snare(decay=0.14, tone=200)
SNARE_CRUSH = sd.devil_loc(SNARE)
RIM = sd.rim_click()
HAT = synth.hat(decay=0.03)
PLATE = fx.make_ir(rt60=1.0, predelay=0.012, hi_damp=0.5, seed=71)
HALL = fx.make_ir(rt60=3.5, predelay=0.03, seed=72)
HUGE = fx.make_ir(rt60=6.0, predelay=0.05, hi_damp=0.6, seed=73)

TARGETS = {"bed": (-18.0, (28, 44)), "orig": (-16.0, (60, 76)), "chords": (-17.0, (28, 44)),
           "sub": (-18.0, (28, 44)), "wobble": (-23.0, (28, 44)), "horn": (-22.0, (32, 44)),
           "plucks": (-25.0, (28, 44)), "ghost": (-27.0, (12, 24)), "twinkle": (-23.0, (24, 28)),
           "cloud": (-22.0, (0, 8)), "nature": (-26.0, (0, 8)), "fold": (-23.0, (60, 76)),
           "kick": (-16.5, (28, 44)), "snare": (-20.0, (28, 44)), "hats": (-26.0, (28, 44)),
           "perc": (-28.0, (28, 44)), "shimmer": (-24.0, (55, 60))}
MASTER_REGION = (68, 76)
MASTER_TARGET = -8.5


def speed(x, r):
    n = int(len(x) / r)
    return np.interp(np.arange(n) * r, np.arange(len(x)), x)


def src_span(S0, S1):
    return int(ses.src_bar_t[S0] * SR), int(ses.src_bar_t[S1] * SR)


# ---------------------------------------------------------------- drums

def drums():
    st = {k: ses.stem() for k in ("kick", "snare", "hats", "perc")}
    trig = []
    rng = np.random.default_rng(31)
    for R in sorted(DRUMS):
        trig += ses.hits(st["kick"], KICK, {R}, [0, 7, 10] if R % 2 == 0 else [0, 7, 10, 14], mute=MUTE, jitter_ms=3)
        trig += ses.hits(st["snare"], SNARE, {R}, [8], mute=MUTE, late_ms=15, jitter_ms=4)
        ses.hits(st["snare"], SNARE_CRUSH, {R}, [8], gain=0.5, mute=MUTE, late_ms=15)
        ses.hits(st["snare"], RIM, {R}, [8], gain=0.5, mute=MUTE, late_ms=12)
    for R in sorted(HATS):
        ses.hits(st["hats"], HAT, {R}, [0, 2, 3, 5, 7, 8, 10, 12, 13, 14],
                 vel=[1.0, 0.5, 0.7, 0.45, 0.6, 0.9, 0.55, 0.8, 0.5, 0.65], pan=0.2, swing=0.12, rand=0.15,
                 mute=MUTE, jitter_ms=8)
        tones = CHORDS[CHORD[R]]["tones"]
        for i, s16 in enumerate((3, 11, 14)):  # metallic FM ticks in chord tones
            if (R, int(s16 / 4)) in MUTE:
                continue
            tick = sd.fm_pluck(sd.midi_hz(tones[(R + i) % len(tones)] + 24), length=0.09, index=4.0, ring_mix=0.4)
            ses.add(st["perc"], tick, ses.pos(R, s16 / 4) + int(rng.uniform(-8, 8) * 48), 0.6, pan=(-0.5, 0.5, 0.0)[i])
    for R in (27, 59):  # 1/32 ratchets rising +0 -> +12 st into the silent last beat
        for k in range(24):
            u = k / 23
            ses.add(st["hats"], speed(HAT, 2 ** u), ses.pos(R, k / 8), 0.35 + 0.6 * u, pan=0.2)
    st["snare"] = st["snare"] + 0.18 * fx.reverb(st["snare"], PLATE)
    st["perc"] = st["perc"] + 0.25 * fx.reverb(st["perc"], PLATE)
    drive = ses.auto(0.4).set(28, 44, 0.75).set(60, 78, 0.6).smooth()  # Tri-style drum-bus drive, blended per section
    for k in st:
        st[k] = st[k] * (1 - drive.v) + sd.tri_distort(st[k]) * drive.v
    return st, trig


# ---------------------------------------------------------------- tonal layers

def bloom_env(hits, attack=0.12, decay=0.9):
    env = np.zeros(ses.N)
    L = int((attack + decay * 4) * SR)
    t = np.arange(L) / SR
    shape = np.minimum(t / attack, 1) * np.exp(-np.maximum(t - attack, 0) / decay)
    for h in hits:
        e = min(ses.N, h + L)
        env[h:e] = np.maximum(env[h:e], shape[:e - h])
    return env


def chords(trig):
    main, bright = ses.stem(), ses.stem()
    for R0, nb, c in blocks(CHORD, CHORD_BARS):
        n = ses.pos(R0 + nb) - ses.pos(R0) + int(0.3 * SR)
        m = sd.detuned_stack(CHORDS[c]["pad"], n, voices=9, detune=25, drift=8, scoop=(-120, 0.09), seed=R0)
        b = sd.detuned_stack(CHORDS[c]["bright"], n, voices=5, detune=15, drift=10, scoop=(-120, 0.09), seed=R0 + 1)
        ses.add(main, sd.fade(m, 0.01, 0.3), ses.pos(R0))
        ses.add(bright, sd.fade(b, 0.01, 0.3), ses.pos(R0))
    env = bloom_env([ses.pos(R, b) for R in sorted(CHORD_BARS) for b in (0, 2)])
    main = fx.tv_filter(main, "lowpass", 900 + 2300 * env, q=0.8, stages=2)
    bright = fx.tv_filter(dsp.sos_filter(bright, "highpass", 2500, SR, 2), "lowpass", 3000 + 4000 * env, q=0.8,
                          stages=1)
    y = sd.tube(main + 0.35 * bright, drive=1.6)
    y = y * dsp.undb(ses.auto(0.0).set(60, 68, -6.0).smooth().v)  # first wave: leave room for the original pad
    return y * engine.duck(ses, trig, ses.auto(8.0).set(28, 44, 12.0).set(60, 76, 12.0), release=0.22)


def sub(trig):
    out = ses.stem()
    for R0, nb, c in blocks(CHORD, SUB_BARS):
        length = (ses.pos(R0 + nb) - ses.pos(R0)) / SR + 0.2
        ses.add(out, synth.wave_bass(CHORDS[c]["root"], length, decay_db=4.0 * nb / 4, attack=0.01), ses.pos(R0))
    return out * engine.duck(ses, trig, 10.0, release=0.14)


def wobble(trig):
    out = ses.stem()
    rate = 2 * ses.bpm / 60  # 1/8 notes
    for R0, nb, c in blocks(CHORD, WOBBLE_BARS):
        n = ses.pos(R0 + nb) - ses.pos(R0)
        f = sd.midi_hz(CHORDS[c]["root"] + 12)
        y = sd.saw(f, n) + 0.5 * sd.saw(f * 2 ** (7 / 1200), n, 0.3)
        center = 800 + 400 * np.sin(2 * np.pi * rate * np.arange(n) / SR)
        y = sd.tube(fx.tv_filter(y, "bandpass", center, q=2.0, stages=1, block=32)[0], drive=3.0)
        ses.add(out, sd.fade(y, 0.005, 0.02), ses.pos(R0))
    return out * engine.duck(ses, trig, 8.0, release=0.1)


STAB_NOTES = {"E": [66, 71, 75, 68, 63], "B": [66, 70, 73, 66, 63]}
HORN_A = [(0, 0), (3, 1), (6, 2), (10, 1), (12, 3)]  # (16th step, stab note index): new motif
HORN_B = [(0, 4), (3, 0)]


def horn_note(m, length=0.32):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = sd.midi_hz(m) * 2 ** (-150 * np.exp(-t / 0.04) / 1200)  # pitch scoop up into the note
    y = sd.saw(f * 2 ** (8 / 1200), n) + sd.saw(f * 2 ** (-8 / 1200), n, 0.4) + \
        0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    y = dsp.sos_filter(y, "lowpass", 2600, SR, 2) * np.minimum(t / 0.005, 1) * (0.6 + 0.4 * np.exp(-t / 0.08))
    return sd.fade(sd.amp_sim(y, drive=4.0), 0.002, 0.04)


def horns():
    out = ses.stem()
    for R in sorted(HORN_BARS):
        notes = STAB_NOTES[CHORD[R]]
        for s16, i in (HORN_A if R % 2 == 0 else HORN_B):
            ses.add(out, horn_note(notes[i]), ses.pos(R, s16 / 4), 0.9, pan=0.15 * (-1) ** i)
    return out + 0.25 * fx.reverb(out, PLATE) + 0.3 * fx.pingpong(out, 0.75 * ses.spb / SR, feedback=0.35, taps=4)


def plucks():
    out = ses.stem()
    rng = np.random.default_rng(5)
    gaps = np.array([110, 170, 95, 230]) / 1000  # millisecond-timed arp, not tempo-synced
    for R0, nb, c in blocks(CHORD, PLUCK_BARS):
        t, end, i, idx = ses.pos(R0) / SR, ses.pos(R0 + nb) / SR, 0, 0
        tones = CHORDS[c]["tones"]
        while t < end:
            if not (R0 < 28 and i % 2):
                note = tones[idx % len(tones)] + 12 + 12 * (rng.random() < 0.3)
                ses.add(out, sd.fm_pluck(sd.midi_hz(note)), int(t * SR), rng.uniform(0.5, 1.0),
                        pan=0.7 * np.sin(2 * np.pi * 0.3 * t))
                idx += int(rng.choice([1, 1, 2, -1]))
            t += gaps[i % 4]
            i += 1
    out = sd.ott(out, amount=0.7)
    return out + 0.3 * fx.reverb(out, PLATE)


def ghost():
    out = ses.stem()
    rng = np.random.default_rng(9)
    for R0, nb, c in blocks(CHORD, GHOST_BARS):
        n = ses.pos(R0 + nb) - ses.pos(R0)
        car = sd.detuned_stack([m + 12 for m in CHORDS[c]["pad"][1:]], n, voices=5, detune=10, seed=R0 + 7)
        mod = sd.vowel_noise(n, ["oo", "ah", "ee", "oh"], int(2 * ses.spb), seed=R0)
        eighth = ses.spb / 2
        k = (np.arange(n) / eighth).astype(int)
        accents = rng.choice([0.0, 0.5, 1.0, 1.0], size=k.max() + 1)
        syl = np.sin(np.pi * ((np.arange(n) / eighth) % 1.0)) ** 0.6 * accents[k]
        ses.add(out, sd.vocoder(car, mod * syl), ses.pos(R0))
    out = dsp.sos_filter(dsp.sos_filter(out, "highpass", 300, SR, 2), "lowpass", 8000, SR, 2)
    return fx.widen(out, 1.5) + 0.5 * fx.reverb(out, HALL)


def twinkle():
    out = ses.stem()
    tones = CHORDS["B"]["tones"]
    for k in range(60):  # 16ths across bars 24-27, stopping before the silent beat
        u = k / 63
        f = sd.midi_hz(tones[k % len(tones)] + 12) * 2 ** u  # the whole arp rises an octave
        ses.add(out, sd.fm_bell(f, length=0.5, index=2.0, decay=0.5), ses.pos(24 + k // 16, (k % 16) / 4),
                0.5 + 0.5 * u, pan=0.5 * np.sin(1.7 * k))
    return out + 0.3 * fx.reverb(out, PLATE)


def fold(orig):
    """Your tidal-wave sub, wavefolded into 80-400 Hz harmonics so it reads on small speakers."""
    low = dsp.sos_filter(orig, "lowpass", 110, SR, 4) * ses.auto(0.0).set(60, 76, 1.0).smooth(40).v
    y = dsp.sos_filter(sd.wavefold(low, 2.2), "bandpass", (80, 400), SR, 2)
    return y


# ---------------------------------------------------------------- source treatments and textures

def bed_layers(bed_raw):
    clean = np.asarray(bed_raw, dtype=np.float64)
    tape = dsp.sos_filter(dsp.sos_filter(engine.wobble(clean, depth_cents=25, rate_hz=0.6), "highpass", 300, SR, 2),
                          "lowpass", 9000, SR, 2)
    lofi = sd.tube(dsp.sos_filter(dsp.sos_filter(clean, "highpass", 200, SR, 2), "lowpass", 7000, SR, 2), drive=2.0)
    crushed = sd.bitcrush(reverse_bars(clean, ses, 44, 52), bits=8, hold=4)
    carrier = np.zeros(ses.N)
    for R in range(44, 52):
        sl = ses.span(R, R + 1)
        f = 2.7 * sd.midi_hz(CHORDS[CHORD[R]]["root"] + 24)
        carrier[sl] = np.sin(2 * np.pi * f * np.arange(sl.stop - sl.start) / SR)
    ring = dsp.sos_filter(clean * carrier, "highpass", 300, SR, 2)
    g_tape = ses.auto(0.0).set(0, 8, 1.0).set(8, 9, 1.0, 0.0)
    g_lofi = ses.auto(0.0).set(8, 9, 0.0, 0.55).set(9, 28, 0.55).set(28, 44, 0.45).smooth()
    bed = tape * g_tape.v + lofi * g_lofi.v + crushed * ses.auto(0.0).set(44, 52, 0.8).smooth().v + \
        ring * ses.auto(0.0).set(44, 52, 0.35).smooth().v
    hpf = ses.auto(20.0).set(24, 27.75, 200, 2000, "exp").set(27.75, 28, 2000)
    bed = fx.tv_filter(bed, "highpass", sd.smooth_curve(hpf.v))
    orig = clean * ses.auto(0.0).set(52, 80, 1.0).smooth().v  # the original returns clean for the build and waves
    orig = fx.tv_filter(orig, "lowpass", sd.smooth_curve(ses.auto(21000).set(76, 80, 21000, 4000, "exp").v))
    return bed + 0.12 * fx.reverb(bed, HALL), orig


def dissolve():
    """Final chord time-stretched x4 and low-passed to silence."""
    s0, s1 = src_span(104, 106)
    seg = np.asarray(ses.harm[:, s0:s1], dtype=np.float64)
    st = fx.rubberband(seg, tempo=0.25)
    out = ses.stem()
    a = ses.pos(80)
    n = min(st.shape[1], ses.N - a)
    out[:, a:a + n] = st[:, :n]
    lp = ses.auto(21000).set(80, 88, 8000, 300, "exp").set(88, END + 2, 300)
    out = fx.tv_filter(out, "lowpass", sd.smooth_curve(lp.v)) * \
        ses.auto(0.0).set(80, 81, 0.0, 1.0).set(81, 88, 1.0, 0.0, 1.5).v
    return out + 0.5 * fx.reverb(out, HUGE)


def cloud():
    regions = [(ses.pos(0), ses.pos(8), *src_span(104, 108), 60),
               (ses.pos(44), ses.pos(48), *src_span(68, 72), 90),
               (ses.pos(48), ses.pos(52), *src_span(92, 100), 90),
               (ses.pos(76), ses.pos(80), *src_span(104, 108), 50),
               (ses.pos(80), ses.pos(88), *src_span(104, 108), 140)]
    out = sd.granular(ses.harm, ses.N, regions, grain=(0.03, 0.12), pitches=(0, 12, -12), weights=(0.55, 0.35, 0.1),
                      seed=3)
    out *= ses.auto(1.0).set(80, 88, 1.0, 0.0, 2.0).v
    return out + 0.4 * fx.reverb(out, HALL)


def nature():
    n = ses.N
    th = ses.stem()
    for b in (44, 48):
        ses.add(th, sd.thunder(5.0, seed=b), ses.pos(b), 0.8)
    mix = sd.rain(n, density=70, seed=1) * ses.auto(0.0).set(0, 8, 1.0).set(8, 10, 1.0, 0.0).set(44, 52, 0.8) \
        .set(76, END + 2, 0.6, 1.0).smooth().v
    mix += sd.creek(n, seed=2) * ses.auto(0.0).set(0, 8, 0.6).set(8, 10, 0.6, 0.0).set(80, END + 2, 0.7).smooth().v
    mix += sd.birds(n, rate=0.25, seed=3) * ses.auto(0.0).set(0, 8, 1.0).set(76, END + 2, 1.0).smooth().v
    mix += 0.3 * sd.tape_hiss(n) * ses.auto(0.0).set(0, 8, 1.0).set(44, 52, 1.0).set(80, END + 2, 1.0).smooth().v
    fade_out = ses.auto(1.0).set(84, END + 2, 1.0, 0.0)
    return (mix + th) * fade_out.v


def fx_layer(bed_raw):
    out = ses.stem()
    ses.add(out, synth.riser(8 * 4 * ses.spb / SR, f0=500, f1=12000, seed=81), ses.pos(52), 0.5)
    ses.add(out, synth.riser(4 * 4 * ses.spb / SR, f0=800, f1=9000, seed=82), ses.pos(24), 0.35)
    for b in (28, 60):
        ses.add(out, sd.tube(synth.impact(), drive=3.0), ses.pos(b), 0.9)
        ses.add(out, synth.downlifter(2 * 4 * ses.spb / SR), ses.pos(b), 0.3)
        reverse_swell(ses, out, bed_raw, b, HALL, gain=0.7)
    return out + 0.3 * fx.reverb(out, HALL)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    for k in list(st):
        m.add(k, st.pop(k))
    print("drums done")
    bed, orig = bed_layers(bed_raw)
    m.add("bed", bed)
    m.add("orig", orig)
    m.add("fold", fold(orig) * engine.duck(ses, trig, 4.0, release=0.1))
    sh = sd.shimmer(np.asarray(orig[:, ses.span(52, 60)]), HALL)
    shim = ses.stem()
    shim[:, ses.span(52, 60)] = sh[:, :ses.span(52, 60).stop - ses.span(52, 60).start]
    m.add("shimmer", shim * ses.auto(0.0).set(52, 60, 0.0, 1.0, 2.0).v)
    del bed, sh, shim
    m.add("orig_dissolve", dissolve(), gain_db=m.gains["orig"])
    print("source treatments done")
    m.add("chords", chords(trig))
    m.add("sub", sub(trig))
    m.add("wobble", wobble(trig))
    m.add("horn", horns())
    m.add("plucks", plucks())
    m.add("ghost", ghost())
    m.add("twinkle", twinkle())
    print("tonal layers done")
    m.add("cloud", cloud())
    m.add("nature", nature())
    f = fx_layer(bed_raw)
    m.add("fx", f, gain_db=-9.0 - dsp.db(np.abs(f).max()))
    print("stem gains dB:", m.gains)

    mix = m.mix
    s = ses.span(51.5, 52)  # tape stop out of the break
    mix[:, s] = fx.tape_stop(mix[:, s])
    fxs = np.load(f"{W}/{TAG}_stem_fx.npy")  # pre-drop silences: everything but the fx stem drops out
    g = silence(ses, ses.N, [(27.75, 28), (59.75, 60)])
    mix = (mix - fxs) * g + fxs
    gate = gate_16ths(ses, ses.N, [(R, 2.0, 4.0) for R in (63, 67, 71, 75)])  # stutter-gate each wave's end
    mix *= gate
    T = END + 2
    section = ses.auto(0.0).set(0, 8, -3.0).set(8, 24, -4.0).set(24, 28, -3.5, -2.0).set(28, 44, -1.2) \
        .set(44, 52, -4.0).set(52, 60, -3.0, -1.5).set(60, 68, -1.0).set(76, 80, -2.0).set(80, T, -5.0).smooth()
    m.mix = mix * dsp.undb(section.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
