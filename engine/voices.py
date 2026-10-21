"""Physical and additive voices that sound natural without samples: Karplus-Strong plucked strings with exact
tuning, modal resonator banks (glass, bells, struck metal), and an additive 'breathing' pad whose partials
drift independently. All recursion runs inside scipy's lfilter (C speed), everything else is vectorized.
"""
import numpy as np
from scipy import signal, ndimage
import dsp

SR = dsp.SR


def midi_hz(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=np.float64) - 69) / 12)


def smooth_noise(n, rate_hz, rng):
    """Random curve around 0 (unit-ish std) that wanders at about rate_hz."""
    k = max(4, int(n / SR * rate_hz) + 4)
    pts = rng.standard_normal(k)
    return np.interp(np.linspace(0, k - 3, n), np.arange(k), ndimage.gaussian_filter1d(pts, 1.0) * 1.6)


def ks_pluck(f, length, decay=2.5, bright=0.5, pick=0.12, seed=0):
    """Karplus-Strong string, tuned exactly with an allpass fractional delay inside the loop.
    decay = seconds to -60 dB at the fundamental; bright 0..1 shapes the pluck noise."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    N = SR / float(f)
    L = int(np.floor(N - 0.5))
    frac = N - L - 0.5
    c = (1 - frac) / (1 + frac)
    g = 10 ** (-3.0 / (decay * f))
    exc = rng.uniform(-1, 1, L)
    exc = dsp.sos_filter(exc, "lowpass", 1500 + 9000 * bright, SR, 2)
    exc -= exc.mean()
    x = np.zeros(n)
    x[:L] = exc * np.hanning(L) ** 0.3
    b = np.array([2.0, 2.0 * c])
    a = np.zeros(L + 3)
    a[0], a[1] = 2.0, 2.0 * c
    a[L] -= g * c
    a[L + 1] -= g * (1 + c)
    a[L + 2] -= g
    y = signal.lfilter(b, a, x)
    p = int(pick * L)  # pick position comb: removes harmonics like plucking off the bridge
    if p > 0:
        y = y - 0.6 * np.pad(y, (p, 0))[:n]
    y *= np.minimum(1, (n - np.arange(n)) / (0.05 * SR))
    return y / (np.abs(y).max() + 1e-12)


GLASS = ((1.0, 1.0, 1.0), (2.756, 0.32, 0.45), (5.404, 0.12, 0.22), (8.933, 0.05, 0.12))  # (ratio, amp, decay x)
BELL = ((0.5, 0.4, 1.3), (1.0, 1.0, 1.0), (1.183, 0.5, 0.8), (1.506, 0.35, 0.6), (2.0, 0.45, 0.5), (2.514, 0.2, 0.35),
        (2.662, 0.18, 0.3), (3.011, 0.12, 0.25), (4.166, 0.06, 0.18))
HARMONIC = ((1.0, 1.0, 1.0), (2.0, 0.4, 0.6), (3.0, 0.18, 0.4), (4.0, 0.08, 0.3))
TUNED = ((1.0, 1.0, 1.0), (2.0, 0.16, 0.6), (4.0, 0.3, 0.4), (8.0, 0.06, 0.2))  # tuned bars, celesta-like:
# overtones on octaves only, so the glass rings consonant with the chord


def resonate(excite, notes, decay=2.0, modes=GLASS, spread=0.6, seed=0):
    """Ring a bank of two-pole resonators tuned to `notes` (MIDI) with the given modal ratios.
    excite: mono or stereo signal (transients, noise bursts). Returns stereo, peak-normalized."""
    rng = np.random.default_rng(seed)
    x = np.asarray(excite, dtype=np.float64)
    x = x.mean(0) if x.ndim == 2 else x
    out = np.zeros((2, len(x)))
    for i, m in enumerate(notes):
        f0 = float(midi_hz(m))
        p = spread * np.sin(1.7 * i + rng.uniform(0, 0.5))
        for ratio, amp, dx in modes:
            f = f0 * ratio
            if f > 0.45 * SR:
                continue
            r = np.exp(-6.91 / (decay * dx * SR))
            w = 2 * np.pi * f / SR
            y = signal.lfilter([1 - r], [1, -2 * r * np.cos(w), r * r], x) * amp
            th = (p + 1) * np.pi / 4
            out[0] += y * np.cos(th)
            out[1] += y * np.sin(th)
    return out / (np.abs(out).max() + 1e-12)


def breath_pad(notes, length, attack=1.5, release=2.5, partials=12, bright=0.6, motion=0.35, seed=0):
    """Additive pad: each note's partials drift in level independently (slow random LFOs), pairs of detuned
    copies give width, a touch of stretch keeps it glassy. Stereo, peak-normalized."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for m in notes:
        f0 = float(midi_hz(m))
        for k in range(1, partials + 1):
            fk = f0 * k * (1 + 0.0004 * k * k)
            if fk > 16000:
                break
            amp = (1.0 / k ** (1.6 - 0.8 * bright)) * (1 + motion * smooth_noise(n, 0.15 + 0.05 * k, rng))
            amp = np.maximum(amp, 0)
            for c, det in ((0, -3.0), (1, 3.0)):
                ph = rng.uniform(0, 2 * np.pi)
                out[c] += amp * np.sin(2 * np.pi * fk * 2 ** (det / 1200) * t + ph)
    env = np.minimum(t / attack, 1) * np.clip((length - t) / release, 0, 1)
    out *= env
    return out / (np.abs(out).max() + 1e-12)


def fm_bell(f, length=2.5, ratio=3.5, index=2.2, decay=1.6):
    t = np.arange(int(length * SR)) / SR
    env = np.exp(-t / decay) * np.minimum(t / 0.002, 1)
    y = np.sin(2 * np.pi * f * t + index * np.exp(-t / (decay * 0.4)) * np.sin(2 * np.pi * f * ratio * t))
    return y * env
