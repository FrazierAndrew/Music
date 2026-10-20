"""ddd2 remix A, "Tidal": melodic techno at 136 BPM.

Driving rolling bass and rumble through the first half, a teasing pre-wave, then the rolling bass stops
and your original last-drop wave carries the low end, twice (bare, then with full drums and chops).
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_tidal.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
from engine import Session, Mixer, bed_chain, snare_roll, reverse_swell, chop

W = engine.WORK
TAG = "ddd2_tidal"
SECTIONS = [  # (name, first remix bar, bars, first source bar)
    ("intro", 0, 16, 0),
    ("groove", 16, 24, 20),
    ("build", 40, 8, 44),
    ("drop", 48, 16, 52),
    ("breakdown", 64, 8, 68),
    ("prewave", 72, 8, 92),
    ("wave", 80, 8, 100),
    ("wave2", 88, 8, 100),
    ("outro", 96, 12, 0),
    ("end", 108, 4, 108),
]
END = 112
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_harm.npy", f"{W}/ddd2_perc.npy", END + 2)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]
SRC_OF = dict(MAPPING)


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


KICK_BARS = bars((8, 47), (48, 64), (80, 104))
CLAP_BARS = bars((24, 47), (48, 64), (88, 96))
HAT_BARS = bars((4, 47), (48, 64), (82, 102))
OHAT_BARS = bars((24, 47), (48, 64), (88, 96))
RIDE_BARS = bars((56, 64), (88, 96))
PERC_BARS = bars((32, 47), (52, 64))
BASS_BARS = bars((16, 46), (48, 64))  # rolling bass; none in the wave, the original carries it
CHOP_BARS = bars((56, 64), (88, 96))
MUTE = {(15, 3), (39, 3), (63, 3), (95, 3)}

# kit kept soft and dark to match the original's top end (it rolls off steeply above 3 kHz)
KICK = fx.eq_peak(synth.kick(f_end=46.25, f_start=210, pitch_tau=0.022, body_tau=0.075, click=0.6, drive=1.5),
                  150, -3.0, q=1.0)  # tuned to F#1, less 100-200 Hz boxiness
KICK_M = dsp.sos_filter(KICK, "lowpass", 260, dsp.SR, 2)
CLAP, SNARE = synth.clap(), synth.snare(decay=0.12, tone=200)


def soft(x, fc=9000):
    return dsp.sos_filter(x, "lowpass", fc, dsp.SR, 2)


HAT, OHAT = soft(synth.hat(decay=0.035)), soft(synth.open_hat(decay=0.18))
RIDE, RIM = soft(synth.ride(), 10000), synth.rim(freq=1500)
TOMS = [synth.tom(f) for f in (185, 156, 131, 110)]
CRASH, IMPACT = soft(synth.crash(), 10000), synth.impact()
ROOM = fx.make_ir(rt60=0.9, predelay=0.01, seed=21)
HALL = fx.make_ir(rt60=3.8, predelay=0.03, seed=22)
HUGE = fx.make_ir(rt60=6.5, predelay=0.05, hi_damp=0.6, seed=23)

TARGETS = {"bed": (-16.0, (48, 64)), "kick": (-17.0, (48, 64)), "bass": (-18.5, (48, 64)),
           "clap": (-24.5, (48, 64)), "hats": (-36.0, (48, 64)), "ohat": (-36.0, (48, 64)),
           "ride": (-34.0, (56, 64)), "perc": (-29.5, (52, 64)), "rumble": (-27.0, (48, 64)),
           "chops": (-26.0, (56, 64)), "shimmer": (-25.0, (64, 72))}
MASTER_REGION = (88, 96)


def drums():
    st = {k: ses.stem() for k in ("kick", "clap", "hats", "ohat", "ride", "perc")}
    trig = []
    for R in range(END):
        for beat in range(4):
            if (R, beat) in MUTE:
                continue
            if R in KICK_BARS:
                ses.add(st["kick"], KICK, ses.pos(R, beat))
                trig.append(ses.pos(R, beat))
    scale = {R: (0.5 if R < 8 else 0.75 if R < 16 else 1.0) for R in HAT_BARS}
    for R in sorted(HAT_BARS):
        ses.hits(st["hats"], HAT, {R}, range(16), gain=scale[R], vel=[0.35, 0.6, 0.9, 0.55],
                 pan=0.18, swing=0.08, rand=0.08, mute=MUTE)
    ses.hits(st["clap"], CLAP, CLAP_BARS, [4, 12], mute=MUTE)
    ses.hits(st["clap"], SNARE, CLAP_BARS, [4, 12], gain=0.35, mute=MUTE)
    ses.hits(st["ohat"], OHAT, OHAT_BARS, [2, 6, 10, 14], gain=0.8, pan=-0.15, mute=MUTE)
    ses.hits(st["ride"], RIDE, RIDE_BARS, [0, 2, 4, 6, 8, 10, 12, 14], vel=[0.8, 0.45], pan=0.3)
    ses.hits(st["perc"], RIM, PERC_BARS, [3, 6, 11, 14], gain=0.8, pan=-0.3)
    for R in (39, 63, 95):  # tom fills on the muted last beats
        for i, tom in enumerate(TOMS):
            ses.add(st["perc"], tom, ses.pos(R, 3 + i / 4), 0.9, pan=-0.4 + 0.27 * i)
    for R in (76, 77, 78):  # pre-wave: muffled kick, then a roll into the gap
        for beat in range(4):
            ses.add(st["kick"], KICK_M, ses.pos(R, beat), 0.9)
    for b in (0, 0.5, 1, 1.5, 2, 2.25, 2.5, 2.75):
        ses.add(st["kick"], KICK_M, ses.pos(79, b), 0.95)
    st["clap"] = st["clap"] + 0.22 * fx.reverb(st["clap"], ROOM) + 0.1 * fx.reverb(st["clap"], HALL)
    st["perc"] = st["perc"] + 0.3 * fx.reverb(st["perc"], ROOM)
    return st, trig


def rolling_bass():
    out = ses.stem()
    sixteenth = ses.spb / 4 / dsp.SR
    for R in sorted(BASS_BARS):
        root = ses.root(SRC_OF[R], 28, 39)
        growl = 0.5 if R >= 48 else 0.15
        for beat in range(4):
            if (R, beat) in MUTE:
                continue
            for k, vel in ((1, 0.95), (2, 0.72), (3, 0.86)):
                ses.add(out, synth.bass_note(root, 0.86 * sixteenth, growl=growl), ses.pos(R, beat + k / 4), vel)
    return out


def wash(length, seed=40):
    """Soft noise 'spray' that crests and recedes with each wave note."""
    n = int(length * dsp.SR)
    rng = np.random.default_rng(seed)
    y = fx.tv_filter(rng.standard_normal((2, n)), "bandpass", fx.sweep(n, 7000, 1200), q=0.8, stages=1, block=64)
    t = np.arange(n) / dsp.SR
    return y / np.abs(y).max() * np.minimum(t / 0.15, 1) * np.exp(-t / (length / 3))


def fx_layer(bed_raw):
    out = ses.stem()
    for b, g in ((16, 0.35), (48, 0.55), (64, 0.3), (80, 0.5), (88, 0.4), (96, 0.35)):
        ses.add(out, CRASH, ses.pos(b), g)
    for b, g in ((48, 0.9), (80, 1.0)):
        ses.add(out, IMPACT, ses.pos(b), g)
        ses.add(out, synth.downlifter(2 * 4 * ses.spb / dsp.SR), ses.pos(b), 0.3)
    ses.add(out, synth.riser(8 * 4 * ses.spb / dsp.SR, seed=41), ses.pos(40), 0.45)
    ses.add(out, synth.riser(8 * 4 * ses.spb / dsp.SR, seed=42), ses.pos(72), 0.4)
    snare_roll(ses, out, SNARE, 44, level=1.0)
    snare_roll(ses, out, SNARE, 76, level=0.75)
    rc = CRASH[:, :int(1.5 * 4 * ses.spb)][:, ::-1]
    for b in (16, 48, 80):
        ses.add(out, rc * np.linspace(0, 1, rc.shape[1]) ** 2, ses.pos(b) - rc.shape[1], 0.35)
    for b in (16, 48, 80, 96):
        reverse_swell(ses, out, bed_raw, b, HALL)
    for b in (80, 84, 88, 92):  # spray on each wave crest
        ses.add(out, wash(4 * 4 * ses.spb / dsp.SR, seed=b), ses.pos(b), 0.22)
    return out + 0.35 * fx.reverb(out, HALL)


def chops(bed_raw, trig):
    out = ses.stem()
    for R in sorted(CHOP_BARS):
        c = chop(ses, bed_raw, R, beat=1.5, semitones=12)
        for s16 in (3, 6, 11, 14):
            ses.add(out, c, ses.pos(R, s16 / 4))
    out = dsp.sos_filter(out, "highpass", 450, dsp.SR, 2)
    out = out + 0.55 * fx.pingpong(out, 0.75 * ses.spb / dsp.SR, feedback=0.42, taps=6, lp=4500)
    return out * engine.duck(ses, trig, 3.0, release=0.1)


def shimmer(bed_raw):
    out = ses.stem()
    sl = ses.span(64, 72)
    blurred = fx.spectral_blur(np.asarray(bed_raw[:, sl]), 1.6 * ses.spb / dsp.SR)
    up = dsp.sos_filter(fx.rubberband(blurred, pitch=2.0)[:, :sl.stop - sl.start], "highpass", 900, dsp.SR, 2)
    n = up.shape[1]
    env = np.minimum(np.linspace(0, 1, n) * 4, 1) * np.minimum(np.linspace(1, 0, n) * 3, 1)
    out[:, sl.start:sl.start + n] += up * env
    return fx.reverb(out, HUGE)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / dsp.SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    rumble_src = st["kick"] * ses.auto(0.0).set(16, 46, 1.0).set(48, 64, 1.0).v
    for name in list(st):
        m.add(name, st.pop(name))
    rumble = dsp.sos_filter(fx.reverb(rumble_src, HUGE), "lowpass", 140, dsp.SR, 4)
    m.add("rumble", rumble * engine.duck(ses, trig, 14.0, release=0.18))
    del rumble, rumble_src
    m.add("bass", rolling_bass() * engine.duck(ses, trig, 5.0, release=0.07))

    T = END + 2
    hpf = ses.auto(120).set(0, 12, 30).set(12, 16, 30, 120, "exp").set(42, 47, 120, 900, "exp") \
        .set(47, 48, 900).set(64, 72, 60).set(72, 79, 30).set(79, 79.75, 30, 400, "exp") \
        .set(79.75, 80, 400).set(80, 96, 20).set(96, T, 30)
    lpf = ses.auto(21000).set(0, 8, 900, 4000, "exp").set(8, 16, 4000, 21000, "exp") \
        .set(100, 112, 21000, 700, "exp").set(112, T, 700)
    gain = ses.auto(0.0).set(0, 2, -30, -4, 0.5).set(2, 16, -4, -1).set(16, 40, -1.5) \
        .set(40, 47.75, -1.5, 0).set(47.75, 48, -90).set(64, 72, -2).set(72, 79.75, -1) \
        .set(79.75, 80, -90).set(96, 108, -1).set(108, 112, -1, -30).set(112, T, -90)
    send = ses.auto(0.06).set(0, 16, 0.35).set(40, 48, 0.06, 0.25).set(64, 72, 0.4).set(72, 80, 0.25) \
        .set(80, 96, 0.07).set(96, 112, 0.25, 0.5)
    duck_lo = ses.auto(3.0).set(80, 96, 7.0)  # carve the original wave under the new kick
    bed, _ = bed_chain(ses, bed_raw, hpf, lpf, gain, trig, duck_lo=duck_lo, duck_hi=1.0, release=0.1,
                       width=1.15, send=send, ir=HALL)
    m.add("bed", bed)
    del bed
    m.add("shimmer", shimmer(bed_raw))
    m.add("chops", chops(bed_raw, trig))
    f = soft(fx_layer(bed_raw), 10000)
    m.add("fx", f, gain_db=-9.0 - dsp.db(np.abs(f).max()))
    del f
    print("stem gains dB:", m.gains)
    section_db = ses.auto(0.0).set(16, 40, -2.0).set(40, 48, -2.0, -1.0).set(48, 64, -1.0).set(64, 72, -3.0) \
        .set(72, 80, -2.5, -0.5).set(96, T, -1.0)
    m.mix *= dsp.undb(section_db.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
