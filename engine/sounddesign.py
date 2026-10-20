"""Sound-design toolkit for the style engines (numpy/scipy only).

Oscillators and voices: band-limited saws, detuned stacks with drift and pitch scoops, FM/ring-mod plucks,
FM bells, additive piano, CS-80-style brass, formant "vocal" chops, vocoder.
Textures: granular clouds, synthesized field recordings (rain, creek, birds, thunder), tape hiss, room tone.
Colour: 3-band distortion, tube, amp+cab, bitcrush, wavefold, Decapitator/Devil-Loc/exciter-style chains,
OTT-style upward+downward multiband compression, shimmer.
Parameter choices follow the Flume/ODESZA research notes; numbers are engineering defaults, not presets.
"""
import numpy as np
from scipy import signal, ndimage
import dsp
import fx

SR = dsp.SR


def midi_hz(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=np.float64) - 69) / 12)


def _t(n):
    return np.arange(n) / SR


def fade(y, a=0.002, r=0.01):
    n = y.shape[-1]
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    env = np.ones(n)
    if na:
        env[:na] = np.linspace(0, 1, na)
    if nr:
        env[-nr:] *= np.linspace(1, 0, nr)
    return y * env


def smooth_curve(c, ms=25.0):
    """Log-domain smoothing of a cutoff automation curve: turns jumps into short ramps so block-wise
    time-varying filters don't spike when the cutoff snaps (e.g. 2 kHz -> 20 Hz on a drop)."""
    return np.exp(ndimage.uniform_filter1d(np.log(np.maximum(c, 1.0)), max(1, int(ms * SR / 1000))))


def pan(x, p):
    th = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(th), x * np.sin(th)])


# ---------------------------------------------------------------- oscillators

def _polyblep(ph, dt):
    y = np.zeros_like(ph)
    m = ph < dt
    x = ph[m] / dt[m]
    y[m] = x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    y[m] = x * x + x + x + 1
    return y


def saw(freq, n, phase0=0.0):
    """Band-limited (PolyBLEP) saw; freq is a number or a per-sample array."""
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    dt = np.abs(f) / SR
    ph = (phase0 + np.cumsum(dt)) % 1.0
    return 2 * ph - 1 - _polyblep(ph, np.maximum(dt, 1e-9))


def detuned_stack(notes, n, voices=9, detune=25.0, drift=8.0, scoop=None, width=1.0, seed=0,
                  drift_rates=(0.13, 0.31)):
    """Stereo supersaw chord. Voices spread over +-detune cents, random phases, slow two-LFO drift
    (drift_rates Hz, +-drift cents), optional pitch scoop (cents, seconds) that glides back to pitch."""
    rng = np.random.default_rng(seed)
    t = _t(n)
    out = np.zeros((2, n))
    scoop_c = scoop[0] * np.exp(-t / scoop[1]) if scoop else 0.0
    for note in notes:
        f0 = midi_hz(note)
        lfo = np.sin(2 * np.pi * drift_rates[0] * t + rng.uniform(0, 6.28)) + \
            0.6 * np.sin(2 * np.pi * drift_rates[1] * t + rng.uniform(0, 6.28))
        for v in range(voices):
            u = 2 * v / (voices - 1) - 1 if voices > 1 else 0.0
            cents = detune * u + drift * lfo * rng.uniform(0.4, 1.0) + scoop_c
            y = saw(f0 * 2 ** (cents / 1200), n, rng.uniform())
            out += pan(y, u * width)
    return out / (len(notes) * np.sqrt(voices))


def fm_pluck(f, length=0.45, ratio=4.0, index=6.0, ring=2.7, ring_mix=0.25):
    """Metallic pluck: FM from an operator two octaves up, index 6 -> 0 over ~400 ms, plus ring mod."""
    n = int(length * SR)
    t = _t(n)
    idx = index * np.exp(-t / 0.09)
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * ratio * f * t))
    y *= (1 - ring_mix) + ring_mix * np.sin(2 * np.pi * ring * f * t)
    return fade(y * np.exp(-t / 0.12), 0.002, 0.015)


def fm_bell(f, length=1.6, ratio=3.5, index=3.0, decay=1.2):
    n = int(length * SR)
    t = _t(n)
    y = np.sin(2 * np.pi * f * t + index * np.exp(-t / 0.4) * np.sin(2 * np.pi * ratio * f * t))
    return fade(y * np.exp(-t / (decay / 3)), 0.001, 0.05)


