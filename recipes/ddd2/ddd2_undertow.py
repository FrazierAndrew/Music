"""ddd2, "Undertow". Engine: SAMPLER. Your song chopped like a sample pack and replayed as 2-step garage at
your original 136 BPM.

- stabs: one-shots cut from your de-pumped pad at the first beat of an E bar, a B bar and the D#m bar, given
  a sampler's amp and filter envelopes, layered with an octave-up copy, played in skipping garage patterns;
- chops: eighth-note slices of your pad's top voice (D#6 / C#6), sped up an octave like a sped-up vocal, cut
  into a hook with stutters, plus a vowel-like midrange lift;
- subs: your own bass notes (the E1 and B1 that start your wave) sampled and replayed as a rolling 2-step
  bassline, repitched by speed for the other notes; under the wave itself, your real bass stem returns;
- drums: 2-step kick and snare from your own drum stem, shuffled hats, rim ghosts, shaker;
- your habits: filter bloom in the intro, vinyl under everything, tape wobble on the pad in the breakdown,
  a tape slowdown into the breakdown and another to end the track.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_undertow.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
import sounddesign as sd
import space
import sampler as smp
from engine import Session, Mixer, reverse_swell
from ddd2_harmony import chord_of_source_bar, blocks, silence

SR = dsp.SR
W = engine.WORK
TAG = "ddd2_undertow"
SECTIONS = [
    ("intro", 0, 8, 0),
    ("groove", 8, 16, 20),
    ("build", 24, 4, 44),
    ("drop", 28, 16, 76),
    ("drop_b", 44, 8, 84),
    ("break", 52, 8, 68),
    ("lift", 60, 4, 92),
    ("wave", 64, 8, 100),
    ("wave2", 72, 8, 100),
    ("outro", 80, 4, 108),
]
END = 84
T = END + 2
ses = Session("ddd2_stems", "tracks/ddd2/analysis.json", f"{W}/ddd2_bed_dp.npy", None, T, seed=63)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]
SRC_OF = dict(MAPPING)
CHORD = {R: chord_of_source_bar(S) for R, S in MAPPING}
CHORD.update({R: "B" for R in range(84, T)})


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


DRUM_BARS = bars((8, 27), (28, 51), (64, 83))
KICK_BARS = DRUM_BARS
HAT_BARS = bars((6, 8), (8, 27), (28, 51), (61, 64), (64, 83))
STAB_BARS = bars((4, 8), (8, 27), (28, 52), (60, 64), (64, 84))
CHOP_BARS = bars((20, 24), (28, 52), (52, 60), (72, 80))
SUB_BARS = bars((12, 27), (28, 52))
WAVE_BARS = bars((64, 80))
MUTE = {(27, 3), (51, 2), (51, 3), (63, 3), (83, 2), (83, 3)}
BASS_BARS, BASS_STEMS = SUB_BARS, ["subs"]
CHORD_STEMS, HARMONY_REF = ["stabs", "chops"], ["bed"]
CHORD_BARS = bars((8, 52), (64, 80))

STAB_A = [(0, 3), (3, 2), (7, 2), (10, 3), (14, 2)]  # (16th step, length in 16ths)
STAB_B = [(2, 2), (6, 3), (9, 2), (12, 4)]
CHOP_HOOK = [(0, 1), (1, 1), (3, 2), (6, 1), (8, 1), (9, 1), (11, 2), (14, 1), (15, 1)]
# rolling 2-step bassline per chord: (16th step, MIDI, length in 16ths); beat 1.5 is always the root's octave
SUBLINE = {"E": [(0, 28, 3), (3, 28, 2), (6, 40, 2), (8, 35, 3), (11, 28, 2), (14, 39, 2)],
           "B": [(0, 35, 3), (3, 35, 2), (6, 47, 2), (8, 30, 3), (11, 35, 2), (14, 34, 2)],
           "D#m": [(0, 27, 6), (8, 34, 4), (12, 30, 4)]}

PLATE = space.hall_ir(rt60=1.3, predelay=0.012, dark=0.4, early=0.8, seed=31)
HALL = space.hall_ir(rt60=3.4, predelay=0.025, dark=0.55, bloom=0.2, seed=32)
ROOM = space.hall_ir(rt60=0.5, predelay=0.003, dark=0.3, early=1.0, seed=33)

TARGETS = {"bed": (-19.5, (28, 44)), "stabs": (-19.0, (28, 44)), "chops": (-23.5, (28, 44)),
           "subs": (-18.5, (28, 44)), "wave": (-19.0, (64, 72)), "kick": (-17.0, (28, 44)),
           "snare": (-21.0, (28, 44)), "hats": (-27.0, (28, 44)), "perc": (-28.5, (28, 44)),
           "vinyl": (-37.0, (0, 8))}
MASTER_REGION = (72, 80)
MASTER_TARGET = -10.5
MASTER_CEILING = -1.9


def hp(x, f, order=2):
    return dsp.sos_filter(np.asarray(x, dtype=np.float64), "highpass", f, SR, order)


def lp(x, f, order=2):
    return dsp.sos_filter(np.asarray(x, dtype=np.float64), "lowpass", f, SR, order)


# ---------------------------------------------------------------- the sample pack, cut from your stems

def src_t(S, beat=0.0):
    bt = np.array(ses.an["beats"])
    return bt[ses.an["downbeat_phase"] + 4 * S] + beat * np.median(np.diff(bt))


def make_samples():
    bed0 = np.load(f"{W}/ddd2_bed_dp.npy", mmap_mode="r")
    bass0 = np.load(f"{W}/ddd2_bass.npy", mmap_mode="r")
    stabs = {}
    for c, S in (("E", 20), ("B", 24), ("D#m", 68)):
        raw = smp.capture(bed0, src_t(S) + 0.03, 0.9)
        up = smp.repitch(raw, 12)
        full = raw.copy()
        full[:, :up.shape[1]] += 0.4 * up
        stabs[c] = smp.normalize(hp(full, 140))
    chops = {}
    for name, S, beat in (("hi", 20, 0.0), ("lo", 21, 0.0), ("hi2", 22, 2.0), ("lo2", 23, 2.0)):
        raw = hp(smp.capture(bed0, src_t(S, beat) + 0.02, 0.5), 600, 4)
        raw = fx.eq_peak(fx.eq_peak(raw, 950, 4.0, q=1.2), 2600, 3.0, q=1.5)  # vowel-like lift
        chops[name] = smp.normalize(smp.repitch(raw, 12))
    subs = {}
    for name, S in (("E1", 100), ("B1", 104)):
        raw = smp.capture(bass0, src_t(S) + 0.015, 1.6, fade_in=0.004)
        subs[name] = smp.normalize(lp(raw, 260, 4).mean(0))
    return stabs, chops, subs


# ---------------------------------------------------------------- parts

def stab_part(stabs):
    out = ses.stem()
    rng = np.random.default_rng(3)
    for R in sorted(STAB_BARS):
        c = CHORD[R]
        pattern = STAB_A if R % 2 == 0 else STAB_B
        if R in bars((64, 72)):
            pattern = STAB_B  # first wave: stabs only answer in the gaps
        if R in bars((24, 28)):
            pattern = [(s, 1) for s in range(0, 16, 2 if R < 26 else 1)]  # build: eighths, then sixteenths
        for st, ln in pattern:
            if (R, st // 4) in MUTE:
                continue
            dur = ln * ses.spb / 4 / SR
            s = smp.amp_env(stabs[c], attack=0.003, hold=min(0.04, dur * 0.3), decay=max(0.08, dur * 0.55))
            bright = 7000 if R >= 28 else 4500
            s = smp.filter_env(s, bright, 1300, 0.18)
            ses.add(out, s, ses.pos(R, st / 4) + int(rng.uniform(-2, 2) * SR / 1000),
                    0.8 + 0.2 * (st % 4 == 0))
    filt = ses.auto(16000).set(4, 8, 900, 3000, "exp").set(24, 27.75, 2500, 14000, "exp") \
        .set(60, 63.75, 1500, 12000, "exp").set(80, T, 9000, 700, "exp")
    out = fx.tv_filter(out, "lowpass", sd.smooth_curve(filt.v))
    out = engine.wobble(out, depth_cents=6, rate_hz=0.5)
    wet = 0.35 * space.send(out, PLATE, hp=300) + 0.35 * fx.pingpong(out, 0.75 * ses.spb / SR, feedback=0.32,
                                                                    taps=4, lp=5000)
    return out + wet


def chop_part(chops):
    out = ses.stem()
    names = ["hi", "lo", "hi2", "lo2"]
    for R in sorted(CHOP_BARS):
        if R in bars((52, 60)):
            hits = [(0, 4), (8, 4)] if R % 2 == 0 else [(4, 6)]  # breakdown: slow, sparse
        elif R in bars((20, 24)):
            hits = CHOP_HOOK[:3]
        else:
            hits = CHOP_HOOK if R % 2 == 0 else CHOP_HOOK[:5] + [(12, 1), (13, 1), (14, 1), (15, 1)]  # stutter
        for i, (st, ln) in enumerate(hits):
            if (R, st // 4) in MUTE:
                continue
            src = chops[names[(R // 2 + i) % 4]]
            dur = ln * ses.spb / 4 / SR
            s = smp.amp_env(src, attack=0.002, hold=dur * 0.6, decay=0.05 + dur * 0.3)
            ses.add(out, s[:, :int((dur + 0.25) * SR)], ses.pos(R, st / 4), 0.75 + 0.25 * (i == 0),
                    )
    out = out * ses.auto(1.0).set(52, 60, 0.8).smooth(40).v
    wet = 0.5 * space.send(out, HALL, hp=600) + 0.3 * fx.pingpong(out, 0.375 * ses.spb / SR, feedback=0.3,
                                                                 taps=4, lp=7000)
    return out + wet


def sub_part(subs, trig):
    out = np.zeros(ses.N)
    for R in sorted(SUB_BARS):
        c = CHORD[R]
        for st, m, ln in SUBLINE[c]:
            if (R, st // 4) in MUTE:
                continue
            if R in bars((44, 52)) and st == 14:
                m += 12  # drop B: the last note jumps an octave
            base, root = (subs["E1"], 28) if c == "E" or m in (28, 40, 39) else (subs["B1"], 35)
            note = smp.repitch(base, m - root)[0]
            dur = ln * ses.spb / 4 / SR
            n = min(len(note), int((dur + 0.06) * SR))
            env = np.ones(n)
            env[-int(0.04 * SR):] = np.linspace(1, 0, int(0.04 * SR))
            p = ses.pos(R, st / 4)
            e = min(ses.N, p + n)
            out[p:e] += (note[:n] * env)[:e - p]
    out = sd.tube(out, drive=1.6) * engine.duck(ses, trig, 5.0, release=0.08)
    return np.stack([out, out])


def wave_part(bass_raw, trig):
    g = ses.auto(0.0).set(64, 80, 1.0).set(63.5, 64, 0.0, 1.0).set(80, 82, 1.0, 0.0).smooth(30)
    return np.asarray(bass_raw, dtype=np.float64) * g.v * engine.duck(ses, trig, 3.0, release=0.1)


def kit():
    kick = hp(np.load(f"{W}/ddd2_kit_kick_2.npy"), 30, 2)
    snare = hp(np.load(f"{W}/ddd2_kit_snare_3.npy"), 170, 2)
    clap = synth.clap(decay=0.14)
    body = synth.snare(decay=0.12, tone=220)
    layer = np.zeros((2, max(snare.shape[1], len(clap))))
    layer[:, :snare.shape[1]] += 0.7 * snare / (np.abs(snare).max() + 1e-9)
    layer[:, :len(clap)] += 0.6 * clap
    layer[:, :len(body)] += 0.35 * body
    layer = layer + 0.3 * space.convolve(layer, ROOM)[:, :layer.shape[1]]
    return kick, layer


def hat(decay, seed, band=(7000, 15000)):
    rng = np.random.default_rng(seed)
    n = int(decay * 6 * SR)
    t = np.arange(n) / SR
    return dsp.sos_filter(rng.standard_normal(n), "bandpass", band, SR, 2) * np.exp(-t / decay) * \
        np.minimum(t / 0.0006, 1)


def drums():
    kick, snare = kit()
    st = {k: ses.stem() for k in ("kick", "snare", "hats", "perc")}
    trig = []
    for R in sorted(KICK_BARS):
        steps = [0, 10] if R % 2 == 0 else [0, 7, 11]
        vel = [1.0, 0.9] if R % 2 == 0 else [1.0, 0.55, 0.9]
        if R in bars((24, 28)):
            steps, vel = [0], [1.0]
        trig += ses.hits(st["kick"], kick, {R}, steps, vel=vel, mute=MUTE, jitter_ms=1.0)
        if R not in bars((24, 28)):
            ses.hits(st["snare"], snare, {R}, [4, 12], mute=MUTE, jitter_ms=1.5, late_ms=3)
            if R % 2 == 1:
                ses.hits(st["snare"], snare, {R}, [15], gain=0.25, mute=MUTE)
    closed, opened = hat(0.018, 41), hat(0.1, 42, (6000, 14000))
    for R in sorted(HAT_BARS):
        ses.hits(st["hats"], closed, {R}, range(16), vel=[0.9, 0.3, 0.6, 0.4, 0.85, 0.3, 0.6, 0.45] * 2,
                 pan=0.2, swing=0.22, rand=0.12, mute=MUTE, jitter_ms=2)
        if R in DRUM_BARS:
            ses.hits(st["hats"], opened, {R}, [6, 14], gain=0.55, pan=-0.2, mute=MUTE)
    rim = synth.rim(freq=1750)
    shaker = sd.shaker(0.035)
    for R in sorted(DRUM_BARS):
        if R % 2 == 1:
            ses.hits(st["perc"], rim, {R}, [3, 11], gain=0.45, pan=-0.35, mute=MUTE)
        if R in bars((44, 52), (72, 80)):
            ses.hits(st["perc"], shaker, {R}, range(16), vel=[0.6, 0.3, 0.45, 0.3], pan=0.4, swing=0.22, mute=MUTE)
    st["snare"] = st["snare"] + 0.18 * space.send(st["snare"], PLATE, hp=300)
    st["perc"] = st["perc"] + 0.2 * space.send(st["perc"], PLATE, hp=500)
    return st, trig


def bed_layer(bed_raw):
    x = hp(bed_raw, 130)
    bloom = ses.auto(14000).set(0, 8, 600, 6000, "exp").set(24, 27.75, 300, 2500, "exp").set(52, 60, 5000) \
        .set(80, T, 6000, 900, "exp")
    x = fx.tv_filter(x, "lowpass", sd.smooth_curve(bloom.v))
    hpc = ses.auto(130).set(24, 27.75, 130, 900, "exp").set(60, 63.75, 130, 600, "exp")
    x = fx.tv_filter(x, "highpass", sd.smooth_curve(hpc.v))
    wob = engine.wobble(x, depth_cents=18, rate_hz=0.45)
    mixw = ses.auto(0.0).set(52, 60, 1.0).smooth(80).v
    x = x * (1 - mixw) + wob * mixw
    level = ses.auto(1.0).set(0, 8, 1.4).set(52, 60, 1.6).smooth(60).v
    return x * level + 0.35 * space.send(x, HALL)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    bass_raw = ses.assemble(np.load(f"{W}/ddd2_bass.npy", mmap_mode="r"), MAPPING)
    stabs, chops, subs = make_samples()
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    for k in list(st):
        m.add(k, st.pop(k))
    duck2 = engine.duck(ses, trig, 2.0, release=0.15)
    m.add("bed", bed_layer(bed_raw) * duck2)
    m.add("stabs", stab_part(stabs) * duck2)
    m.add("chops", chop_part(chops))
    m.add("subs", sub_part(subs, trig))
    m.add("wave", wave_part(bass_raw, trig))
    m.add("vinyl", engine.lofi_texture(ses.N) * ses.auto(0.6).set(0, 8, 1.0).set(52, 60, 1.3).smooth(100).v)
    f = ses.stem()
    for b in (28, 64):
        reverse_swell(ses, f, bed_raw, b, HALL, beats=2, gain=0.8)
    m.add("fx", f, gain_db=-12.0 - dsp.db(np.abs(f).max() + 1e-9))
    print("stem gains dB:", m.gains)
    mix = m.mix
    for a, b in ((51.5, 52), (83.5, 84)):  # tape slowdowns: into the breakdown, and to end the track
        s = ses.span(a, b)
        mix[:, s] = fx.tape_stop(mix[:, s])
    k = int(0.03 * SR)
    mix[:, ses.pos(84) - k:ses.pos(84)] *= np.linspace(1, 0, k)
    mix[:, ses.pos(84):] *= 0.0
    fxs = np.load(f"{W}/{TAG}_stem_fx.npy")
    g = silence(ses, ses.N, [(27.75, 28), (63.75, 64)], fade_ms=8)
    mix = (mix - fxs) * g + fxs
    section = ses.auto(0.0).set(0, 8, -5.0, -3.5).set(8, 24, -3.0).set(24, 28, -3.5, -2.0).set(28, 44, -2.0) \
        .set(44, 52, -1.6).set(52, 60, -6.0).set(60, 64, -5.0, -3.0).set(64, 72, -1.5).set(72, 80, 0.0) \
        .set(80, T, -3.0).smooth(60)
    m.mix = mix * dsp.undb(section.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
