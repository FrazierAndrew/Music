"""Remix of 2_5.wav: source bars re-arranged on a strict grid, new drums/bass/chops/FX, pre-master mix.

Usage: bash recipes/2_5/run.sh (from the repo root) runs the whole pipeline
Needs: tracks/2_5/analysis.json (analyze.py with the harmonic layer) and WORK/src_harm.npy, WORK/src_perc.npy
(separate.py). Writes WORK/mix_<version>.npy and one WORK/stem_<name>.npy per stem.
"""
import os
import sys
import json
import numpy as np
from scipy import signal
import dsp
import fx
import synth

SR = dsp.SR
SP = os.environ.get("REMIX_WORK", "work")  # large intermediate files
SRC = os.environ.get("REMIX_SRC", "src/2_5.wav")
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v1"
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- arrangement
# (name, first remix bar, bars, first source bar). Source bars were picked from analysis:
# 163-186 = D/G groove into the original's pre-drop gap bar (186), 187-202 = strongest G/Bm run,
# 139-154 = the only real chord movement (D, G, Bm, Em) -> breakdown, 211-250 = D/G drive + outro.
SECTIONS = [
    ("intro", 0, 16, 195),
    ("groove", 16, 16, 163),
    ("build", 32, 8, 179),
    ("drop1", 40, 16, 187),
    ("bridge", 56, 8, 203),
    ("breakdown", 64, 16, 139),
    ("drop2", 80, 24, 211),
    ("outro", 104, 16, 235),
]
END = SECTIONS[-1][1] + SECTIONS[-1][2]
TOTAL = END + 2  # two bars of reverb tail

an = json.load(open("tracks/2_5/analysis.json"))
BPM = an["bpm"]
SPB = 60.0 / BPM * SR  # samples per beat (float, never rounded cumulatively)
N = int(round(TOTAL * 4 * SPB))
SRC_BAR_T = np.array(an["beats"])[an["downbeat_phase"]::4]
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]


def pos(bar, beat=0.0):
    return int(round((bar * 4 + beat) * SPB))


def span(b0, b1):
    return slice(pos(b0), min(N, pos(b1)))


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


# ---------------------------------------------------------------- harmony
SNAP = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 6, 7: 7, 8: 7, 9: 9, 10: 11, 11: 11}  # to D major / B minor
BASS_SRC = np.array(an.get("beat_bass_harm_midi", an["beat_bass_midi"]))


def fold(m, lo, hi):
    while m > hi:
        m -= 12
    while m < lo:
        m += 12
    return m


def bar_roots(S, lo=31, hi=42):
    """Per-beat bass roots for a source bar: snapped to key, majority per bar, half-bar splits kept."""
    k = an["downbeat_phase"] + 4 * S
    notes = []
    for v in BASS_SRC[k:k + 4]:
        r = int(round(v))
        notes.append(fold(r - r % 12 + SNAP[r % 12], lo, hi))
    if notes[0] == notes[1] and notes[2] == notes[3] and notes[0] != notes[2]:
        return [notes[0]] * 2 + [notes[2]] * 2
    vals, counts = np.unique(notes, return_counts=True)
    best = vals[counts == counts.max()]
    m = notes[0] if notes[0] in best else int(best[0])
    return [m] * 4


ROOTS = {R: bar_roots(S) for R, S in MAPPING}


# ---------------------------------------------------------------- helpers
class Auto:
    """Per-sample automation curve, written in bars."""

    def __init__(self, default):
        self.v = np.full(N, float(default))

    def set(self, b0, b1, v0, v1=None, shape="lin"):
        s = span(b0, b1)
        n = s.stop - s.start
        if v1 is None:
            self.v[s] = v0
        elif shape == "exp":
            self.v[s] = v0 * (v1 / v0) ** np.linspace(0, 1, n)
        else:
            self.v[s] = v0 + (v1 - v0) * np.linspace(0, 1, n) ** (shape if isinstance(shape, float) else 1.0)
        return self


def stem():
    return np.zeros((2, N), np.float32)


def pan_mono(x, pan):
    th = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(th), x * np.sin(th)])


def add(dst, snd, at, gain=1.0, pan=0.0):
    snd = snd if snd.ndim == 2 else pan_mono(snd, pan)
    if at < 0:
        snd, at = snd[:, -at:], 0
    b = min(N, at + snd.shape[1])
    if at < N:
        dst[:, at:b] += gain * snd[:, :b - at]


