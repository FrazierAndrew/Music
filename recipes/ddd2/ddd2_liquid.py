"""ddd2 remix C, "Liquid": liquid drum & bass at 170 BPM (source time-stretched 1.25x, pitch kept).

Two-step breakbeat, rolling legato sub and a moving reese in the first drop; then a 32-bar wave drop where
each chord lands as a sustained tidal sub (your last-drop shape) under a filtered reese crest.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_liquid.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
from engine import Session, Mixer, bed_chain, snare_roll, reverse_swell

W = engine.WORK
TAG = "ddd2_liquid"
SECTIONS = [
    ("intro", 0, 16, 0),
    ("drop", 16, 32, 20),
    ("breakdown", 48, 8, 68),
    ("prewave", 56, 8, 92),
    ("wave", 64, 8, 100),
    ("wave_mid", 72, 16, 76),
    ("wave_end", 88, 8, 100),
    ("outro", 96, 4, 108),
    ("coda", 100, 4, 0),
]
END = 104
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_harm.npy", f"{W}/ddd2_perc.npy", END + 2,
              stretch=1.25, seed=13)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]
SRC_OF = dict(MAPPING)


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


BEAT_BARS = bars((12, 16), (16, 48), (60, 64), (64, 100))
FULL = bars((16, 48), (64, 96))
HAT_BARS = bars((8, 48), (60, 98))
RIDE_BARS = bars((32, 48), (72, 96))
ROLL_BASS = bars((16, 47))  # rolling legato sub + reese in the first drop
WAVE_BARS = bars((64, 96))  # sustained tidal sub per chord
BASS_BARS, BASS_STEMS = ROLL_BASS | WAVE_BARS, ["sub", "wave"]
MUTE = {(15, 3), (31, 3), (47, 2), (47, 3), (63, 3), (79, 3), (95, 3)}

KICK = synth.kick(f_end=61.74, f_start=300, pitch_tau=0.018, body_tau=0.055, click=1.0, drive=1.8)  # B1
KICK_M = dsp.sos_filter(KICK, "lowpass", 300, dsp.SR, 2)


def soft(x, fc=10000):
    return dsp.sos_filter(x, "lowpass", fc, dsp.SR, 2)


SNARE = soft(synth.snare(decay=0.15, tone=225), 9000)
CLAP = soft(synth.clap(decay=0.1), 9000)


HAT, SHAKER = soft(synth.hat(decay=0.025)), soft(synth.hat(decay=0.015, bright=1.2), 11000)
RIDE = soft(synth.ride(decay=0.7), 10000)
CRASH, IMPACT = soft(synth.crash(), 10000), synth.impact()
ROOM = fx.make_ir(rt60=0.7, predelay=0.008, seed=41)
HALL = fx.make_ir(rt60=3.5, predelay=0.03, seed=42)
HUGE = fx.make_ir(rt60=6.5, predelay=0.05, hi_damp=0.6, seed=43)

TARGETS = {"bed": (-16.0, (16, 32)), "kick": (-17.5, (16, 32)), "snare": (-21.0, (16, 32)),
           "hats": (-35.0, (16, 32)), "ride": (-35.0, (32, 48)), "shaker": (-38.0, (16, 32)),
           "sub": (-18.0, (16, 32)), "reese": (-24.0, (16, 32)), "wave": (-17.0, (72, 88)),
           "crest": (-25.0, (72, 88)), "shimmer": (-25.0, (48, 56))}
MASTER_REGION = (72, 88)


def drums():
    st = {k: ses.stem() for k in ("kick", "snare", "hats", "ride", "shaker")}
    trig = []
    for R in sorted(BEAT_BARS):
        light = R not in FULL
        kick = KICK_M if light else KICK
        ksteps = [0, 10] if R % 2 == 0 else [0, 10, 13]
        trig += ses.hits(st["kick"], kick, {R}, ksteps, mute=MUTE)
        trig += ses.hits(st["snare"], SNARE, {R}, [4, 12], gain=0.7 if light else 1.0, mute=MUTE)
        ses.hits(st["snare"], CLAP, {R}, [4, 12], gain=0.45, mute=MUTE)
        if not light:
            ses.hits(st["snare"], SNARE, {R}, [7, 15], vel=[0.16, 0.22], mute=MUTE)  # ghost notes
    for R in sorted(HAT_BARS):
        ses.hits(st["hats"], HAT, {R}, range(0, 16, 2), vel=[0.55, 0.9], pan=0.2, swing=0.0, rand=0.08, mute=MUTE)
        if R in FULL:
            ses.hits(st["shaker"], SHAKER, {R}, range(16), vel=[0.3, 0.6, 0.4, 0.7], pan=-0.25, swing=0.12,
                     rand=0.12, mute=MUTE)
    ses.hits(st["ride"], RIDE, RIDE_BARS, [0, 2, 4, 6, 8, 10, 12, 14], vel=[0.75, 0.45], pan=0.3, mute=MUTE)
    for b in (0, 0.5, 1, 1.5, 2, 2.25, 2.5, 2.75):  # kick roll into the wave
        ses.add(st["kick"], KICK_M, ses.pos(63, b), 0.9)
    st["snare"] = st["snare"] + 0.25 * fx.reverb(st["snare"], ROOM) + 0.12 * fx.reverb(st["snare"], HALL)
    return st, trig


def rolling_sub():
    """Legato sine sub on a bouncy two-step rhythm, following the original roots."""
    out = ses.stem()
    steps = [0, 3, 6, 10, 13]
    for R in sorted(ROLL_BASS):
        root = ses.root(SRC_OF[R], 28, 39)
        for i, st in enumerate(steps):
            if (R, int(st / 4)) in MUTE:
                continue
            nxt = steps[i + 1] if i + 1 < len(steps) else 16
            length = (nxt - st) / 4 * ses.spb / dsp.SR * 0.95
            note = synth.wave_bass(root, length, decay_db=4.0, attack=0.006, release=0.02)
            ses.add(out, note, ses.pos(R, st / 4), 1.0 if st in (0, 10) else 0.8)
    return out


def reese_layer(bars_set, cutoff=650, level_by_bar=None):
    out = ses.stem()
    R = min(bars_set)
    while R <= max(bars_set):
        if R not in bars_set:
            R += 1
            continue
        root = ses.root(SRC_OF[R], 28, 39) + 12
        n = 1
        while R + n in bars_set and n < 4 and ses.root(SRC_OF[R + n], 28, 39) + 12 == root \
                and SRC_OF[R + n] == SRC_OF[R] + n:
            n += 1
        r = synth.reese(root, (ses.pos(R + n) - ses.pos(R)) / dsp.SR, cutoff=cutoff, detune=13, lfo_hz=0.35, seed=R)
        ses.add(out, r, ses.pos(R))
        R += n
    return out


def wave_layer():
    out = ses.stem()
    R = min(WAVE_BARS)
    while R <= max(WAVE_BARS):
        root = ses.root(SRC_OF[R], 28, 39)
        n = 1
        while R + n in WAVE_BARS and n < 4 and SRC_OF[R + n] == SRC_OF[R] + n:
            n += 1
        length = (ses.pos(R + n) - ses.pos(R)) / dsp.SR + 0.25
        g = 1.0 if root % 12 == 4 else dsp.undb(-3)
        ses.add(out, synth.wave_bass(root, length, decay_db=11.0 * n / 4), ses.pos(R), g)
        R += n
    return out


def shimmer(bed_raw):
    out = ses.stem()
    sl = ses.span(48, 56)
    blurred = fx.spectral_blur(np.asarray(bed_raw[:, sl]), 1.6 * ses.spb / dsp.SR)
    up = dsp.sos_filter(fx.rubberband(blurred, pitch=2.0)[:, :sl.stop - sl.start], "highpass", 900, dsp.SR, 2)
    n = up.shape[1]
    env = np.minimum(np.linspace(0, 1, n) * 4, 1) * np.minimum(np.linspace(1, 0, n) * 3, 1)
    out[:, sl.start:sl.start + n] += up * env
    return fx.reverb(out, HUGE)


def fx_layer(bed_raw):
    out = ses.stem()
    for b, g in ((16, 0.5), (48, 0.3), (64, 0.55), (72, 0.4), (80, 0.4), (88, 0.45), (96, 0.3)):
        ses.add(out, CRASH, ses.pos(b), g)
    for b, g in ((16, 0.85), (64, 1.0)):
        ses.add(out, IMPACT, ses.pos(b), g)
        ses.add(out, synth.downlifter(2 * 4 * ses.spb / dsp.SR), ses.pos(b), 0.3)
    ses.add(out, synth.riser(4 * 4 * ses.spb / dsp.SR, seed=61), ses.pos(12), 0.4)
    ses.add(out, synth.riser(8 * 4 * ses.spb / dsp.SR, seed=62), ses.pos(56), 0.45)
    snare_roll(ses, out, SNARE, 60, level=0.75)
    for b in (16, 64, 88, 100):
        reverse_swell(ses, out, bed_raw, b, HALL)
    return out + 0.35 * fx.reverb(out, HALL)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / dsp.SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    for name in list(st):
        m.add(name, st.pop(name))
    kick_trig = [p for p in trig]  # kicks and snares both carve the sub
    m.add("sub", rolling_sub() * engine.duck(ses, kick_trig, 5.0, release=0.07))
    m.add("reese", reese_layer(ROLL_BASS) * engine.duck(ses, kick_trig, 6.0, release=0.12))
    m.add("wave", wave_layer() * engine.duck(ses, kick_trig, 5.0, release=0.09))
    crest = reese_layer(WAVE_BARS, cutoff=480)
    crest *= ses.auto(1.0).set(64, 72, 0.6, 1.0).v
    m.add("crest", crest * engine.duck(ses, kick_trig, 7.0, release=0.15))

    T = END + 2
    hpf = ses.auto(100).set(0, 16, 30).set(12, 15.75, 30, 500, "exp").set(15.75, 16, 500).set(48, 56, 60) \
        .set(56, 63, 40).set(63, 63.75, 40, 700, "exp").set(63.75, 64, 700).set(96, T, 30)
    lpf = ses.auto(21000).set(0, 8, 1500, 9000, "exp").set(8, 12, 9000, 21000, "exp").set(48, 56, 7000) \
        .set(98, 104, 12000, 900, "exp").set(104, T, 900)
    gain = ses.auto(0.0).set(0, 2, -30, -4, 0.5).set(2, 12, -4, -2).set(12, 15.75, -2, 0) \
        .set(15.75, 16, -90).set(48, 56, -3).set(56, 63.75, -1.5).set(63.75, 64, -90) \
        .set(100, 104, -1, -30).set(104, T, -90)
    send = ses.auto(0.07).set(0, 12, 0.4).set(12, 16, 0.4, 0.15).set(48, 56, 0.45).set(56, 64, 0.3) \
        .set(96, 104, 0.3, 0.6)
    blur = ses.auto(0.0).set(16, 48, 0.35).set(48, 56, 0.6).set(64, 96, 0.35)  # soften original 4/4 pumping
    bed, _ = bed_chain(ses, bed_raw, hpf, lpf, gain, trig, duck_lo=4.0, duck_hi=1.5, release=0.15,
                       width=1.2, send=send, ir=HALL, blur_mix=blur, blur_regions=((16, 48), (48, 56), (64, 96)))
    m.add("bed", bed)
    del bed
    m.add("shimmer", shimmer(bed_raw))
    f = soft(fx_layer(bed_raw), 10000)
    m.add("fx", f, gain_db=-9.0 - dsp.db(np.abs(f).max()))
    del f
    print("stem gains dB:", m.gains)
    section_db = ses.auto(0.0).set(0, 16, -1.0).set(16, 48, -1.0).set(48, 56, -3.0).set(56, 64, -2.5, -0.5) \
        .set(96, T, -1.0)
    m.mix *= dsp.undb(section_db.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