def piano_note(m, length, vel=0.7, B=0.0004, seed=0):
    """Additive piano-ish tone: inharmonic partials f_n = n f sqrt(1 + B n^2), two detuned strings,
    faster decay for higher partials, hammer noise."""
    rng = np.random.default_rng(seed)
    f = float(midi_hz(m))
    n = int(length * SR)
    t = _t(n)
    y = np.zeros(n)
    for k in range(1, 14):
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > 16000:
            break
        amp = (1.0 / k ** 1.15) * vel ** (0.12 * k)
        tau = 3.2 / (1 + 0.45 * k) * (261.6 / f) ** 0.35
        for det in (-0.6, 0.6):
            y += 0.5 * amp * np.sin(2 * np.pi * fk * 2 ** (det / 1200) * t + rng.uniform(0, 6.28)) * \
                (0.75 * np.exp(-t / (tau * 0.25)) + 0.25 * np.exp(-t / tau))
    ham = dsp.sos_filter(rng.standard_normal(n), "bandpass", (300, 3500), SR, 2) * np.exp(-t / 0.004) * 0.04
    return fade((y + ham) * vel, 0.002, 0.08)


def brass(notes, length, attack=0.25, cut0=600.0, cut1=3000.0, after=1.0, vib_hz=5.0, vib_cents=15.0, seed=0):
    """CS-80-style brass: two saws per note +-7 cents (left/right), 2-pole low-pass opening with the
    attack, then 'aftertouch' (more brightness and vibrato) after `after` seconds, slow 0.2 Hz cutoff LFO."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = _t(n)
    vib = vib_cents * np.clip((t - after) / 1.5, 0, 1) * np.sin(2 * np.pi * vib_hz * t)
    out = np.zeros((2, n))
    for note in notes:
        f0 = midi_hz(note)
        for ch, det in ((0, 7.0), (1, -7.0)):
            out[ch] += saw(f0 * 2 ** ((det + vib) / 1200), n, rng.uniform())
    out /= max(1, len(notes))
    cutoff = cut0 + (cut1 - cut0) * (1 - np.exp(-t / attack)) + 1500 * np.clip((t - after) / 2.0, 0, 1) + \
        250 * np.sin(2 * np.pi * 0.2 * t + rng.uniform(0, 6.28))
    out = fx.tv_filter(out, "lowpass", cutoff, q=0.9, stages=1, block=64)
    env = (1 - np.exp(-t / (attack / 2.5))) * np.clip((length - t) / 0.6, 0, 1)
    return np.tanh(1.3 * out * env) / np.tanh(1.3)


def strings_pad(notes, length, attack=1.2, release=2.0, cutoff=2500.0, seed=0):
    y = detuned_stack(notes, int(length * SR), voices=6, detune=12.0, drift=4.0, seed=seed)
    y = dsp.sos_filter(y, "lowpass", cutoff, SR, 2)
    t = _t(y.shape[1])
    return y * np.minimum(t / attack, 1) * np.clip((length - t) / release, 0, 1)


# ---------------------------------------------------------------- vocal-like layers

VOWELS = {"ah": [(800, 1.0), (1150, 0.5), (2900, 0.25)], "oh": [(450, 1.0), (800, 0.4), (2830, 0.15)],
          "ee": [(270, 1.0), (2300, 0.45), (3000, 0.3)], "oo": [(325, 1.0), (700, 0.3), (2530, 0.1)],
          "eh": [(530, 1.0), (1840, 0.5), (2480, 0.3)]}


def vocal_chop(f, length, vowel="ah", shift=1.2, q=10.0, breath=0.08, vib=(5.5, 12.0), seed=0):
    """Formant 'vocal chop': glottal-ish saw through a vowel resonator bank (formants shifted by `shift`,
    the pitched-up 'another vocalist' trick), delayed vibrato, pitch jitter, breath transient."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = _t(n)
    cents = vib[1] * np.sin(2 * np.pi * vib[0] * t) * np.clip((t - 0.06) / 0.15, 0, 1)
    cents += np.cumsum(rng.normal(0, 0.15, n)) * 0.02
    src = saw(f * 2 ** (cents / 1200), n, rng.uniform())
    y = np.zeros(n)
    for fc, g in VOWELS[vowel]:
        b, a = signal.iirpeak(min(fc * shift, SR * 0.45), q, fs=SR)
        y += g * signal.lfilter(b, a, src)
    y = 0.7 * y / (np.abs(y).max() + 1e-9) + 0.3 * src * 0.3
    br = dsp.sos_filter(rng.standard_normal(n), "bandpass", (3000, 6000), SR, 2) * np.exp(-t / 0.012)
    y = y + breath * br / (np.abs(br).max() + 1e-9)
    return fade(y, 0.008, min(0.06, length / 3))


