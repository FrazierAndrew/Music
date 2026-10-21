"""ddd2, "Aurora". Engine: SPECTRAL. Your chords, frozen and re-lit in the frequency domain, over a steady
four-on-the-floor at 122 BPM (your stems time-stretched with pitch kept).

- aurora: the long-term spectrum of each of your chords (median over every bar that plays it, taken from your
  de-pumped pad stem), resynthesized with fresh random phases every frame: an endlessly sustained, pure
  version of your pad's own colour, gliding into each chord change and slowly brightening and darkening;
- halo: the same spectra an octave and two octaves up (octaves only, so it never adds a note you don't play);
- pulse: the aurora split into six bands, each gated with its own rhythm (dotted eighths, sixteenths,
  off-beats, triplets), so the pad itself becomes a polyrhythmic shimmer in the peaks;
- cascade: a bell-and-string motif grown from your pad's top line (D#6 to C#6), sent through a per-bin
  spectral delay where high partials echo later than low ones, so every note dissolves upward;
- freeze: one bar where time stops: the instant before the wave is held as a frozen spectrum, then the wave;
- your bass stem carries the low end (gated into eighths in the first peak, smooth under the wave), and the
  kick and clap are your own, recovered from your drum stem.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_aurora.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
import sounddesign as sd
import space
import spectral as spc
import voices as V
from engine import Session, Mixer, reverse_swell
from ddd2_harmony import chord_of_source_bar, blocks, silence

SR = dsp.SR
W = engine.WORK
TAG = "ddd2_aurora"
SECTIONS = [
    ("aurora", 0, 16, 0),
    ("pulse", 16, 16, 20),
    ("peak", 32, 16, 76),
    ("fall", 48, 8, 68),
    ("inhale", 56, 4, 92),
    ("wave", 60, 8, 100),
    ("wave2", 68, 8, 100),
    ("afterglow", 76, 4, 108),
    ("frozen", 80, 6, None),
]
END = 86
T = END + 2
ses = Session("ddd2_stems", "tracks/ddd2/analysis.json", f"{W}/ddd2_bed_dp.npy", None, T, stretch=122 / 136.0045,
              seed=52)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS if s0 is not None for i in range(nb)]
SRC_OF = dict(MAPPING)
CHORD = {R: chord_of_source_bar(S) for R, S in MAPPING}
CHORD.update({R: "B" for R in range(80, T)})
AURORA_CHORD = dict(CHORD)
AURORA_CHORD.update({R: "Bi" for R in range(0, 16)})  # the intro pad has its own (wider, softer) colour


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


N_FFT, HOP = 16384, 4096
GATED = bars((32, 48), (60, 76))
MOTIF = {  # (eighth step in a 2-bar phrase, MIDI, length in eighths): from your top line, the D#6 -> C#6 sigh
    "E": [(0, 78, 1), (1, 82, 1), (2, 85, 1), (3, 87, 3), (6, 85, 2), (8, 83, 4), (12, 82, 2), (14, 78, 2)],
    "B": [(0, 75, 1), (1, 78, 1), (2, 82, 1), (3, 85, 3), (6, 83, 2), (8, 82, 4), (12, 78, 2), (14, 75, 2)],
    "D#m": [(0, 82, 4), (4, 78, 4), (8, 75, 8)],
}
MOTIF_BARS = bars((32, 48), (48, 56), (64, 68), (68, 76))
KICK_BARS = bars((16, 48), (60, 76), (76, 78))
CLAP_BARS = bars((24, 47), (60, 76))
HAT_BARS = bars((20, 47), (62, 76))
RIDE_BARS = bars((68, 76))
MUTE = {(47, 3), (59, 0), (59, 1), (59, 2), (59, 3)}
CHORD_STEMS, HARMONY_REF = ["aurora", "halo", "cascade"], ["bed"]
CHORD_BARS = bars((16, 48), (60, 76))

HALL = space.hall_ir(rt60=3.2, predelay=0.02, dark=0.5, bloom=0.15, seed=21)
VAST = space.hall_ir(rt60=9.0, predelay=0.05, dark=0.75, bloom=1.2, seed=22)
ROOM = space.hall_ir(rt60=0.6, predelay=0.003, dark=0.3, early=1.0, seed=23)

TARGETS = {"bed": (-18.5, (32, 48)), "aurora": (-19.0, (32, 48)), "halo": (-26.0, (68, 76)),
           "bass": (-20.5, (32, 48)), "kick": (-16.5, (32, 48)), "clap": (-21.5, (32, 48)),
           "hats": (-26.5, (32, 48)), "ride": (-27.5, (68, 76)), "cascade": (-21.5, (32, 48)),
           "freeze": (-17.0, (59, 60))}
MASTER_REGION = (68, 76)
MASTER_TARGET = -10.5
MASTER_CEILING = -1.9


def hp(x, f, order=2):
    return dsp.sos_filter(np.asarray(x, dtype=np.float64), "highpass", f, SR, order)


def lp(x, f, order=2):
    return dsp.sos_filter(np.asarray(x, dtype=np.float64), "lowpass", f, SR, order)


# ---------------------------------------------------------------- spectra of your chords

def chord_spectra():
    bed0 = np.load(f"{W}/ddd2_bed_dp.npy", mmap_mode="r")  # original speed: spectra don't depend on tempo
    bt = np.array(ses.an["beats"])[ses.an["downbeat_phase"]::4]
    rng = lambda starts, n=4: [(bt[S], bt[S + n]) for S in starts]
    return {"E": spc.chord_spectrum(bed0, rng((20, 28, 36, 76, 84, 100)), N_FFT),
            "B": spc.chord_spectrum(bed0, rng((24, 32, 40, 80, 88, 104)), N_FFT),
            "D#m": spc.chord_spectrum(bed0, rng((68,)), N_FFT),
            "Bi": spc.chord_spectrum(bed0, rng((0,), 12), N_FFT)}


def frame_chords():
    n_frames = ses.N // HOP + 8
    bar_len = 4 * ses.spb
    return [AURORA_CHORD[min(T - 1, int(i * HOP / bar_len))] for i in range(n_frames)]


def tilt_curve(n_frames):
    """Brightness in dB/octave per frame, written per bar."""
    a = ses.auto(0.0).set(0, 16, -2.5, -0.5).set(32, 48, 1.0).set(48, 56, -1.5).set(56, 59, -1.5, 3.0) \
        .set(59, 60, 3.0).set(60, 68, 1.0).set(68, 76, 2.0).set(76, 80, 0.0).set(80, T, 0.0, -3.0)
    return a.v[np.minimum(np.arange(n_frames) * HOP, ses.N - 1)]


def aurora_layers(spectra):
    names = frame_chords()
    mags = spc.morph_frames(names, spectra, morph_frames_n=int(ses.spb / HOP) + 1)
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    slope = tilt_curve(len(mags))
    g = (np.maximum(f, 20.0)[None, :] / 1000.0) ** (slope[:, None] / 6.02)
    mags = mags * g[:, None, :].astype(np.float32)
    pad = spc.freeze(mags, ses.N, N_FFT, HOP, seed=5)
    halo_m = 0.65 * spc.shift(mags, 2.0) + 0.3 * spc.shift(mags, 4.0)
    halo = hp(spc.freeze(halo_m.astype(np.float32), ses.N, N_FFT, HOP, seed=6), 1400)
    del mags, halo_m
    return hp(pad, 90), halo


# ---------------------------------------------------------------- rhythm

BANDS = [(90, 350), (350, 800), (800, 1800), (1800, 4000), (4000, 8000), (8000, 16000)]


def band_envelopes():
    n = ses.N
    on = ses.auto(0.0)
    for a, b in ((32, 48), (60, 76)):
        on.set(a, b, 1.0)
    on.set(31, 32, 0.0, 1.0).set(59, 60, 0.0, 1.0)
    on.smooth(40)

    def hits(steps, per_bar=16):
        return [ses.pos(R, s * 4 / per_bar) for R in sorted(GATED | bars((31, 32), (59, 60))) for s in steps]
    kick = [ses.pos(R, b) for R in range(T) for b in range(4)]
    pump = 1 - 0.45 * np.exp(-np.maximum(0, (np.arange(n) - np.repeat(kick, 1)[np.searchsorted(kick, np.arange(n), side="right") - 1]) / SR) / 0.11)
    envs = [pump,
            spc.gate_env(n, hits([0, 3, 6, 9, 12, 15]), 0.16, floor=0.25),
            spc.gate_env(n, hits([0, 2, 3, 5, 7, 8, 10, 11, 13, 15]), 0.07, floor=0.2),
            spc.gate_env(n, hits([2, 6, 10, 14]), 0.12, floor=0.2),
            spc.gate_env(n, hits(range(12), per_bar=12), 0.08, floor=0.25),
            None]
    return [None if e is None else (1 - on.v) + on.v * e for e in envs]


def pulse(pad):
    return spc.band_gate(pad, BANDS, band_envelopes())


def kit():
    kick = hp(np.load(f"{W}/ddd2_kit_kick_2.npy"), 28, 2)
    snare = hp(np.load(f"{W}/ddd2_kit_snare_3.npy"), 160, 2)
    clap = synth.clap(decay=0.2)
    layer = np.zeros((2, max(snare.shape[1], len(clap))))
    layer[:, :snare.shape[1]] += 0.8 * snare / (np.abs(snare).max() + 1e-9)
    layer[:, :len(clap)] += 0.7 * clap
    layer = layer + 0.4 * space.convolve(layer, ROOM)[:, :layer.shape[1]]
    return kick, layer


def hat(decay, seed, band=(7000, 15500)):
    rng = np.random.default_rng(seed)
    n = int(decay * 6 * SR)
    t = np.arange(n) / SR
    return dsp.sos_filter(rng.standard_normal(n), "bandpass", band, SR, 2) * np.exp(-t / decay) * np.minimum(t / 0.0008, 1)


def drums():
    kick, clap = kit()
    st = {k: ses.stem() for k in ("kick", "clap", "hats", "ride")}
    trig = ses.hits(st["kick"], kick, KICK_BARS, [0, 4, 8, 12], mute=MUTE, jitter_ms=0.8)
    ses.hits(st["clap"], clap, CLAP_BARS, [4, 12], mute=MUTE, late_ms=4, jitter_ms=2)
    closed, opened = hat(0.02, 31), hat(0.09, 32, (6500, 14000))
    for R in sorted(HAT_BARS):
        ses.hits(st["hats"], opened, {R}, [2, 6, 10, 14], gain=0.75, pan=-0.15, mute=MUTE, jitter_ms=2)
        ses.hits(st["hats"], closed, {R}, [1, 3, 5, 7, 9, 11, 13, 15], vel=[0.4, 0.65, 0.45, 0.75], pan=0.25,
                 swing=0.06, rand=0.15, mute=MUTE, jitter_ms=3)
    ride = synth.ride(decay=1.1)
    ses.hits(st["ride"], ride, RIDE_BARS, [0, 2, 4, 6, 8, 10, 12, 14], vel=[0.9, 0.55], pan=0.3, mute=MUTE)
    st["clap"] = st["clap"] + 0.2 * space.send(st["clap"], HALL, hp=300)
    st["hats"] = st["hats"] + 0.08 * space.send(st["hats"], HALL, hp=2500)
    st["ride"] = st["ride"] + 0.15 * space.send(st["ride"], HALL, hp=2500)
    return st, trig


# ---------------------------------------------------------------- your material, re-lit

def bed_layer(bed_raw):
    x = hp(bed_raw, 110)
    bloom = ses.auto(16000).set(0, 16, 500, 9000, "exp").set(48, 56, 2800).set(56, 59, 2800, 14000, "exp") \
        .set(76, T, 7000, 1200, "exp")
    x = fx.tv_filter(x, "lowpass", sd.smooth_curve(bloom.v))
    x = x * ses.auto(1.0).set(0, 4, 0.0, 1.0, 1.5).set(59, 60, 0.0).set(80, T, 1.0, 0.0).smooth(60).v
    return x + 0.4 * space.send(x, HALL)


def bass_layer(bass_raw, trig):
    x = np.asarray(bass_raw, dtype=np.float64)
    gain = ses.auto(0.0).set(16, 20, 0.0, 1.0).set(20, 59, 1.0).set(59, 60, 0.0).set(60, 76, 1.0) \
        .set(76, 80, 1.0, 0.0).smooth(40)
    eighths = [ses.pos(R, s / 2) for R in sorted(bars((32, 48))) for s in range(8)]
    roll = spc.gate_env(ses.N, eighths, 0.16, floor=0.45)
    roll = np.where(np.isin(np.arange(ses.N) // int(4 * ses.spb), list(bars((32, 48)))), roll, 1.0)
    return x * gain.v * roll * engine.duck(ses, trig, 4.0, release=0.1)


def cascade():
    dry = ses.stem()
    for R0, nb, c in blocks(CHORD, MOTIF_BARS):
        for b0 in range(R0, R0 + nb, 2):
            for st, m, ln in MOTIF[c]:
                R = b0 + st // 8
                if R not in MOTIF_BARS or (R, int((st % 8) / 2)) in MUTE:
                    continue
                if R in bars((48, 56)) and st % 4:
                    continue  # the fall: only the strong beats
                if R in bars((64, 68)) and st >= 8:
                    continue  # first wave: half the phrase, room for the wave
                up = 12 if R in bars((68, 76)) else 0
                length = ln * ses.spb / 2 / SR
                p = ses.pos(R, (st % 8) / 2)
                bell = V.fm_bell(V.midi_hz(m + up), length=length + 1.5, ratio=2.0, index=1.4, decay=1.1)
                string = V.ks_pluck(V.midi_hz(m + up), length + 1.5, decay=1.3, bright=0.7, seed=R * 16 + st)
                k = min(len(bell), len(string))
                bell, string = bell[:k], string[:k]
                ses.add(dry, 0.75 * bell + 0.45 * string, p, 0.8, pan=0.25 * np.sin(1.3 * st))
    dry = hp(dry, 250)
    trail = spc.spectral_delay(dry, 0.75 * ses.spb / SR, feedback=0.6)
    out = dry + 0.9 * trail
    return out + 0.45 * space.send(out, VAST, hp=500)


def freeze_moment(source):
    """Hold the spectrum of the first instant of bar 59 for one bar, high-pass rising, then cut at the wave."""
    a = ses.pos(59)
    seg = np.asarray(source[:, a:a + N_FFT], dtype=np.float64)
    M = np.abs(np.fft.rfft(seg * np.hanning(N_FFT), axis=1))
    n = ses.pos(60) - a
    frames = n // HOP + 4
    held = spc.freeze(np.repeat(M[None].astype(np.float32), frames, axis=0), n, N_FFT, HOP, seed=9)
    held = fx.tv_filter(held, "highpass", sd.smooth_curve(np.geomspace(150, 2500, n)))
    held *= np.minimum(np.arange(n) / (0.02 * SR), 1) * np.linspace(0.8, 1.2, n)
    out = ses.stem()
    out[:, a:a + n] = held
    return out + 0.6 * space.send(out, VAST, hp=300)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    bass_raw = ses.assemble(ses._layer(f"{W}/ddd2_bass.npy", "bass"), MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    for k in list(st):
        m.add(k, st.pop(k))
    bed = bed_layer(bed_raw)
    m.add("bed", bed)
    m.add("bass", bass_layer(bass_raw, trig))
    print("drums, bed, bass done")
    pad, halo = aurora_layers(chord_spectra())
    pad = pad * ses.auto(1.0).set(0, 6, 0.0, 1.0, 1.6).set(59, 60, 0.0).set(80, T, 1.0, 0.0, 1.2).smooth(80).v
    aur = pulse(pad)
    aur = aur + 0.35 * space.ensemble(aur, seed=3)
    m.add("aurora", aur + 0.5 * space.send(aur, VAST, hp=300))
    halo = halo * ses.auto(0.0).set(8, 16, 0.0, 0.7).set(16, 32, 0.5).set(32, 48, 0.8).set(48, 56, 1.0) \
        .set(56, 59, 1.0, 1.4).set(60, 68, 0.7).set(68, 76, 1.2).set(76, 86, 1.0, 0.0).smooth(80).v
    m.add("halo", halo + 0.6 * space.send(halo, VAST, hp=1500))
    print("aurora done")
    m.add("cascade", cascade())
    m.add("freeze", freeze_moment(bed + aur))
    f = ses.stem()
    for b in (32, 60):
        reverse_swell(ses, f, bed_raw, b, VAST, beats=4, gain=0.8)
    m.add("fx", f, gain_db=-11.0 - dsp.db(np.abs(f).max() + 1e-9))
    print("stem gains dB:", m.gains)
    mix = m.mix
    keep = np.load(f"{W}/{TAG}_stem_freeze.npy") + np.load(f"{W}/{TAG}_stem_fx.npy")
    g = silence(ses, ses.N, [(59, 60), (47.75, 48)], fade_ms=10)
    mix = (mix - keep) * g + keep
    section = ses.auto(0.0).set(0, 16, -11.0, -7.0).set(16, 32, -6.0, -4.5).set(32, 48, -1.8).set(48, 56, -8.0) \
        .set(56, 59, -7.0, -3.0).set(59, 60, -3.0).set(60, 68, -2.5).set(68, 76, 0.0).set(76, 80, -5.0) \
        .set(80, T, -8.0, -16.0).smooth(80)
    m.mix = mix * dsp.undb(section.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
