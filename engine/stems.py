"""Neural stems as remix material: loading, de-pumping, drum-kit extraction, beat-modulation measurement.

Stems come from engine/separate_mdx.py: work/<t>_{drums,bass,other,vocals,resid}.npy at 48 kHz.
"""
import numpy as np
from scipy import ndimage, signal
import dsp

SR = dsp.SR
NAMES = ("drums", "bass", "other", "vocals", "resid")


def load(prefix, names=NAMES):
    return {k: np.load(f"{prefix}_{k}.npy", mmap_mode="r") for k in names}


def envelope(x, ms=10.0):
    m = np.asarray(x, dtype=np.float64)
    m = m.mean(0) if m.ndim == 2 else m
    return np.sqrt(ndimage.uniform_filter1d(m ** 2, max(1, int(ms * SR / 1000))) + 1e-12)


def beat_modulation(x, beat_times, lo=None, hi=None):
    """Depth (dB) of the average beat-synchronous loudness dip, and its position (fraction of a beat)."""
    m = np.asarray(x, dtype=np.float64).mean(0)
    if lo and hi:
        m = dsp.sos_filter(m, "bandpass", (lo, hi), SR, 4)
    elif hi:
        m = dsp.sos_filter(m, "lowpass", hi, SR, 4)
    elif lo:
        m = dsp.sos_filter(m, "highpass", lo, SR, 4)
    e = envelope(m) ** 2
    n = int(np.median(np.diff(beat_times)) * SR)
    segs = [e[int(t * SR):int(t * SR) + n] for t in beat_times if int(t * SR) + n < len(e)]
    db = 10 * np.log10(np.mean(segs, 0) + 1e-12)
    return float(db.max() - db.min()), float(np.argmin(db) / n)


def depump(x, beat_times, window_beats=16, phases=96, max_boost_db=8.0):
    """Undo quarter-note sidechain ducking baked into a stem: measure the average loudness shape across the
    beat (over a sliding window of beats), and divide it out. Keeps slow dynamics, removes the pump."""
    x = np.asarray(x, dtype=np.float64)
    env = envelope(x, 8.0)
    bt = np.asarray(beat_times)
    nb = len(bt) - 1
    shape = np.ones((nb, phases))
    for k in range(nb):
        idx = (bt[k] + (bt[k + 1] - bt[k]) * np.arange(phases) / phases) * SR
        v = env[np.clip(idx.astype(int), 0, len(env) - 1)]
        shape[k] = v / (v.mean() + 1e-9)
    gain = np.ones(len(env))
    half = window_beats // 2
    lim = dsp.undb(max_boost_db)
    for k in range(nb):
        a, b = max(0, k - half), min(nb, k + half)
        tmpl = np.median(shape[a:b], axis=0)
        tmpl = ndimage.uniform_filter1d(tmpl, 5, mode="wrap")
        g = np.clip(1.0 / np.maximum(tmpl, 1e-3), 1 / lim, lim)
        s0, s1 = int(bt[k] * SR), int(bt[k + 1] * SR)
        gain[s0:s1] = np.interp(np.arange(s1 - s0), np.linspace(0, s1 - s0, phases, endpoint=False), g)
    gain = ndimage.uniform_filter1d(gain, int(0.004 * SR))
    return x * gain


def _onset(d_mono, t, search=0.03):
    """Precise onset near time t: the steepest rise of a 1 ms envelope within +-search seconds."""
    a, b = int((t - search) * SR), int((t + search) * SR)
    seg = d_mono[max(0, a):b]
    e = np.sqrt(ndimage.uniform_filter1d(seg ** 2, int(0.001 * SR)) + 1e-12)
    rise = np.diff(ndimage.uniform_filter1d(e, int(0.002 * SR)))
    return max(0, a) + int(np.argmax(rise))


def extract_hit(drums, times, pre=0.005, post=0.45, keep=0.5):
    """Recover a clean one-shot from a separated drum stem (the same sample retriggered in a DAW): align every
    instance on its onset, take the per-sample median, keep the instances that best match it, and take the
    median again. Bleed from other instruments, which differs between instances, averages away.
    Returns (stereo hit, mean correlation of the kept instances with the result, number kept)."""
    d = np.asarray(drums, dtype=np.float64)
    mono = d.mean(0)
    n0, n1 = int(pre * SR), int(post * SR)
    segs = []
    for t in times:
        o = _onset(mono, t)
        if o - n0 >= 0 and o + n1 <= d.shape[1]:
            segs.append(d[:, o - n0:o + n1])
    segs = np.array(segs)
    hit = np.median(segs, axis=0)
    corr = np.array([np.corrcoef(hit.mean(0), s.mean(0))[0, 1] for s in segs])
    best = segs[np.argsort(corr)[::-1][:max(3, int(len(segs) * keep))]]
    hit = np.median(best, axis=0)
    c = float(np.mean([np.corrcoef(hit.mean(0), s.mean(0))[0, 1] for s in best]))
    fade = np.ones(n0 + n1)
    fade[-int(0.02 * SR):] = np.linspace(1, 0, int(0.02 * SR))
    return hit * fade, c, len(best)