def vowel_noise(n, vowels, seg, seed=0):
    """Noise shaped by a sequence of vowels (one per `seg` samples), crossfaded: a vocoder modulator."""
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n)
    shaped = {}
    for v in set(vowels):
        y = np.zeros(n)
        for fc, g in VOWELS[v]:
            b, a = signal.iirpeak(fc, 6.0, fs=SR)
            y += g * signal.lfilter(b, a, noise)
        shaped[v] = y
    out = np.zeros(n)
    xf = int(0.03 * SR)
    for i in range(0, n, seg):
        v = vowels[(i // seg) % len(vowels)]
        a, b = max(0, i - xf), min(n, i + seg + xf)
        env = np.ones(b - a)
        env[:min(xf, len(env))] = np.linspace(0, 1, min(xf, len(env)))
        env[-min(xf, len(env)):] *= np.linspace(1, 0, min(xf, len(env)))
        out[a:b] += shaped[v][a:b] * env
    return out


def vocoder(carrier, modulator, bands=16, fmin=150.0, fmax=8000.0, smooth=0.012):
    """Filter-bank vocoder: each carrier band takes the RMS envelope of the same modulator band."""
    carrier = fx.as_stereo(carrier)
    mod = modulator.mean(0) if modulator.ndim == 2 else modulator
    edges = np.geomspace(fmin, fmax, bands + 1)
    out = np.zeros_like(carrier)
    for lo, hi in zip(edges[:-1], edges[1:]):
        sos = signal.butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
        env = np.sqrt(ndimage.uniform_filter1d(signal.sosfilt(sos, mod) ** 2, int(smooth * SR)) + 1e-12)
        out += signal.sosfilt(sos, carrier, axis=-1) * env
    return out


def paulstretch(x, stretch, window_s=0.3, seed=0):
    """Extreme time-stretch (Paul Nasca's method): windowed FFT frames, magnitudes kept, phases
    randomized, overlap-added at a slower hop. Turns seconds of audio into a smeared, glassy drone."""
    x = fx.as_stereo(np.asarray(x, dtype=np.float64))
    rng = np.random.default_rng(seed)
    nw = int(window_s * SR) // 2 * 2
    win = (1 - np.linspace(-1, 1, nw) ** 2) ** 1.25
    hop_out = nw // 4
    hop_in = hop_out / stretch
    n_frames = max(1, int((x.shape[1] - nw) / hop_in))
    out = np.zeros((2, n_frames * hop_out + nw))
    for i in range(n_frames):
        a = int(i * hop_in)
        frame = x[:, a:a + nw]
        if frame.shape[1] < nw:
            break
        spec = np.abs(np.fft.rfft(frame * win, axis=1))
        ph = rng.uniform(0, 2 * np.pi, spec.shape[1])
        ph = np.stack([ph, ph + rng.normal(0, 0.6, spec.shape[1])])  # slight L/R decorrelation for width
        out[:, i * hop_out:i * hop_out + nw] += np.fft.irfft(spec * np.exp(1j * ph), nw, axis=1) * win
    return out / (np.sum(win ** 2) / hop_out)


# ---------------------------------------------------------------- granular

def granular(src, n_out, regions, density=80.0, grain=(0.03, 0.12), pitches=(0, 12, -12),
             weights=(0.6, 0.3, 0.1), spread=0.8, seed=0, hp=150.0):
    """Grain cloud. regions: list of (out_start, out_end, src_start, src_end[, density]) samples; grains
    placed in [out_start, out_end) read from a slow random walk over src[src_start:src_end]."""
    rng = np.random.default_rng(seed)
    out = np.zeros((2, n_out))
    w = np.asarray(weights) / np.sum(weights)
    for reg in regions:
        o0, o1, s0, s1 = reg[:4]
        k = int((o1 - o0) / SR * (reg[4] if len(reg) > 4 else density))
        if k <= 0:
            continue
        times = np.sort(rng.uniform(o0, o1, k)).astype(int)
        walk = np.cumsum(rng.normal(0, 1, k))
        walk = (walk - walk.min()) / (np.ptp(walk) + 1e-9)
        for t0, u in zip(times, walk):
            L = int(rng.uniform(*grain) * SR)
            ratio = 2 ** (rng.choice(pitches, p=w) / 12)
            need = int(L * ratio) + 2
            sp = int(s0 + u * max(0, (s1 - s0) - need))
            g = np.asarray(src[:, sp:sp + need], dtype=np.float64).mean(0)
            if len(g) < need:
                continue
            g = np.interp(np.arange(L) * ratio, np.arange(need), g) * np.hanning(L)
            e = min(n_out, t0 + L)
            out[:, t0:e] += pan(g, rng.uniform(-spread, spread))[:, :e - t0]
    return dsp.sos_filter(out, "highpass", hp, SR, 2) if hp else out


# ---------------------------------------------------------------- synthesized field recordings

def pink(n, rng):
    X = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    k = np.arange(n // 2 + 1)
    X[1:] /= np.sqrt(k[1:])
    X[0] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-12)


def brown(n, rng):
    y = np.cumsum(rng.standard_normal(n))
    y = dsp.sos_filter(y, "highpass", 20, SR, 2)
    return y / (np.abs(y).max() + 1e-12)


def rain(n, density=70.0, seed=1):
    rng = np.random.default_rng(seed)
    bed = np.stack([dsp.sos_filter(pink(n, rng), "lowpass", 6000, SR, 2) for _ in range(2)]) * 0.35
    drops = np.zeros((2, n))
    for t0 in rng.integers(0, max(1, n - 2000), int(n / SR * density)):
        L = int(rng.uniform(0.002, 0.008) * SR)
        d = rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.1, 1) ** 2
        drops[:, t0:t0 + L] += pan(d, rng.uniform(-0.9, 0.9))
    drops = dsp.sos_filter(drops, "bandpass", (2000, 6000), SR, 2)
    return bed + 1.5 * drops / (np.abs(drops).max() + 1e-12)


def creek(n, seed=2):
    rng = np.random.default_rng(seed)
    out = []
    for c in range(2):
        b = brown(n, rng) + 0.3 * pink(n, rng)
        t = _t(n)
        center = 650 + 350 * np.sin(2 * np.pi * 0.23 * t + c) + 200 * np.sin(2 * np.pi * 0.71 * t + 2 * c)
        out.append(fx.tv_filter(b, "bandpass", center, q=1.2, stages=1, block=64)[0])
    out = np.stack(out)
    return out / (np.abs(out).max() + 1e-12)


def birds(n, rate=0.35, seed=3):
    """Sparse FM chirps (60-250 ms, 2.5 -> 4.5 kHz sweeps, 20-40 Hz vibrato), sometimes short trills."""
    rng = np.random.default_rng(seed)
    out = np.zeros((2, n))
    for t0 in rng.integers(0, max(1, n - SR), max(1, int(n / SR * rate))):
        p = rng.uniform(-0.8, 0.8)
        for k in range(rng.choice([1, 1, 2, 3, 5])):
            L = int(rng.uniform(0.06, 0.25) * SR)
            t = _t(L)
            f0, f1 = sorted(rng.uniform(2500, 4500, 2))[::rng.choice([1, -1])]
            f = f0 + (f1 - f0) * t / t[-1] + rng.uniform(80, 250) * np.sin(2 * np.pi * rng.uniform(20, 40) * t)
            y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) ** 2
            s = t0 + k * int(rng.uniform(0.09, 0.2) * SR)
            e = min(n, s + L)
            out[:, s:e] += pan(y, p)[:, :e - s] * rng.uniform(0.4, 1.0)
    return out