def resample_speed(x, r):
    """Play x at speed r (pitch up for r > 1)."""
    n = int(len(x) / r)
    return np.interp(np.arange(n) * r, np.arange(len(x)), x)


def assemble(layer, pre=0.006, jump_tail=0.04):
    """Place each source bar at its remix bar on the strict grid, crossfading in the pre-roll."""
    out = np.zeros((2, N), np.float32)
    p = int(pre * SR)
    for j, (R, S) in enumerate(MAPPING):
        contiguous = j + 1 < len(MAPPING) and MAPPING[j + 1] == (R + 1, S + 1)
        t = p if contiguous else int(jump_tail * SR)
        a = int(round(SRC_BAR_T[S] * SR)) - p
        length = pos(R + 1) - pos(R) + t
        seg = layer[:, a:a + length].astype(np.float32)
        env = np.ones(seg.shape[1], np.float32)
        env[:p] = np.linspace(0, 1, p)
        env[-t:] = np.linspace(1, 0, t)
        o = pos(R) - p
        if o < 0:
            seg, env, o = seg[:, -o:], env[-o:], 0
        out[:, o:o + seg.shape[1]] += seg * env
    return out


# ---------------------------------------------------------------- sounds
KICK = synth.kick(body_tau=0.075, click=0.9)
KICK_MUFFLED = dsp.sos_filter(KICK, "lowpass", 260, SR, 2)
CLAP = synth.clap()
SNARE = synth.snare()
HAT = synth.hat()
OHAT = synth.open_hat()
RIDE = synth.ride()
RIM = synth.rim()
TOMS = [synth.tom(f) for f in (196, 165, 131, 110)]
CRASH = synth.crash()
IMPACT = synth.impact()
ROOM = fx.make_ir(rt60=0.9, predelay=0.01, seed=21)
HALL = fx.make_ir(rt60=3.8, predelay=0.03, seed=22)
HUGE = fx.make_ir(rt60=6.5, predelay=0.05, hi_damp=0.6, seed=23)

# ---------------------------------------------------------------- pattern map
KICK_BARS = bars((8, 39), (40, 64), (80, 116))
CLAP_BARS = bars((16, 39), (40, 56), (80, 112))
HAT_BARS = bars((4, 39), (40, 64), (80, 118))
OHAT_BARS = bars((24, 39), (40, 56), (80, 104))
RIDE_BARS = bars((48, 56), (88, 104))
RIM_BARS = bars((24, 32), (56, 63))
BASS_BARS = bars((16, 38), (40, 63), (80, 111))
STAB_BARS = bars((48, 56), (84, 104))
# (bar, beat) slots where drums and bass sit out (fills, gaps, glitches)
MUTE = {(15, 3), (31, 3), (63, 2), (63, 3), (95, 2), (95, 3), (103, 3)}


def drums():
    kick, clap, hats, ohat, ride, perc = stem(), stem(), stem(), stem(), stem(), stem()
    triggers = []
    for R in range(TOTAL):
        for beat in range(4):
            if (R, beat) in MUTE:
                continue
            if R in KICK_BARS:
                add(kick, KICK, pos(R, beat))
                triggers.append(pos(R, beat))
            if R in CLAP_BARS and beat in (1, 3):
                add(clap, CLAP, pos(R, beat), 1.0)
                add(clap, SNARE, pos(R, beat), 0.35)
            if R in HAT_BARS:
                scale = 0.55 if R < 8 else 0.8 if R < 16 else 1.0
                for k, v in enumerate((0.42, 0.72, 0.30, 0.62)):
                    add(hats, HAT, pos(R, beat + k / 4), scale * v * rng.uniform(0.9, 1.08), pan=0.18)
            if R in OHAT_BARS:
                add(ohat, OHAT, pos(R, beat + 0.5), 0.8, pan=-0.15)
            if R in RIDE_BARS:
                add(ride, RIDE, pos(R, beat), 0.8, pan=0.3)
                add(ride, RIDE, pos(R, beat + 0.5), 0.45, pan=0.3)
        if R in RIM_BARS:
            for i, s16 in enumerate((3, 6, 11, 14)):
                add(perc, RIM, pos(R, s16 / 4), 0.8, pan=(-0.35, 0.35)[i % 2])
    # tom fills on the muted last beats of phrases
    for R in (31, 103):
        for i, tom in enumerate(TOMS):
            add(perc, tom, pos(R, 3 + i / 4), 0.9, pan=-0.4 + 0.27 * i)
    # breakdown build: muffled kick, accelerating into the gap
    for R in (76, 77, 78):
        for beat in range(4):
            add(kick, KICK_MUFFLED, pos(R, beat), 0.9)
    for b in (0, 0.5, 1, 1.5, 2, 2.25, 2.5, 2.75):
        add(kick, KICK_MUFFLED, pos(79, b), 0.95)
    return dict(kick=kick, clap=clap, hats=hats, ohat=ohat, ride=ride, perc=perc), triggers


