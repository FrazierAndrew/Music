"""Space: better reverbs (designed impulse responses with early reflections, per-band decay and bloom),
ensemble chorus, and stereo helpers. Convolution is FFT-based (scipy oaconvolve), so long tails are cheap.
"""
import numpy as np
from scipy import signal
import dsp

SR = dsp.SR
BANDS = [(20, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 20000)]


def hall_ir(rt60=3.0, predelay=0.02, dark=0.5, bloom=0.0, width=1.0, early=0.5, seed=0):
    """Stereo IR: early reflections + a late tail whose decay time falls with frequency (`dark` 0..1),
    an echo-density build-up, and an optional slow `bloom` (seconds) so the tail swells after the dry sound."""
    rng = np.random.default_rng(seed)
    n = int((rt60 * 1.25 + bloom) * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal((2, n))
    if width < 1.0:
        m = noise.mean(0)
        noise = m + width * (noise - m)
    tail = np.zeros((2, n))
    for lo, hi in BANDS:
        fc = np.sqrt(lo * hi)
        rt = rt60 * np.clip((1000.0 / fc) ** (0.45 * dark), 0.3, 1.25)
        tail += dsp.sos_filter(noise, "bandpass", (lo, min(hi, 0.45 * SR)), SR, 2) * np.exp(-6.91 * t / rt)
    build = 1 - np.exp(-t / (0.012 + bloom / 3.0))  # density build-up, or a slow swell when bloom > 0
    tail *= build
    er = np.zeros((2, n))
    taps = np.sort(rng.uniform(0.006, 0.08, 18))
    for i, d in enumerate(taps):
        k = int(d * SR)
        er[i % 2, k] += rng.choice([-1, 1]) * (1 - d / 0.09) * 0.9
        er[(i + 1) % 2, min(n - 1, k + int(rng.uniform(0.0003, 0.002) * SR))] += rng.choice([-1, 1]) * 0.4 * (1 - d / 0.09)
    er = dsp.sos_filter(er, "lowpass", 7000, SR, 2)
    tail /= np.sqrt(np.sum(tail ** 2, axis=1, keepdims=True)) + 1e-12
    er /= np.sqrt(np.sum(er ** 2, axis=1, keepdims=True)) + 1e-12
    ir = tail + early * er
    ir = dsp.sos_filter(ir, "highpass", 90, SR, 2)
    ir = np.pad(ir, ((0, 0), (int(predelay * SR), 0)))
    return ir / (np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True)) + 1e-12)


def convolve(x, ir):
    """Wet-only convolution, mono or stereo in, stereo out, same length as x."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x])
    return np.stack([signal.oaconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])


def send(x, ir, hp=250.0, lp=9000.0):
    """A reverb send: band-limit what goes in (no mud, no fizz), then convolve."""
    x = np.asarray(x, dtype=np.float64)
    return convolve(dsp.sos_filter(dsp.sos_filter(x, "highpass", hp, SR, 2), "lowpass", lp, SR, 2), ir)


def ensemble(x, voices=4, depth_ms=2.5, base_ms=9.0, rate_hz=0.25, seed=0):
    """Slowly modulated delay copies spread left and right (chorus / string-machine ensemble). Wet only."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x])
    rng = np.random.default_rng(seed)
    n = x.shape[1]
    t = np.arange(n) / SR
    idx = np.arange(n, dtype=np.float64)
    out = np.zeros_like(x)
    for v in range(voices):
        r = rate_hz * rng.uniform(0.7, 1.4)
        d = (base_ms + depth_ms * np.sin(2 * np.pi * r * t + rng.uniform(0, 6.28))) * SR / 1000
        c = v % 2
        out[c] += np.interp(idx - d, idx, x[c], left=0.0)
    return out * (2.0 / voices)


def width(x, amount=1.3):
    x = np.asarray(x, dtype=np.float64)
    m, s = (x[0] + x[1]) / 2, (x[0] - x[1]) / 2
    return np.stack([m + amount * s, m - amount * s])


def haas(x, ms=12.0, side=1):
    """Mono source to stereo with a short inter-channel delay (wide without phasey modulation)."""
    x = np.asarray(x, dtype=np.float64)
    m = x.mean(0) if x.ndim == 2 else x
    k = int(ms * SR / 1000)
    late = np.pad(m, (k, 0))[:len(m)]
    return np.stack([m, late]) if side > 0 else np.stack([late, m])