def thunder(length=4.0, seed=4):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = _t(n)
    env = np.minimum(t / 0.3, 1) * np.exp(-t / (length / 4))
    env *= 1 + 0.6 * np.abs(ndimage.uniform_filter1d(rng.standard_normal(n), int(0.15 * SR))) * 8
    y = np.stack([dsp.sos_filter(rng.standard_normal(n), "lowpass", 180, SR, 4) for _ in range(2)]) * env
    return y / (np.abs(y).max() + 1e-12)


def tape_hiss(n, seed=5):
    rng = np.random.default_rng(seed)
    return dsp.sos_filter(rng.standard_normal((2, n)), "lowpass", 7000, SR, 2) * 0.3


def room_tone(n, seed=6):
    rng = np.random.default_rng(seed)
    return np.stack([dsp.sos_filter(brown(n, rng), "bandpass", (100, 500), SR, 2) for _ in range(2)])


# ---------------------------------------------------------------- colour / distortion

def tri_distort(x, f1=200.0, f2=2500.0, drive=(2.0, 3.0, 2.0)):
    """3-band distortion (Tri-style): tanh on lows, hard clip on mids, wavefold on highs; level matched."""
    x = np.asarray(x, dtype=np.float64)
    pk = np.abs(x).max() + 1e-12
    x = x / pk
    lo = dsp.sos_filter(x, "lowpass", f1, SR, 4)
    hi = dsp.sos_filter(x, "highpass", f2, SR, 4)
    mid = x - lo - hi
    y = np.tanh(drive[0] * lo) / drive[0] * 1.5 + np.clip(drive[1] * mid, -0.6, 0.6) / drive[1] * 1.6 + \
        np.sin(drive[2] * hi * np.pi / 2) / drive[2]
    return y * pk


