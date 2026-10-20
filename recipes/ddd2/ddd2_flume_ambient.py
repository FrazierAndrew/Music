"""ddd2, ambient remix of the Flume-style remix.

Same palette as ddd2_flume.py (wonky detuned chords, metallic FM plucks, granular storm, vocoded ghost voice,
the horn motif, the wavefolded tidal wave), slowed to half speed with pitch kept (68 BPM grid), drums removed,
and opened into space: paulstretch drones (the intro pad, the Flume-style drop, the final chord), synthesized
rain, creek, birds and distant thunder, vinyl and tape, reversed-bar weather with a long tape slowdown into
near-silence, a slow twinkle and shimmer return, a heartbeat under the wave, and a paulstretch ending.
Needs the Flume-style render's stems in work/ (render recipes/ddd2/ddd2_flume.py first) for the drop-memory drone.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_flume_ambient.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
import sounddesign as sd
from engine import Session, Mixer, reverse_swell
from ddd2_harmony import CHORDS, chord_of_source_bar, blocks, reverse_bars, silence
from ddd2_flume import STAB_NOTES, ses as flume_ses  # the horn motif and grid of the Flume-style remix

SR = dsp.SR
W = engine.WORK
TAG = "ddd2_flume_ambient"
SECTIONS = [  # slow bars (68 BPM, 3.53 s); source bars play at half speed
    ("rain", 0, 12, 0),
    ("bloom", 12, 16, 20),
    ("weather", 28, 8, 68),
    ("return", 36, 8, 92),
    ("tidal", 44, 8, 100),
    ("tidal2", 52, 8, 100),
    ("ebb", 60, 4, 108),
    ("dissolve", 64, 20, None),  # paulstretch drones only
]
END = 84
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_harm.npy", None, END + 2, stretch=0.5, seed=31)
MAPPING = [(r0 + i, s0 + i) for name, r0, nb, s0 in SECTIONS if s0 is not None for i in range(nb)]
SRC_OF = dict(MAPPING)
CHORD = {R: chord_of_source_bar(S) for R, S in MAPPING}
CHORD.update({R: "B" for R in range(64, END + 2)})


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


CHORD_BARS = bars((12, 28), (40, 60))
GHOST_BARS = bars((16, 28), (52, 60))
PLUCK_BARS = bars((14, 28), (52, 60))
HEART_BARS = bars((44, 60))
HORN_BARS = bars((52, 60))
BASS_BARS = set()
CHORD_STEMS, HARMONY_REF = ["chords"], ["bed"]

KICK_SOFT = dsp.sos_filter(synth.kick(f_end=46.25, f_start=120, pitch_tau=0.02, body_tau=0.12, click=0.0, drive=1.2),
                           "lowpass", 140, SR, 4)
PLATE = fx.make_ir(rt60=1.4, predelay=0.015, hi_damp=0.5, seed=101)
HUGE = fx.make_ir(rt60=8.0, predelay=0.06, hi_damp=0.55, seed=102)

TARGETS = {"bed": (-17.0, (44, 60)), "chords": (-19.0, (12, 28)), "ghost": (-26.0, (16, 28)),
           "plucks": (-27.0, (14, 28)), "chimes": (-29.0, (0, 12)), "cloud": (-24.0, (0, 12)),
           "nature": (-24.0, (0, 12)), "drone": (-21.0, (0, 12)), "twinkle": (-25.0, (36, 44)),
           "shimmer": (-24.0, (40, 44)), "fold": (-26.0, (44, 60)), "horn": (-25.0, (52, 60)),
           "wash": (-31.0, (44, 60)), "heart": (-29.0, (44, 60)), "memory": (-25.0, (64, 76)),
           "lofi": (-38.0, (0, 12))}
MASTER_REGION = (52, 60)
MASTER_TARGET = -11.5  # ambient: the climax sits here, everything else breathes below it


def src_span(S0, S1, stretched=True):
    """Sample span of source bars in the half-speed layer (or the original-speed layer)."""
    if stretched:
        return int(ses.src_bar_t[S0] * SR), int(ses.src_bar_t[S1] * SR)
    t = np.array(ses.an["beats"])[ses.an["downbeat_phase"]::4]
    return int(t[S0] * SR), int(t[S1] * SR)


def place(dst, y, bar):
    a = ses.pos(bar)
    n = min(y.shape[-1], ses.N - a)
    dst[:, a:a + n] += y[:, :n]


# ---------------------------------------------------------------- the original, slowed

def bed_layer(bed_raw):
    clean = np.asarray(bed_raw, dtype=np.float64)
    pad = engine.wobble(dsp.sos_filter(clean, "lowpass", 3500, SR, 2), depth_cents=18, rate_hz=0.35)
    blur = fx.spectral_blur(clean, 1.2 * ses.spb / SR)  # removes the original's (now slow) pumping
    weather = dsp.sos_filter(sd.bitcrush(reverse_bars(clean, ses, 28, 36), bits=10, hold=3), "lowpass", 4500, SR, 2)
    g = lambda *spans: ses.auto(0.0).set(*spans).smooth(80).v
    bed = pad * ses.auto(0.0).set(0, 12, 1.0).set(12, 13, 1.0, 0.0).smooth(80).v + \
        dsp.sos_filter(blur, "highpass", 90, SR, 2) * ses.auto(0.0).set(12, 13, 0.0, 0.8).set(13, 28, 0.8).smooth(80).v + \
        weather * g(28, 36, 0.8) + \
        (0.6 * blur + 0.4 * clean) * g(36, 44, 1.0) + \
        clean * ses.auto(0.0).set(44, 60, 1.0).set(60, 64, 1.0).smooth(80).v
    bed = fx.tv_filter(bed, "lowpass", sd.smooth_curve(ses.auto(21000).set(60, 64, 21000, 2500, "exp")
                                                       .set(64, END + 2, 2500).v))
    send = ses.auto(0.25).set(0, 12, 0.5).set(12, 28, 0.35).set(28, 36, 0.4).set(36, 44, 0.4).set(60, 64, 0.5).smooth(80)
    return bed + fx.reverb(bed * send.v, HUGE)


# ---------------------------------------------------------------- the Flume-style palette, slowed

def chords():
    out = ses.stem()
    for R0, nb, c in blocks(CHORD, CHORD_BARS):
        n = ses.pos(R0 + nb) - ses.pos(R0) + int(3.0 * SR)
        m = sd.detuned_stack(CHORDS[c]["pad"], n, voices=9, detune=20, drift=10, scoop=(-80, 0.4), seed=R0,
                             drift_rates=(0.05, 0.11))
        b = sd.detuned_stack(CHORDS[c]["bright"], n, voices=5, detune=12, drift=12, scoop=(-80, 0.4), seed=R0 + 1,
                             drift_rates=(0.07, 0.17))
        t = np.arange(n) / SR
        cut = 1100 + 1500 * np.minimum(t / 3.0, 1) * np.exp(-np.maximum(t - 3.0, 0) / 6.0) + \
            200 * np.sin(2 * np.pi * 0.05 * t)  # slow bloom per chord
        y = fx.tv_filter(m + 0.3 * dsp.sos_filter(b, "highpass", 2000, SR, 2), "lowpass", cut, q=0.7, stages=2)
        place(out, sd.fade(sd.tube(y, drive=1.3), 1.5, 3.0), R0)
    out *= dsp.undb(ses.auto(0.0).set(40, 44, -14.0, -4.0).set(44, 52, -8.0).smooth(80).v)
    return out + 0.5 * fx.reverb(out, HUGE)


def ghost():
    out = ses.stem()
    rng = np.random.default_rng(19)
    for R0, nb, c in blocks(CHORD, GHOST_BARS):
        n = ses.pos(R0 + nb) - ses.pos(R0)
        car = sd.detuned_stack([m + 12 for m in CHORDS[c]["pad"][1:]], n, voices=5, detune=10, seed=R0 + 7,
                               drift_rates=(0.05, 0.11))
        mod = sd.vowel_noise(n, ["oo", "ah", "oh", "ee"], int(4 * ses.spb), seed=R0)
        k = (np.arange(n) / ses.spb).astype(int)  # one slow syllable per beat
        acc = rng.choice([0.0, 0.6, 1.0, 1.0], size=k.max() + 1)
        syl = np.sin(np.pi * ((np.arange(n) / ses.spb) % 1.0)) ** 0.8 * acc[k]
        place(out, sd.vocoder(car, mod * syl), R0)
    out = dsp.sos_filter(dsp.sos_filter(out, "highpass", 300, SR, 2), "lowpass", 6000, SR, 2)
    return fx.widen(out, 1.6) + 0.6 * fx.reverb(out, HUGE)


def plucks():
    out = ses.stem()
    rng = np.random.default_rng(23)
    gaps = np.array([330, 510, 285, 690]) / 1000  # the Flume-style ms arp, three times slower
    for R0, nb, c in blocks(CHORD, PLUCK_BARS):
        t, end, i = ses.pos(R0) / SR, ses.pos(R0 + nb) / SR, 0
        tones = CHORDS[c]["tones"]
        while t < end:
            if rng.random() < 0.5:
                note = int(rng.choice(tones)) + 12 + 12 * (rng.random() < 0.35)
                ses.add(out, sd.fm_pluck(sd.midi_hz(note), length=0.6), int(t * SR), rng.uniform(0.4, 0.9),
                        pan=0.7 * np.sin(2 * np.pi * 0.07 * t))
            t += gaps[i % 4]
            i += 1
    out = sd.ott(out, amount=0.5)
    return out + 0.35 * fx.reverb(out, PLATE) + 0.6 * fx.reverb(out, HUGE)


def chimes():
    """Sparse metallic plucks and bells in the rain and the dissolve."""
    out = ses.stem()
    rng = np.random.default_rng(29)
    for b0, b1 in ((2, 12), (64, 80)):
        t, end = ses.pos(b0) / SR, ses.pos(b1) / SR
        while t < end:
            note = int(rng.choice(CHORDS["B"]["tones"])) + 24
            snd = sd.fm_bell(sd.midi_hz(note), length=2.5, index=2.5, decay=2.0) if rng.random() < 0.5 else \
                sd.fm_pluck(sd.midi_hz(note), length=0.6)
            ses.add(out, snd, int(t * SR), rng.uniform(0.4, 1.0), pan=rng.uniform(-0.7, 0.7))
            t += rng.uniform(2.0, 5.0)
    return out + 0.7 * fx.reverb(out, HUGE)


def twinkle():
    out = ses.stem()
    tones = CHORDS["B"]["tones"]
    for k in range(62):  # 8ths across the return, rising an octave
        u = k / 63
        f = sd.midi_hz(tones[k % len(tones)] + 12) * 2 ** u
        ses.add(out, sd.fm_bell(f, length=1.2, index=2.0, decay=1.0), ses.pos(36 + k // 8, (k % 8) / 2),
                0.4 + 0.5 * u, pan=0.6 * np.sin(1.3 * k))
    return out + 0.6 * fx.reverb(out, HUGE)


def horn_swell(m, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = sd.midi_hz(m) * 2 ** (-150 * np.exp(-t / 0.12) / 1200)  # the Flume-style scoop, slowed
    y = sd.saw(f * 2 ** (8 / 1200), n) + sd.saw(f * 2 ** (-8 / 1200), n, 0.4)
    env = np.minimum(t / 0.4, 1) * np.clip((length - t) / 1.5, 0, 1)
    y = dsp.sos_filter(y * env, "lowpass", 2200, SR, 2)
    return sd.fade(sd.amp_sim(y, drive=2.0), 0.01, 0.2)


def horns():
    out = ses.stem()
    for R in sorted(HORN_BARS):
        notes = STAB_NOTES[CHORD[R]]
        for beat, i in ((0, 0), (2, 1)) if R % 2 == 0 else ((0, 2), (2, 1)):
            ses.add(out, horn_swell(notes[i], 3.0), ses.pos(R, beat), 0.8, pan=(-0.35, 0.35)[i % 2])
    return out + 0.8 * fx.reverb(out, HUGE)


def wash(length, seed):
    n = int(length * SR)
    rng = np.random.default_rng(seed)
    y = fx.tv_filter(rng.standard_normal((2, n)), "bandpass", fx.sweep(n, 6000, 900), q=0.8, stages=1, block=64)
    t = np.arange(n) / SR
    return y / np.abs(y).max() * np.minimum(t / 0.4, 1) * np.exp(-t / (length / 3))


# ---------------------------------------------------------------- drones, weather, textures

def drones():
    out = ses.stem()
    harm = np.load(f"{W}/ddd2_harm.npy", mmap_mode="r")  # original-speed harmonic layer
    s0, s1 = src_span(0, 4, stretched=False)  # the intro pad, stretched x6 under the rain
    intro = dsp.sos_filter(sd.paulstretch(np.asarray(harm[:, s0:s1]), 6.0, seed=1), "lowpass", 4000, SR, 2)
    n = min(ses.pos(13) - ses.pos(0), intro.shape[1])
    intro = intro[:, :n] * np.minimum(np.arange(n) / (4 * SR), 1)
    place(out, sd.fade(intro, 0.01, 6.0), 0)
    s0, s1 = src_span(104, 106, stretched=False)  # the final B chord, stretched x20: the ending
    end = sd.paulstretch(np.asarray(harm[:, s0:s1]), 20.0, window_s=0.4, seed=2)
    end = dsp.sos_filter(end, "highpass", 140, SR, 2) * dsp.undb(-5.0)  # airy, without the wave's sub rumble
    place(out, sd.fade(end, 10.0, 1.0), 58)
    lp = sd.smooth_curve(ses.auto(21000).set(62, END + 2, 6000, 300, "exp").v)
    out = fx.tv_filter(out, "lowpass", lp) * ses.auto(1.0).set(68, END + 2, 1.0, 0.0, 1.2).smooth(200).v
    return out + 0.4 * fx.reverb(out, HUGE)


def drop_memory():
    """The Flume-style drop (chords, horns, wobble, plucks; no drums), paulstretched x10 in the dissolve."""
    sl = flume_ses.span(28, 32)
    src = sum(np.asarray(np.load(f"{W}/ddd2_flume_stem_{k}.npy", mmap_mode="r")[:, sl], dtype=np.float64)
              for k in ("chords", "horn", "wobble", "plucks"))
    y = dsp.sos_filter(sd.paulstretch(src, 10.0, window_s=0.35, seed=3), "lowpass", 3000, SR, 2)
    out = ses.stem()
    place(out, sd.fade(y, 6.0, 8.0), 62)
    out = out * ses.auto(1.0).set(70, END + 2, 1.0, 0.0, 1.3).smooth(200).v
    return out + 0.4 * fx.reverb(out, HUGE)


def cloud():
    regions = [(ses.pos(0), ses.pos(12), *src_span(104, 108), 30),
               (ses.pos(28), ses.pos(36), *src_span(68, 76), 70),
               (ses.pos(64), ses.pos(72), *src_span(104, 108), 80),
               (ses.pos(72), ses.pos(82), *src_span(104, 108), 40)]
    out = sd.granular(ses.harm, ses.N, regions, grain=(0.08, 0.25), pitches=(0, 12, -12, 24),
                      weights=(0.5, 0.3, 0.1, 0.1), seed=7)
    out *= ses.auto(1.0).set(68, 82, 1.0, 0.0, 1.5).smooth(200).v
    return out + 0.6 * fx.reverb(out, HUGE)


def nature():
    n = ses.N
    th = ses.stem()
    for b in (28, 31, 34):
        ses.add(th, sd.thunder(6.0, seed=b), ses.pos(b), 0.6)
    mix = sd.rain(n, density=55, seed=11) * ses.auto(0.0).set(0, 12, 1.0).set(12, 28, 0.35).set(28, 36, 1.0) \
        .set(36, 40, 1.0, 0.0).set(62, END + 2, 0.8).smooth(200).v
    mix += sd.creek(n, seed=12) * ses.auto(0.0).set(0, 12, 0.5).set(12, 14, 0.5, 0.0).set(64, END + 2, 0.6).smooth(200).v
    mix += sd.birds(n, rate=0.18, seed=13) * ses.auto(0.0).set(0, 12, 1.0).set(66, END + 2, 1.0).smooth(200).v
    return (mix + th) * ses.auto(1.0).set(78, END + 2, 1.0, 0.0).v


def heart():
    """A soft lub-dub every slow bar under the wave (68 per minute)."""
    out = ses.stem()
    for R in sorted(HEART_BARS):
        ses.add(out, KICK_SOFT, ses.pos(R, 0), 1.0)
        ses.add(out, KICK_SOFT, ses.pos(R, 0.35), 0.6)
    return out


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM grid, {ses.total} slow bars, {ses.N / SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    m.add("bed", bed_layer(bed_raw))
    fold = dsp.sos_filter(sd.wavefold(dsp.sos_filter(np.asarray(bed_raw, dtype=np.float64), "lowpass", 110, SR, 4) *
                                      ses.auto(0.0).set(44, 60, 1.0).smooth(80).v, 2.0), "bandpass", (80, 400), SR, 2)
    m.add("fold", fold)
    sh = sd.shimmer(np.asarray(bed_raw[:, ses.span(36, 44)]), HUGE)
    shim = ses.stem()
    sl = ses.span(36, 44)
    shim[:, sl] = sh[:, :sl.stop - sl.start]
    m.add("shimmer", shim * ses.auto(0.0).set(36, 44, 0.0, 1.0, 2.0).v)
    del sh, shim, fold
    print("source layers done")
    m.add("chords", chords())
    m.add("ghost", ghost())
    m.add("plucks", plucks())
    m.add("chimes", chimes())
    m.add("twinkle", twinkle())
    m.add("horn", horns())
    w = ses.stem()
    for b in (44, 48, 52, 56):  # spray on each slow wave crest
        place(w, wash(4 * 4 * ses.spb / SR, seed=b), b)
    m.add("wash", w + 0.5 * fx.reverb(w, HUGE))
    m.add("heart", heart())
    print("palette done")
    m.add("drone", drones())
    m.add("memory", drop_memory())
    m.add("cloud", cloud())
    m.add("nature", nature())
    m.add("lofi", engine.lofi_texture(ses.N) * ses.auto(0.0).set(0, 12, 1.0).set(28, 36, 0.8).set(62, END + 2, 1.0)
          .smooth(200).v)
    f = ses.stem()
    for b in (12, 44, 52):
        reverse_swell(ses, f, bed_raw, b, HUGE, beats=4, gain=0.7)
    m.add("fx", f, gain_db=-14.0 - dsp.db(np.abs(f).max() + 1e-9))
    print("stem gains dB:", m.gains)

    mix = m.mix
    s = ses.span(34.5, 36)  # long tape slowdown out of the weather, into near-silence
    mix[:, s] = fx.tape_stop(mix[:, s])
    mix *= silence(ses, ses.N, [(35.85, 36)], fade_ms=40)
    T = END + 2
    section = ses.auto(0.0).set(0, 2, -16.0, -5.0, 0.5).set(2, 12, -5.0).set(12, 28, -1.5).set(28, 36, -2.5) \
        .set(36, 44, -3.0, -1.0).set(44, 52, -0.5).set(60, 64, -2.0).set(64, T, -3.0, -8.0).smooth(80)
    m.mix = mix * dsp.undb(section.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