def bass_line():
    out = stem()
    sixteenth = SPB / 4 / SR
    for R in sorted(BASS_BARS):
        growl = 0.55 if 40 <= R < 56 else 0.8 if R >= 80 else 0.25 if 56 <= R < 64 else 0.0
        roots = ROOTS[R]
        for beat in range(4):
            if (R, beat) in MUTE:
                continue
            for k, vel in ((1, 0.95), (2, 0.72), (3, 0.86)):
                m = roots[beat] + (12 if (R >= 80 and beat in (1, 3) and k == 3) else 0)
                add(out, synth.bass_note(m, 0.86 * sixteenth, growl=growl), pos(R, beat + k / 4), vel)
    # breakdown: sustained sub drone per 4-bar chord block, fading before the build
    for R in range(64, 76, 4):
        m = fold(ROOTS[R][0], 28, 39)
        d = synth.sub_drone(m, (pos(R + 4) - pos(R)) / SR + 0.6, attack=0.5, release=0.9)
        add(out, d, pos(R), 0.55)
    return out


def snare_roll(dst, b0, level=1.0):
    """4-bar roll: quarters, 8ths, 16ths, then 32nds into a 1-beat gap. Pitch and level rise."""
    hits = [b0 * 4 + i for i in range(4)] + [b0 * 4 + 4 + i / 2 for i in range(8)] + \
           [b0 * 4 + 8 + i / 4 for i in range(16)] + [b0 * 4 + 12 + i / 8 for i in range(24)]
    first, last = hits[0], hits[-1]
    for h in hits:
        u = (h - first) / (last - first)
        snd = resample_speed(SNARE, 1.0 + 0.55 * u)
        add(dst, snd, int(round(h * SPB)), level * (0.25 + 0.75 * u ** 1.5), pan=0.1)


def fx_layer(bed_raw):
    out = stem()
    # transitions into each section
    for b in (16, 40, 64, 80, 104):
        add(out, CRASH, pos(b), 0.55 if b in (40, 80) else 0.35)
    for b in (40, 80):
        add(out, IMPACT, pos(b), 0.9)
        add(out, synth.downlifter(2 * 4 * SPB / SR), pos(b), 0.35)
    add(out, IMPACT, pos(64), 0.5)
    for b in (88, 96):
        add(out, CRASH, pos(b), 0.3)
    # risers
    add(out, synth.riser(8 * 4 * SPB / SR, seed=31), pos(32), 0.5)
    add(out, synth.riser(8 * 4 * SPB / SR, seed=32), pos(72), 0.36)
    add(out, synth.riser(4 * SPB / SR, f0=1500, f1=12000, seed=33), pos(63), 0.35)
    snare_roll(out, 36)
    snare_roll(out, 76, level=0.7)
    # reverse crash and reverse reverb of the next chord into big downbeats
    rc = CRASH[:, :int(1.5 * 4 * SPB)][:, ::-1]
    for b in (8, 40, 80):
        add(out, rc * np.linspace(0, 1, rc.shape[1]) ** 2, pos(b) - rc.shape[1], 0.35)
    for b in (16, 40, 64, 80):
        chord = bed_raw[:, pos(b):pos(b, 1)]
        sw = synth.reverse_swell(chord, HALL)
        add(out, sw[:, -int(2 * SPB):] * np.linspace(0, 1, int(2 * SPB)) ** 1.5, pos(b) - int(2 * SPB), 0.6)
    return out