def tube(x, drive=2.0, bias=0.15):
    """Asymmetric (even-harmonic) saturation, HG-2-ish."""
    pk = np.abs(x).max() + 1e-12
    y = np.tanh(drive * x / pk + bias) - np.tanh(bias)
    y = dsp.sos_filter(y, "highpass", 20, SR, 2)
    return y / (np.abs(y).max() + 1e-12) * pk


def amp_sim(x, drive=4.0):
    """Guitar-amp colour: 800 Hz push, tanh drive, cab = 5.5 kHz low-pass with a 2 kHz bump."""
    pk = np.abs(x).max() + 1e-12
    y = fx.eq_peak(x / pk, 800, 6.0, q=0.8)
    y = np.tanh(drive * y)
    y = fx.eq_peak(dsp.sos_filter(y, "lowpass", 5500, SR, 2), 2000, 4.0, q=1.0)
    return y / (np.abs(y).max() + 1e-12) * pk


def bitcrush(x, bits=8, hold=4):
    q = 2 ** (bits - 1)
    y = np.round(np.asarray(x) * q) / q
    if hold > 1:
        idx = (np.arange(y.shape[-1]) // hold) * hold
        y = y[..., idx]
    return y


def wavefold(x, gain=2.0):
    pk = np.abs(x).max() + 1e-12
    return np.sin(gain * (x / pk) * np.pi / 2) * pk


def decapitator(x, drive_db=9.0, mix=0.4, tone_hz=9000.0):
    """Parallel vintage drive: +3 dB shelf at 3 kHz, asymmetric tanh, tone low-pass, blended."""
    x = np.asarray(x, dtype=np.float64)
    pk = np.abs(x).max() + 1e-12
    pre = fx.eq_shelf(x / pk, 3000, 3.0, "high")
    y = np.tanh(dsp.undb(drive_db) * pre + 0.1) - np.tanh(0.1)
    y = dsp.sos_filter(dsp.sos_filter(y, "lowpass", tone_hz, SR, 2), "highpass", 20, SR, 2)
    y = y / (np.abs(y).max() + 1e-12) * pk
    return (1 - mix) * x + mix * y


def devil_loc(x, release=0.1):
    """Level smasher: extreme fast compression then soft clip (for crushed, breathing reverb returns)."""
    y, _ = fx.compress(x, threshold_db=-32, ratio=20, attack=0.001, release=release, knee_db=3)
    y = fx.soft_clip(y / (np.abs(y).max() + 1e-12) * 1.2, 0.7)
    return y


def exciter(x, amount_db=-15.0, hp=5000.0):
    """Dopamine-style air: high-passed copy driven through tanh, mixed back under the dry signal."""
    h = dsp.sos_filter(x, "highpass", hp, SR, 2)
    pk = np.abs(h).max() + 1e-12
    return x + dsp.undb(amount_db) * np.tanh(4 * h / pk) * pk * 3


def ott(x, bands=(200.0, 2500.0), thr_db=-30.0, up_ratio=3.0, down_ratio=4.0, amount=0.7):
    """Upward + downward multiband compression: lifts quiet detail and noise, squashes peaks."""
    x = fx.as_stereo(np.asarray(x, dtype=np.float64))
    lo = dsp.sos_filter(x, "lowpass", bands[0], SR, 4)
    hi = dsp.sos_filter(x, "highpass", bands[1], SR, 4)
    out = np.zeros_like(x)
    for b in (lo, x - lo - hi, hi):
        env = np.sqrt(ndimage.uniform_filter1d(np.mean(b ** 2, 0), int(0.01 * SR)) + 1e-12)
        env = ndimage.uniform_filter1d(ndimage.maximum_filter1d(env, int(0.12 * SR)), int(0.01 * SR))
        over = dsp.db(env) - thr_db
        g = np.where(over > 0, -over * (1 - 1 / down_ratio), -over * (1 - 1 / up_ratio))
        out += b * dsp.undb(np.clip(g, -24, 15) * amount)
    return out


def shimmer(x, ir, iterations=2, feedback=0.7, hp=300.0):
    """Reverb -> octave up -> high-pass, fed back a couple of times."""
    wet = fx.reverb(x, ir)
    acc = np.zeros_like(wet)
    cur = wet
    for _ in range(iterations):
        up = fx.rubberband(cur, pitch=2.0)[:, :cur.shape[1]]
        if up.shape[1] < cur.shape[1]:
            up = np.pad(up, ((0, 0), (0, cur.shape[1] - up.shape[1])))
        up = dsp.sos_filter(up, "highpass", hp, SR, 2)
        acc += up
        cur = fx.reverb(up * feedback, ir)
    return wet * 0.5 + acc


def tape_delay(x, delay_s, feedback=0.4, lp=4000.0, taps=6, drive=1.5):
    """Saturating tape-echo throw (stereo, alternating sides)."""
    mono = x.mean(0) if x.ndim == 2 else x
    n = len(mono)
    d = int(round(delay_s * SR))
    out = np.zeros((2, n))
    sig = mono.astype(np.float64)
    for k in range(1, taps + 1):
        sig = np.tanh(drive * dsp.sos_filter_causal(sig, "lowpass", lp, SR, 1) * feedback) / np.tanh(drive)
        if k * d >= n:
            break
        out[(k - 1) % 2, k * d:] += sig[:n - k * d]
    return out


def marching_snare(tone=330.0, decay=0.14, seed=7):
    """Noise 1.5-8 kHz + tuned head + short comb 'buzz' of the snares."""
    rng = np.random.default_rng(seed)
    n = int(0.4 * SR)
    t = _t(n)
    noise = dsp.sos_filter(rng.standard_normal(n), "bandpass", (1500, 8000), SR, 2) * np.exp(-t / decay)
    d = int(0.005 * SR)
    buzz = noise.copy()
    for k in range(1, 6):
        buzz[k * d:] += noise[:-k * d] * 0.6 ** k
    head = np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.05)
    y = 0.8 * buzz / (np.abs(buzz).max() + 1e-12) + 0.5 * head
    return fade(np.tanh(1.6 * y) / np.tanh(1.6), 0.0005, 0.03)


