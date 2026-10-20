"""ddd2 remix B, "Halftime": Flume-leaning future bass on the 136 grid with a halftime feel.

Chords de-pumped then re-pumped by a halftime kick/snare, a wonky pitched chord-chop melody, swung hats
with rolls, lo-fi texture, and the wave rebuilt as a clean synth sub (same pitch and 4-bar recession as
your last drop) so it can breathe with the halftime groove instead of the original 4/4 kick.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_halftime.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
from engine import Session, Mixer, bed_chain, snare_roll, reverse_swell, chop, wobble, lofi_texture

W = engine.WORK
TAG = "ddd2_halftime"
SECTIONS = [
    ("intro", 0, 8, 0),
    ("verse", 8, 16, 12),
    ("build", 24, 8, 44),
    ("drop", 32, 16, 76),
    ("drop_b", 48, 8, 52),
    ("breakdown", 56, 8, 68),
    ("prewave", 64, 8, 92),
    ("wave", 72, 8, 100),
    ("wave2", 80, 8, 100),
    ("outro", 88, 4, 108),
    ("coda", 92, 4, 0),
]
END = 96
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_harm.npy", f"{W}/ddd2_perc.npy", END + 2, seed=12)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]
SRC_OF = dict(MAPPING)


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


GROOVE = bars((12, 31), (32, 56), (68, 71), (72, 92))  # halftime kick/snare
HATS = bars((12, 31), (32, 56), (74, 92))
ROLL_BARS = {R for R in bars((36, 56), (80, 88)) if R % 2 == 1}  # hat rolls closing every 2nd bar
PERC = bars((16, 24), (40, 56), (80, 88))
OHAT = bars((32, 56), (80, 88))
WAVE_BARS = bars((16, 24), (32, 56), (72, 88))  # synth wave sub, one note per source chord
BASS_BARS, BASS_STEMS = WAVE_BARS, ["wave"]
CREST_BARS = bars((72, 88))
CHOP_BARS = bars((40, 56), (80, 88))
MUTE = {(23, 3), (31, 2), (31, 3), (47, 3), (55, 2), (55, 3), (71, 3), (87, 3)}

KICK = synth.kick(f_end=61.74, f_start=260, pitch_tau=0.02, body_tau=0.09, click=0.7, drive=2.0)  # B1
KICK_M = dsp.sos_filter(KICK, "lowpass", 300, dsp.SR, 2)


def soft(x, fc=9500):
    return dsp.sos_filter(x, "lowpass", fc, dsp.SR, 2)


SNARE = soft(synth.snare(decay=0.18, tone=190), 9000)
CLAP = soft(synth.clap(decay=0.16), 9000)


HAT, OHAT_S = soft(synth.hat(decay=0.03)), soft(synth.open_hat(decay=0.16))
RIM = synth.rim(freq=1900)
CRASH, IMPACT = soft(synth.crash(), 10000), synth.impact()
ROOM = fx.make_ir(rt60=0.9, predelay=0.01, seed=31)
PLATE = fx.make_ir(rt60=2.4, predelay=0.02, hi_damp=0.45, seed=32)
HALL = fx.make_ir(rt60=3.8, predelay=0.03, seed=33)
HUGE = fx.make_ir(rt60=7.0, predelay=0.05, hi_damp=0.6, seed=34)

TARGETS = {"bed": (-16.0, (32, 48)), "kick": (-16.5, (32, 48)), "snare": (-20.5, (32, 48)),
           "hats": (-34.5, (32, 48)), "ohat": (-36.0, (32, 48)), "perc": (-31.0, (40, 56)),
           "wave": (-17.0, (32, 48)), "crest": (-27.0, (72, 88)), "chops": (-23.0, (40, 56)),
           "lofi": (-40.0, (0, 8))}
MASTER_REGION = (80, 88)


def drums():
    st = {k: ses.stem() for k in ("kick", "snare", "hats", "ohat", "perc")}
    trig = []
    for R in sorted(GROOVE):
        light = R < 32 or R in (68, 69, 70)
        ksteps = [0, 10] if (R % 2 == 0 or light) else [0, 3, 10, 14]
        trig += ses.hits(st["kick"], KICK if R >= 16 else KICK_M, {R}, ksteps, mute=MUTE)
        trig += ses.hits(st["snare"], SNARE, {R}, [8], mute=MUTE)
        ses.hits(st["snare"], CLAP, {R}, [8], gain=0.6, mute=MUTE)
        if not light:
            ses.hits(st["snare"], SNARE, {R}, [15], gain=0.18, mute=MUTE)  # ghost
    for R in sorted(HATS):
        steps = range(16) if R >= 32 else range(0, 16, 2)
        ses.hits(st["hats"], HAT, {R}, steps, vel=[0.7, 0.35, 0.55, 0.35], pan=0.2, swing=0.18, rand=0.1,
                 mute=MUTE | ({(R, 3)} if R in ROLL_BARS else set()))
    for R in sorted(ROLL_BARS):  # triplet-32nd roll rising in level across beat 4
        for k in range(12):
            ses.add(st["hats"], HAT, ses.pos(R, 3 + k / 12), 0.25 + 0.5 * k / 11, pan=0.2)
    ses.hits(st["ohat"], OHAT_S, OHAT, [14], gain=0.7, pan=-0.2, mute=MUTE)
    for R in sorted(PERC):
        ses.hits(st["perc"], RIM, {R}, [6, 13] if R % 2 else [3, 11], gain=0.8, pan=(-0.35 if R % 2 else 0.35))
    for R in (68, 69, 70):  # pre-wave: muffled kicks doubling up
        for b in ((0, 2) if R < 70 else (0, 1, 2, 3)):
            ses.add(st["kick"], KICK_M, ses.pos(R, b), 0.85)
    for b in (0, 0.5, 1, 1.5, 2, 2.25, 2.5, 2.75):
        ses.add(st["kick"], KICK_M, ses.pos(71, b), 0.9)
    st["snare"] = st["snare"] + 0.35 * fx.reverb(st["snare"], PLATE) + 0.12 * fx.reverb(st["snare"], HALL)
    st["perc"] = st["perc"] + 0.3 * fx.reverb(st["perc"], ROOM)
    return st, trig


def wave_layer():
    """One wave note per 4-bar source chord (E or B), B notes 3 dB lower, like the original."""
    out = ses.stem()
    R = min(WAVE_BARS)
    while R <= max(WAVE_BARS):
        if R not in WAVE_BARS:
            R += 1
            continue
        n = 1
        while R + n in WAVE_BARS and SRC_OF[R + n] == SRC_OF[R] + n and (SRC_OF[R + n] - SRC_OF[R]) < 4 \
                and ses.root(SRC_OF[R + n]) == ses.root(SRC_OF[R]):
            n += 1
        root = ses.root(SRC_OF[R], 28, 39)
        length = (ses.pos(R + n) - ses.pos(R)) / dsp.SR + 0.25
        g = 1.0 if root % 12 == 4 else dsp.undb(-3)
        ses.add(out, synth.wave_bass(root, length, decay_db=11.0 * n / 4), ses.pos(R), g)
        R += n
    return out


def crest_layer():
    out = ses.stem()
    for R in range(min(CREST_BARS), max(CREST_BARS) + 1, 4):
        root = ses.root(SRC_OF[R], 28, 39) + 12
        r = synth.reese(root, (ses.pos(R + 4) - ses.pos(R)) / dsp.SR, cutoff=520, detune=12, lfo_hz=0.2, seed=R)
        t = np.arange(r.shape[1]) / dsp.SR
        ses.add(out, r * dsp.undb(-10 * t / t[-1]), ses.pos(R))
    return out


def chop_melody(bed_raw):
    """Pitched chops of each bar's own chord; intervals chosen to stay in B major per chord."""
    out = ses.stem()
    steps = [0, 3, 6, 8, 10, 13]
    for R in sorted(CHOP_BARS):
        e_chord = ses.root(SRC_OF[R]) % 12 == 4
        offs = [12, 12, 19, 12, 24, 19] if e_chord else [12, 12, 17, 12, 24, 17]
        if R % 4 == 3:
            offs = offs[:4] + [12, 12]
        for st, semi in zip(steps, offs):
            c = chop(ses, bed_raw, R, beat=1.5, semitones=semi, decay=0.09, length_beats=0.5)
            ses.add(out, c, ses.pos(R, st / 4), 0.9 if st in (0, 8) else 0.7)
    out = dsp.sos_filter(dsp.sos_filter(out, "highpass", 380, dsp.SR, 2), "lowpass", 7000, dsp.SR, 2)
    out = wobble(out, depth_cents=22, rate_hz=1.7)
    return out + 0.45 * fx.pingpong(out, 0.75 * ses.spb / dsp.SR, feedback=0.4, taps=6, lp=4200) + \
        0.25 * fx.reverb(out, HALL)