def chord_stabs(bed_raw):
    """Octave-up chops of each bar's own chord (taken between kicks), syncopated, ping-pong delayed."""
    out = stem()
    for R in sorted(STAB_BARS):
        src = bed_raw[:, pos(R, 1.5):pos(R, 1.5) + int(SPB)]
        chop = np.stack([signal.resample_poly(c, 1, 2) for c in src])
        t = np.arange(chop.shape[1]) / SR
        chop = chop * np.minimum(t / 0.003, 1) * np.exp(-t / 0.07)
        for s16 in (3, 6, 11, 14):
            add(out, chop, pos(R, s16 / 4), 1.0)
    out = dsp.sos_filter(out, "highpass", 450, SR, 2)
    return out + 0.55 * fx.pingpong(out, 0.75 * SPB / SR, feedback=0.42, taps=6, lp=4500)


def bed_chain(bed_raw, triggers):
    """Source harmonic layer -> blur/automation/filters/sidechain/space."""
    hpf = Auto(140).set(0, 16, 100).set(34, 39, 140, 1100, "exp").set(39, 40, 1100) \
        .set(56, 62.5, 180).set(62.5, 64, 180, 1600, "exp").set(64, 72, 100).set(72, 76, 100, 160, "exp") \
        .set(76, 79.75, 160, 900, "exp").set(79.75, 80, 900)
    lpf = Auto(21000).set(0, 8, 300, 2600, "exp").set(8, 16, 2600, 21000, "exp").set(56, 62.5, 3200) \
        .set(62.5, 63, 3200, 21000, "exp").set(64, 72, 5000, 12000, "exp").set(72, 80, 12000, 21000, "exp") \
        .set(108, TOTAL, 21000, 320, "exp")
    # section dynamics: groove sits under the drops, breakdown drops away and climbs back
    gain = Auto(0.0).set(0, 2, -36, -8, 0.5).set(2, 8, -8, -5).set(8, 16, -5, -2).set(16, 32, -1.5) \
        .set(32, 39.75, -1.5, 0).set(39.75, 40, -90).set(56, 64, -2).set(64, 72, -6) \
        .set(72, 79.75, -6, -3).set(79.75, 80, -90).set(104, 116, -1).set(116, 120, -1, -30) \
        .set(120, TOTAL, -90)
    blur_mix = Auto(0.0).set(0, 6, 1.0).set(6, 8, 1.0, 0.0).set(64, 72, 1.0).set(72, 78, 1.0, 0.0)
    send = Auto(0.08).set(0, 8, 0.5).set(8, 16, 0.5, 0.15).set(56, 64, 0.25).set(64, 72, 0.45) \
        .set(72, 80, 0.45, 0.2).set(104, 120, 0.1, 0.45)

    # glitch edits on the raw bed (filters sweep over them afterwards)
    bed = bed_raw.astype(np.float64)
    e8, e16 = int(SPB / 2), int(SPB / 4)
    for R in (63, 95):
        a = pos(R, 2)
        rep = np.concatenate([fx.stutter(bed, a, e8, 2), fx.stutter(bed, a, e16, 4)], axis=1)
        bed[:, a:a + rep.shape[1]] = rep[:, :min(rep.shape[1], N - a)]

    # blurred (de-pumped) versions only where used
    blurred = np.zeros_like(bed)
    for b0, b1 in ((0, 8), (64, 78)):
        s = span(max(0, b0 - 1), b1 + 1)
        blurred[:, s] = fx.spectral_blur(bed[:, s], 1.6 * SPB / SR)
    m = blur_mix.v
    bed = bed * (1 - m) + blurred * m

    bed = fx.tv_filter(bed, "highpass", hpf.v)
    bed = fx.tv_filter(bed, "lowpass", lpf.v)
    # gentle two-band sidechain so the new kick owns the low end
    duck_lo = fx.duck_curve(N, triggers, 3.0, release=0.12)
    duck_hi = fx.duck_curve(N, triggers, 1.0, release=0.12)
    lo = dsp.sos_filter(bed, "lowpass", 400, SR, 2)
    bed = lo * duck_lo + (bed - lo) * duck_hi
    bed = fx.widen(bed, 1.2)
    bed = bed * dsp.undb(gain.v)
    wet = fx.reverb(bed * send.v, HALL)
    return bed, wet, blurred