def shaker(length=0.03, seed=8):
    rng = np.random.default_rng(seed)
    n = int(max(length, 0.015) * SR) * 3
    t = _t(n)
    env = np.minimum(t / (length * 0.4), 1) * np.exp(-np.maximum(t - length * 0.4, 0) / (length * 0.5))
    y = dsp.sos_filter(rng.standard_normal(n), "bandpass", (6000, 10000), SR, 2) * env
    return fade(y / (np.abs(y).max() + 1e-12))


def snap(seed=9):
    rng = np.random.default_rng(seed)
    n = int(0.08 * SR)
    t = _t(n)
    y = np.sin(2 * np.pi * 2000 * t) * np.exp(-t / 0.006) + \
        dsp.sos_filter(rng.standard_normal(n), "highpass", 2500, SR, 2) * np.exp(-t / 0.003) * 0.6
    return fade(y / np.abs(y).max())


def rim_click():
    n = int(0.06 * SR)
    t = _t(n)
    y = np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.008) + 0.7 * np.sin(2 * np.pi * 2900 * t) * np.exp(-t / 0.006)
    return fade(y / np.abs(y).max(), 0.0003, 0.01)


def wood(f=650.0):
    n = int(0.12 * SR)
    t = _t(n)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.02) + 0.4 * np.sin(2 * np.pi * f * 2.7 * t) * np.exp(-t / 0.01)
    return fade(y / np.abs(y).max())