def fx_layer(bed_raw):
    out = ses.stem()
    for b, g in ((32, 0.5), (56, 0.3), (72, 0.45), (80, 0.45), (88, 0.3)):
        ses.add(out, CRASH, ses.pos(b), g)
    for b, g in ((32, 0.9), (72, 1.0)):
        ses.add(out, IMPACT, ses.pos(b), g)
        ses.add(out, synth.downlifter(2 * 4 * ses.spb / dsp.SR), ses.pos(b), 0.3)
    ses.add(out, synth.riser(8 * 4 * ses.spb / dsp.SR, seed=51), ses.pos(24), 0.45)
    ses.add(out, synth.riser(8 * 4 * ses.spb / dsp.SR, seed=52), ses.pos(64), 0.4)
    snare_roll(ses, out, SNARE, 28, level=0.9, end_beat=2.0)
    snare_roll(ses, out, SNARE, 68, level=0.7)
    for b in (8, 32, 72, 92):
        reverse_swell(ses, out, bed_raw, b, HALL)
    return out + 0.35 * fx.reverb(out, HALL)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / dsp.SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    # glitch edits on the raw bed before processing: stutters at phrase ends
    bed_edit = np.asarray(bed_raw, dtype=np.float64).copy()
    e8, e16 = int(ses.spb / 2), int(ses.spb / 4)
    for R in (47, 55, 87):
        a = ses.pos(R, 2)
        rep = np.concatenate([fx.stutter(bed_edit, a, e8, 2), fx.stutter(bed_edit, a, e16, 4)], axis=1)
        bed_edit[:, a:a + rep.shape[1]] = rep
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    for name in list(st):
        m.add(name, st.pop(name))
    pump = engine.duck(ses, trig, 6.0, release=0.16)
    m.add("wave", wave_layer() * pump)
    m.add("crest", crest_layer() * engine.duck(ses, trig, 8.0, release=0.2))

    T = END + 2
    hpf = ses.auto(90).set(0, 16, 30).set(27, 31.5, 90, 700, "exp").set(31.5, 32, 700).set(56, 64, 60) \
        .set(64, 71, 40).set(71, 72, 40, 600, "exp").set(88, T, 30)
    lpf = ses.auto(21000).set(0, 8, 1200, 8000, "exp").set(8, 12, 8000, 21000, "exp") \
        .set(56, 64, 6000).set(88, 96, 12000, 900, "exp").set(96, T, 900)
    gain = ses.auto(0.0).set(0, 2, -30, -4, 0.5).set(2, 8, -4, -2).set(8, 24, -2).set(24, 31.5, -2, 0) \
        .set(31.5, 32, -90).set(56, 64, -3).set(64, 71.75, -1.5).set(71.75, 72, -90) \
        .set(92, 96, -1, -30).set(96, T, -90)
    send = ses.auto(0.08).set(0, 8, 0.4).set(24, 32, 0.08, 0.3).set(56, 64, 0.45).set(64, 72, 0.3) \
        .set(88, 96, 0.3, 0.6)
    blur = ses.auto(0.0).set(0, 8, 0.5).set(32, 56, 0.55).set(56, 64, 0.8).set(72, 88, 0.55).set(88, 96, 0.5)
    duck_lo = ses.auto(3.0).set(32, 56, 8.0).set(72, 88, 8.0)
    duck_hi = ses.auto(1.5).set(32, 56, 4.0).set(72, 88, 4.0)
    bed, _ = bed_chain(ses, bed_edit, hpf, lpf, gain, trig, duck_lo=duck_lo, duck_hi=duck_hi, release=0.22,
                       width=1.25, send=send, ir=HALL, blur_mix=blur,
                       blur_regions=((0, 8), (32, 56), (56, 64), (72, 88), (88, 96)))
    m.add("bed", bed)
    del bed, bed_edit
    m.add("chops", chop_melody(bed_raw) * engine.duck(ses, trig, 4.0, release=0.15))
    lofi = lofi_texture(ses.N) * ses.auto(0.0).set(0, 12, 1.0).set(12, 16, 1.0, 0.0).set(56, 64, 1.0) \
        .set(88, 98, 1.0).v
    m.add("lofi", lofi)
    f = soft(fx_layer(bed_raw), 10000)
    m.add("fx", f, gain_db=-9.0 - dsp.db(np.abs(f).max()))
    del f
    print("stem gains dB:", m.gains)
    mix = m.mix
    for b0 in (31.5, 94.0):  # tape-stop dive into the first drop, and at the very end
        sl = ses.span(b0, b0 + 0.5 if b0 < 90 else 96)
        mix[:, sl] = fx.tape_stop(mix[:, sl])
    section_db = ses.auto(0.0).set(8, 24, -2.0).set(24, 32, -2.0, -1.0).set(32, 56, -0.5).set(56, 64, -3.0) \
        .set(64, 72, -2.5, -0.5).set(88, T, -1.0)
    m.mix = mix * dsp.undb(section_db.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