def shimmer(blurred):
    """Octave-up, high-passed, huge-reverb copy of the de-pumped bed (intro + breakdown)."""
    out = stem()
    for b0, b1 in ((0, 8), (64, 78)):
        s = span(b0, b1)
        up = fx.rubberband(blurred[:, s], pitch=2.0)[:, :s.stop - s.start]
        up = dsp.sos_filter(up, "highpass", 900, SR, 2)
        n = up.shape[1]
        env = np.minimum(np.linspace(0, 1, n) * 4, 1) * np.minimum(np.linspace(1, 0, n) * 3, 1)
        out[:, s.start:s.start + n] += up * env
    return fx.reverb(out, HUGE)


def lufs_region(x, b0, b1):
    return dsp.lufs(x[:, span(b0, b1)])


# target short-term LUFS per stem, measured over reference bars (genre-typical balance)
TARGETS = {"bed": (-16.0, (80, 96)), "kick": (-17.0, (80, 96)), "bass": (-18.0, (80, 96)),
           "clap": (-23.5, (80, 96)), "hats": (-29.0, (80, 96)), "ohat": (-29.5, (80, 96)),
           "ride": (-30.0, (88, 104)), "perc": (-28.0, (24, 32)), "stabs": (-25.0, (84, 100)),
           "top": (-31.0, (80, 96)), "shimmer": (-25.0, (64, 76))}


class Mixer:
    """Calibrates each stem to its target, saves it, and sums it (one stem in memory at a time)."""

    def __init__(self):
        self.mix = np.zeros((2, N), np.float64)
        self.gains = {}

    def add(self, name, x, gain_db=None):
        if gain_db is None:
            target, (b0, b1) = TARGETS[name]
            gain_db = target - lufs_region(x, b0, b1)
        self.gains[name] = round(float(gain_db), 1)
        x = (x * dsp.undb(gain_db)).astype(np.float32)
        np.save(f"{SP}/stem_{name}.npy", x)
        self.mix += x


def main():
    print(f"{BPM:.3f} BPM, {TOTAL} bars, {N / SR:.1f}s")
    harm = np.load(f"{SP}/src_harm.npy", mmap_mode="r")
    perc = np.load(f"{SP}/src_perc.npy", mmap_mode="r")
    bed_raw = assemble(harm)
    m = Mixer()

    d, triggers = drums()
    d["clap"] = d["clap"] + 0.22 * fx.reverb(d["clap"], ROOM) + 0.1 * fx.reverb(d["clap"], HALL)
    d["perc"] = d["perc"] + 0.3 * fx.reverb(d["perc"], ROOM)
    for name in ("kick", "clap", "hats", "ohat", "ride", "perc"):
        m.add(name, d.pop(name))
    print("drums done")

    m.add("bass", bass_line() * fx.duck_curve(N, triggers, 5.0, attack=0.002, release=0.07))
    bed, bed_wet, blurred = bed_chain(bed_raw, triggers)
    m.add("bed", bed + bed_wet)
    del bed, bed_wet
    print("bed done")
    m.add("shimmer", shimmer(blurred))
    del blurred
    m.add("stabs", chord_stabs(bed_raw) * fx.duck_curve(N, triggers, 3.0, release=0.1))
    top = dsp.sos_filter(assemble(perc).astype(np.float64), "highpass", 5000, SR, 2)
    m.add("top", top * Auto(0.0).set(40, 56, 1.0).set(80, 104, 1.0).v)
    del top
    fxl = fx_layer(bed_raw)
    fxl = fxl + 0.35 * fx.reverb(fxl, HALL)
    m.add("fx", fxl, gain_db=-9.0 - dsp.db(np.abs(fxl).max()))  # fx peaks near -9 dBFS pre-master
    del fxl
    print("stem gains dB:", m.gains)

    mix = m.mix
    s = span(55.75, 56)  # tape stop on the last beat of drop 1
    mix[:, s] = fx.tape_stop(mix[:, s])
    # mix-bus section levels so the drops are the peak of the arc
    section_db = Auto(0.0).set(16, 32, -1.5).set(32, 40, -1.5, 0).set(56, 64, -1.5) \
        .set(64, 80, -2.5, -1.0).set(104, TOTAL, -1.0)
    mix *= dsp.undb(section_db.v)
    print(f"pre-master: drop2 LUFS {lufs_region(mix, 80, 96):.2f}, integrated {dsp.lufs(mix):.2f}, "
          f"peak {dsp.db(np.abs(mix).max()):.2f} dBFS")
    np.save(f"{SP}/mix_{VERSION}.npy", mix.astype(np.float32))


if __name__ == "__main__":
    main()
