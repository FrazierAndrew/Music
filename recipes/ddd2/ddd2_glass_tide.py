"""ddd2, "Glass Tide". Engine: RESONANCE. Every new sound is a physical model rung in the key of your chords.

Material: neural stems (engine/separate_mdx.py) instead of HPSS. Your pad (other + vocals stems, de-pumped so
the old quarter-note sidechain is gone), your bass stem (the tidal wave itself, untouched), and a drum kit
recovered from your own drum stem (onset-aligned medians of your kick and snare).
New voices, all tuned to the chord under them:
- glass: banks of two-pole resonators with tuned-bar mode ratios (octave overtones, like celesta), struck by tiny noise clicks in an arpeggio
  pattern, and in the drops also struck by the transients of your original drums, so the old groove rings as
  harmony;
- strings: Karplus-Strong plucked strings (exactly tuned) playing a motif built from your pad's own top line
  (it sighs D#6 to C#6); octave FM bell sparkle on top in the drops;
- breath: an additive pad whose partials drift independently, upper-structure voicings of your chords;
- choir: grains of your pad an octave, a twelfth and two octaves up;
- coda: your last chord paulstretched x12 while the glass keeps ringing.
Designed reverbs (early reflections, per-band decay, bloom) replace the old noise reverb. Master at -2 dBTP.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_glass_tide.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
import sounddesign as sd
import space
import voices as V
from engine import Session, Mixer, reverse_swell
from ddd2_harmony import chord_of_source_bar, blocks, silence

SR = dsp.SR
W = engine.WORK
TAG = "ddd2_glass_tide"
SECTIONS = [
    ("dawn", 0, 8, 0),
    ("verse", 8, 16, 20),
    ("rise", 24, 4, 48),
    ("drop", 28, 16, 76),
    ("deep", 44, 8, 68),
    ("lift", 52, 4, 96),
    ("wave", 56, 8, 100),
    ("wave2", 64, 8, 100),
    ("ebb", 72, 4, 108),
    ("glass", 76, 8, None),
]
END = 84
T = END + 2
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_bed_dp.npy", None, T, seed=41)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS if s0 is not None for i in range(nb)]
SRC_OF = dict(MAPPING)
CHORD = {R: chord_of_source_bar(S) for R, S in MAPPING}
CHORD.update({R: "B" for R in range(76, T)})


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


# chord tones as heard in your pad (chroma: E bars D# F# B A# over E, B bars B D# F# A# with C# on top)
GLASS_TONES = {"E": [71, 75, 78, 82, 83, 87], "B": [71, 73, 75, 78, 82, 85], "D#m": [70, 73, 75, 78, 82, 87]}
BREATH = {"E": [75, 78, 82, 83], "B": [73, 78, 82, 85], "D#m": [73, 78, 82, 87]}
# motif from your pad's top line (D#6 -> C#6 sigh); (bar in phrase, 16th step, MIDI, length in 16ths)
MOTIF = {
    "E": [(0, 0, 87, 3), (0, 3, 85, 3), (0, 6, 82, 2), (0, 8, 78, 6), (0, 14, 82, 2),
          (1, 0, 85, 4), (1, 4, 82, 4), (1, 8, 83, 8),
          (2, 0, 87, 3), (2, 3, 85, 3), (2, 6, 82, 2), (2, 8, 78, 4), (2, 12, 82, 2), (2, 14, 85, 2),
          (3, 0, 87, 2), (3, 2, 85, 2), (3, 4, 82, 4), (3, 10, 83, 6)],
    "B": [(0, 0, 85, 3), (0, 3, 82, 3), (0, 6, 78, 2), (0, 8, 75, 6), (0, 14, 78, 2),
          (1, 0, 82, 4), (1, 4, 78, 4), (1, 8, 75, 8),
          (2, 0, 85, 3), (2, 3, 82, 3), (2, 6, 78, 2), (2, 8, 75, 4), (2, 12, 78, 2), (2, 14, 82, 2),
          (3, 0, 85, 2), (3, 2, 83, 2), (3, 4, 82, 4), (3, 10, 78, 6)],
    "D#m": [(0, 0, 82, 6), (0, 8, 78, 6), (1, 0, 75, 8), (2, 0, 82, 6), (2, 8, 85, 6), (3, 0, 82, 12)],
}
ARP = [5, 3, 4, 1, 5, 2, 4, 0, 5, 3, 4, 1, 3, 2, 4, 0]  # index into GLASS_TONES per 16th
ACCENT = [1.0, 0.45, 0.6, 0.85, 0.5, 0.6, 0.9, 0.45, 0.6, 0.85, 0.5, 0.6, 0.95, 0.5, 0.6, 0.55]  # 3+3+2 feel

KICK_BARS = bars((12, 27), (28, 44), (64, 72))
SOFT_KICK_BARS = bars((56, 64))
SNARE_BARS = bars((12, 27), (28, 44), (64, 72))
HAT_BARS = bars((16, 27), (28, 44), (66, 72))
MOTIF_BARS = bars((16, 24), (28, 44), (44, 52), (64, 72))
BREATH_BARS = bars((28, 44), (52, 56), (56, 72))
MUTE = {(27, 3), (55, 3), (43, 3)}
CHORD_STEMS, HARMONY_REF = ["glass", "pluck", "breath"], ["bed"]
CHORD_BARS = bars((8, 44), (56, 72))

HALL = space.hall_ir(rt60=3.8, predelay=0.025, dark=0.55, bloom=0.25, seed=11)
HUGE = space.hall_ir(rt60=7.5, predelay=0.04, dark=0.7, bloom=0.8, seed=12)
ROOM = space.hall_ir(rt60=0.7, predelay=0.004, dark=0.3, early=1.0, seed=13)

TARGETS = {"bed": (-16.5, (28, 44)), "bass": (-19.7, (28, 44)), "kick": (-17.5, (28, 44)),
           "snare": (-22.0, (28, 44)), "hats": (-29.0, (28, 44)), "glass": (-22.5, (28, 44)),
           "pluck": (-21.5, (28, 44)), "breath": (-26.0, (28, 44)), "choir": (-25.0, (44, 52)),
           "coda": (-20.0, (76, 84)), "tape": (-44.0, (0, 8))}
MASTER_REGION = (64, 72)
MASTER_TARGET = -10.0
MASTER_CEILING = -1.9  # -2.0 dBTP: Spotify's guidance for masters louder than -14 LUFS


def hp(x, f, order=2):
    return dsp.sos_filter(np.asarray(x, dtype=np.float64), "highpass", f, SR, order)


def lp(x, f, order=2):
    return dsp.sos_filter(np.asarray(x, dtype=np.float64), "lowpass", f, SR, order)


# ---------------------------------------------------------------- your material

def bed_layer(bed_raw):
    x = hp(bed_raw, 110)
    bloom = ses.auto(16000).set(0, 8, 700, 14000, "exp").set(44, 52, 3200).set(72, 76, 9000, 2500, "exp") \
        .set(76, T, 2500)
    x = fx.tv_filter(x, "lowpass", sd.smooth_curve(bloom.v))
    rise = ses.auto(20.0).set(24, 27.75, 120, 1200, "exp").set(52, 55.5, 120, 700, "exp")
    x = fx.tv_filter(x, "highpass", sd.smooth_curve(rise.v))
    x = space.width(x, 1.12) + 0.22 * space.ensemble(x, seed=4)
    wet = space.send(x * ses.auto(0.25).set(0, 8, 0.45).set(44, 56, 0.5).set(72, T, 0.6).smooth(60).v, HALL)
    return x + 0.55 * wet


def bass_layer(bass_raw):
    x = np.asarray(bass_raw, dtype=np.float64) * ses.auto(1.0).set(0, 8, 0.0).set(8, 10, 0.0, 1.0)\
        .set(24, 27.75, 1.0, 0.25).set(55, 56, 1.0, 0.0).set(72, 76, 1.0, 0.0).set(76, T, 0.0).smooth(40).v
    return x


def kit():
    kick = hp(np.load(f"{W}/ddd2_kit_kick_2.npy"), 28, 2)
    snare = hp(np.load(f"{W}/ddd2_kit_snare_3.npy"), 140, 2)
    body = synth.snare(decay=0.16, tone=205)
    clap = synth.clap(decay=0.18)
    layer = np.zeros((2, max(snare.shape[1], len(clap))))
    layer[:, :snare.shape[1]] += snare / (np.abs(snare).max() + 1e-9)
    layer[:, :len(body)] += 0.35 * body
    layer[:, :len(clap)] += 0.45 * clap
    layer = layer + 0.35 * space.convolve(layer, ROOM)[:, :layer.shape[1]]
    return kick, layer


def hat(decay, seed, bright=1.0):
    rng = np.random.default_rng(seed)
    n = int((decay * 5) * SR)
    t = np.arange(n) / SR
    y = dsp.sos_filter(rng.standard_normal(n), "bandpass", (6500, 15500), SR, 2)
    y += 0.4 * V.resonate(np.r_[np.zeros(10), 1.0, np.zeros(n - 11)], [104, 109], decay=0.08, modes=V.BELL)[0]
    return y * np.exp(-t / decay) * np.minimum(t / 0.0007, 1) * bright


def drums():
    kick, snare = kit()
    st = {k: ses.stem() for k in ("kick", "snare", "hats")}
    trig = []
    for R in sorted(KICK_BARS):
        steps = [0, 10] if R < 28 else ([0, 7, 10, 3] if R % 2 else [0, 7, 10])
        vel = [1.0, 0.95] if R < 28 else ([1.0, 0.8, 0.95, 0.45] if R % 2 else [1.0, 0.8, 0.95])
        if R >= 28 and R % 4 == 3:
            steps, vel = steps + [14], vel + [0.6]
        trig += ses.hits(st["kick"], kick, {R}, steps, vel=vel, mute=MUTE, jitter_ms=1.5)
    for R in sorted(SOFT_KICK_BARS):
        trig += ses.hits(st["kick"], lp(kick, 900), {R}, [0], gain=0.7, mute=MUTE)
    for R in sorted(SNARE_BARS):
        ses.hits(st["snare"], snare, {R}, [8], mute=MUTE, late_ms=6, jitter_ms=2)
        if R >= 28 and R % 2:
            ses.hits(st["snare"], snare, {R}, [15], gain=0.22, mute=MUTE, late_ms=4)
    closed, opened = hat(0.022, 3), hat(0.11, 4, 0.8)
    for R in sorted(HAT_BARS):
        ses.hits(st["hats"], closed, {R}, range(16), vel=[0.55, 0.25, 0.75, 0.3, 0.5, 0.25, 0.8, 0.3] * 2,
                 pan=0.25, swing=0.1, rand=0.2, mute=MUTE, jitter_ms=3)
        if R % 2 == 1:
            ses.hits(st["hats"], opened, {R}, [14], gain=0.6, pan=-0.2, mute=MUTE)
    st["snare"] = st["snare"] + 0.16 * space.send(st["snare"], HALL, hp=300)
    st["hats"] = st["hats"] + 0.1 * space.send(st["hats"], HALL, hp=2000)
    st["kick"] = sd.tube(st["kick"], drive=1.3)
    return st, trig


# ---------------------------------------------------------------- resonance voices

def click_train(times_gains, n):
    x = np.zeros(n)
    rng = np.random.default_rng(7)
    burst = dsp.sos_filter(rng.standard_normal(96), "bandpass", (2000, 9000), SR, 2) * np.hanning(96)
    for p, g in times_gains:
        if 0 <= p < n - 96:
            x[p:p + 96] += g * burst
    return x


def glass(drums_raw):
    out = ses.stem()
    density = {**{R: 2 for R in range(0, 8)}, **{R: 2 for R in range(8, 24)}, **{R: 1 for R in range(24, 26)},
               **{R: 0.5 for R in range(26, 28)}, **{R: 1 for R in range(28, 44)}, **{R: 3 for R in range(44, 52)},
               **{R: 1 for R in range(52, 54)}, **{R: 0.5 for R in range(54, 56)}, **{R: 4 for R in range(56, 64)},
               **{R: 1 for R in range(64, 72)}, **{R: 2 for R in range(72, 76)}, **{R: 6 for R in range(76, 84)}}
    decay = {R: (2.2 if R < 56 else 3.2) for R in range(T)}
    rng = np.random.default_rng(17)
    for R0, nb, c in blocks(CHORD, set(range(0, 84))):
        a, e = ses.pos(R0), min(ses.N, ses.pos(R0 + nb) + int(4 * SR))
        n = e - a
        tones = GLASS_TONES[c]
        per_note = {m: [] for m in tones}
        for R in range(R0, R0 + nb):
            step = density[R]
            k = 0.0
            while k < 16:
                i = int(k) % 16
                if not ((R, int(k / 4)) in MUTE) and not (R < 8 and rng.random() < 0.4):
                    p = ses.pos(R, k / 4) - a + int(rng.uniform(-2, 2) * SR / 1000)
                    per_note[tones[ARP[i]]].append((p, ACCENT[i] * (0.55 if R < 24 else 1.0)))
                k += step
        y = np.zeros((2, n))
        for m, hits in per_note.items():
            if hits:
                y += V.resonate(click_train(hits, n), [m], decay=decay[R0], modes=V.TUNED, seed=m)
        # your original drums strike the glass too (drops only): their 3 kHz+ transients, through all tones
        if any(R in bars((28, 44), (64, 72)) for R in range(R0, R0 + nb)):
            dr = hp(np.asarray(drums_raw[:, a:e]).mean(0), 3000, 4)
            dr = dr * np.minimum(1, np.abs(dr) / (np.percentile(np.abs(dr), 99.5) + 1e-9))
            y += 0.5 * V.resonate(dr, tones[1:5], decay=1.4, modes=V.TUNED, seed=R0)
        out[:, a:e] += y[:, :min(n, ses.N - a)]
    out = hp(out, 380)
    out = out * dsp.undb(ses.auto(0.0).set(0, 8, -4.0).set(44, 52, -2.0).set(76, T, -1.0, -12.0).smooth(80).v)
    wet = space.send(out, HALL, hp=500) + 0.5 * fx.pingpong(out, 0.75 * ses.spb / SR, feedback=0.3, taps=5, lp=7000)
    return out + 0.25 * space.ensemble(out, seed=9) + 0.6 * wet


def pluck_note(m, length, bright, seed):
    s = V.ks_pluck(V.midi_hz(m), length + 1.2, decay=1.7, bright=bright, seed=seed)
    return s


def strings():
    out, bell = ses.stem(), ses.stem()
    for R0, nb, c in blocks(CHORD, MOTIF_BARS):
        phrase = MOTIF[c]
        for b0 in range(R0, R0 + nb, 4):
            for bar_off, st, m, ln in phrase:
                R = b0 + bar_off
                if R not in MOTIF_BARS or (R, int(st / 4)) in MUTE:
                    continue
                up = 12 if R in bars((64, 72)) else 0
                if R in bars((44, 52)) and st > 6:
                    continue  # breakdown: only the first notes of each bar, sparse
                length = ln * ses.spb / 4 / SR
                vel = 0.85 if st % 4 == 0 else 0.7
                ses.add(out, pluck_note(m + up - 12 * (R < 24), length, 0.5 + 0.2 * (R >= 28), R * 31 + st),
                        ses.pos(R, st / 4) + int(np.random.default_rng(R * 16 + st).uniform(-3, 3) * 48), vel,
                        pan=0.18 * np.sin(m))
                if R in bars((28, 44), (64, 72)):
                    ses.add(bell, V.fm_bell(V.midi_hz(m + up + 12), length=1.4, ratio=4.0, index=1.2, decay=0.9),
                            ses.pos(R, st / 4), 0.22 * vel, pan=-0.3 * np.sin(m))
    y = sd.tube(out, drive=1.2) + bell
    y = hp(y, 180)
    wet = space.send(y, HALL, hp=400) + 0.55 * fx.pingpong(y, 0.75 * ses.spb / SR, feedback=0.38, taps=6, lp=6000)
    return y + 0.7 * wet


def breath():
    out = ses.stem()
    for R0, nb, c in blocks(CHORD, BREATH_BARS):
        length = (ses.pos(R0 + nb) - ses.pos(R0)) / SR + 2.5
        p = V.breath_pad(BREATH[c], length, attack=1.4, release=2.5, partials=10, bright=0.55, motion=0.45,
                         seed=R0)
        a = ses.pos(R0)
        k = min(p.shape[1], ses.N - a)
        out[:, a:a + k] += p[:, :k]
    out = hp(out, 300)
    return out + 0.3 * space.ensemble(out, seed=5) + 0.8 * space.send(out, HUGE, hp=400)


def choir(bed_raw):
    regions = [(ses.pos(44), ses.pos(52), ses.pos(44), ses.pos(52), 55),
               (ses.pos(64), ses.pos(72), ses.pos(64), ses.pos(72), 35),
               (ses.pos(76), ses.pos(84), ses.pos(72), ses.pos(76), 25)]
    y = sd.granular(bed_raw, ses.N, regions, grain=(0.09, 0.28), pitches=(12, 19, 24), weights=(0.5, 0.3, 0.2),
                    spread=0.9, seed=23, hp=900.0)
    y = lp(y, 9000) * ses.auto(1.0).set(44, 46, 0.0, 1.0).set(64, 66, 0.0, 1.0).set(80, T, 1.0, 0.0).smooth(80).v
    return y + 1.0 * space.send(y, HUGE, hp=900)


def coda():
    """Your final chord paulstretched x12, opening and closing slowly."""
    harm = np.load(f"{W}/ddd2_bed_dp.npy", mmap_mode="r")
    t0, t1 = ses.src_bar_t[104], ses.src_bar_t[106]
    seg = np.asarray(harm[:, int(t0 * SR):int(t1 * SR)], dtype=np.float64)
    st = sd.paulstretch(seg, 12.0, window_s=0.35, seed=5)
    out = ses.stem()
    a = ses.pos(73)
    k = min(st.shape[1], ses.N - a)
    out[:, a:a + k] = st[:, :k]
    out = hp(out, 120) * ses.auto(0.0).set(73, 77, 0.0, 1.0, 1.5).set(77, 82, 1.0).set(82, T, 1.0, 0.0, 1.3).smooth(100).v
    out = fx.tv_filter(out, "lowpass", sd.smooth_curve(ses.auto(12000).set(78, T, 12000, 900, "exp").v))
    return out + 0.5 * space.send(out, HUGE, hp=200)


def fx_layer(bed_raw):
    out = ses.stem()
    for b in (28, 56, 64):
        reverse_swell(ses, out, bed_raw, b, HUGE, beats=3, gain=0.8)
    return out


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    bass_raw = ses.assemble(np.load(f"{W}/ddd2_bass.npy", mmap_mode="r"), MAPPING)
    drums_raw = ses.assemble(np.load(f"{W}/ddd2_drums.npy", mmap_mode="r"), MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    gentle = engine.duck(ses, trig, ses.auto(0.0).set(28, 44, 2.5).set(64, 72, 2.5).smooth(30), release=0.18)
    m.add("bed", bed_layer(bed_raw) * gentle)
    m.add("bass", bass_layer(bass_raw) * engine.duck(ses, trig, 4.0, release=0.09))
    for k in list(st):
        m.add(k, st.pop(k))
    print("material and drums done")
    m.add("glass", glass(drums_raw) * gentle)
    m.add("pluck", strings())
    m.add("breath", breath() * gentle)
    m.add("choir", choir(bed_raw))
    m.add("coda", coda())
    m.add("tape", engine.lofi_texture(ses.N) * ses.auto(0.0).set(0, 10, 1.0).set(72, T, 1.0).smooth(200).v)
    f = fx_layer(bed_raw)
    m.add("fx", f, gain_db=-12.0 - dsp.db(np.abs(f).max() + 1e-9))
    print("stem gains dB:", m.gains)
    mix = m.mix
    s = ses.span(55.5, 56)  # your tape slowdown, into the wave
    mix[:, s] = fx.tape_stop(mix[:, s])
    fxs = np.load(f"{W}/{TAG}_stem_fx.npy")
    g = silence(ses, ses.N, [(27.75, 28)], fade_ms=8)
    mix = (mix - fxs) * g + fxs
    section = ses.auto(0.0).set(0, 8, -4.5).set(8, 24, -3.5).set(24, 28, -3.5, -2.0).set(28, 44, -1.5) \
        .set(44, 52, -5.0).set(52, 56, -4.5, -3.0).set(56, 64, -2.0).set(64, 72, 0.0).set(72, 76, -3.0) \
        .set(76, T, -5.0).smooth(80)
    m.mix = mix * dsp.undb(section.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
