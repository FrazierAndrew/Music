"""Beat tracking that follows tempo drift (generated tracks drift tens of ms).

1. Dynamic-programming beat tracker (Ellis 2007) on a 100 fps onset envelope.
2. Each beat refined to the kick attack (steepest rise of the 30-150 Hz envelope).
3. Smoothed with a local robust linear fit, so beat times follow drift without jitter.
"""
import numpy as np
from scipy import signal, ndimage
import dsp

AN_SR, N_FFT, HOP = 24000, 2048, 240
FPS = AN_SR / HOP


def onset_env(x):
    mono = signal.resample_poly(x.mean(0), 1, 2).astype(np.float32)
    S = dsp.stft_mag(mono, N_FFT, HOP)
    fb, mel_hz = dsp.mel_filterbank(AN_SR, N_FFT, 128, 30, 11000)
    M = fb @ (S ** 2)
    low = dsp.onset_envelope(M, slice(0, int(np.searchsorted(mel_hz, 150))))
    env = dsp.onset_envelope(M) + low
    return env / (env.std() + 1e-9)


def dp_beats(env, bpm, tightness=100.0):
    period = 60 * FPS / bpm
    n = len(env)
    score = env.astype(np.float64).copy()
    back = -np.ones(n, dtype=int)
    lo, hi = int(round(period / 2)), int(round(2 * period))
    d = np.arange(lo, hi + 1)
    pen = -tightness * np.log(d / period) ** 2
    for t in range(hi, n):
        cand = score[t - d] + pen
        k = np.argmax(cand)
        score[t] = env[t] + cand[k]
        back[t] = t - d[k]
    t = n - int(period) + int(np.argmax(score[n - int(period):]))
    out = []
    while t >= 0:
        out.append(t)
        t = back[t]
    return np.array(out[::-1]) / FPS


def refine_to_attack(x, beats, sr=dsp.SR, win=0.025):
    lo = dsp.sos_filter(x.mean(0), "bandpass", (30, 150), sr, order=2)
    env = ndimage.uniform_filter1d(np.abs(lo), int(0.002 * sr))
    deriv = np.diff(env, prepend=env[0])
    deriv = ndimage.uniform_filter1d(deriv, int(0.001 * sr))
    out = []
    for t in beats:
        a, b = int((t - win) * sr), int((t + win) * sr)
        if a < 0 or b >= len(deriv):
            out.append(t)
            continue
        out.append((a + np.argmax(deriv[a:b])) / sr)
    return np.array(out)


def smooth_beats(raw, half=12, tol=0.006):
    """Local robust linear fit of beat time vs index."""
    n = len(raw)
    idx = np.arange(n)
    fit = np.empty(n)
    for i in range(n):
        a, b = max(0, i - half), min(n, i + half + 1)
        xi, yi = idx[a:b], raw[a:b]
        keep = np.ones(len(xi), bool)
        for _ in range(3):
            p = np.polyfit(xi[keep], yi[keep], 1)
            res = yi - np.polyval(p, xi)
            keep = np.abs(res) < max(tol, 2.5 * np.median(np.abs(res[keep])))
        fit[i] = np.polyval(p, i)
    return fit


def hf_envelope(x, sr=dsp.SR, rate=4000):
    """Envelope of the >2 kHz band (kick click / transients) at `rate` Hz."""
    hi = dsp.sos_filter(x.mean(0), "highpass", 2000, sr, order=4)
    env = ndimage.uniform_filter1d(np.abs(hi), int(0.0005 * sr))
    return env[::sr // rate], rate


def attack_time(avg, rate, pre):
    """Onset of an averaged transient: steepest rise of the smoothed envelope."""
    d = np.diff(ndimage.uniform_filter1d(avg, max(1, int(0.001 * rate))))
    return np.argmax(d) / rate - pre


def refine_by_local_average(x, beats, n_avg=33, iters=3, pre=0.03):
    """Shift beats so the averaged transient over neighbouring beats starts exactly on the beat.

    Averaging over ~33 beats cancels hats/bass events and leaves the kick click,
    giving a smooth, sub-millisecond drift correction.
    """
    env, rate = hf_envelope(x)
    w = int(2 * pre * rate)
    b = beats.copy()
    for _ in range(iters):
        segs = np.zeros((len(b), w))
        for i, t in enumerate(b):
            a = int(round((t - pre) * rate))
            if 0 <= a and a + w <= len(env):
                segs[i] = env[a:a + w]
        avg = ndimage.uniform_filter1d(segs, n_avg, axis=0, mode="nearest")
        corr = np.array([attack_time(avg[i], rate, pre) for i in range(len(b))])
        corr = ndimage.uniform_filter1d(ndimage.median_filter(corr, 9), 9)
        b = b + corr
    return b


def beat_strength(env, beats):
    """Onset strength at each beat relative to the track median (kick presence)."""
    idx = np.clip(np.round(beats * FPS).astype(int), 0, len(env) - 1)
    peak = np.array([env[max(0, i - 2):i + 3].max() for i in idx])
    return ndimage.median_filter(peak / np.median(env), 9)


def reliable_span(beats, max_dev=0.005, run=64):
    """First/last beat of the span where inter-beat intervals stay within max_dev of the local median."""
    ibi = np.diff(beats)
    bad = np.abs(ibi - ndimage.median_filter(ibi, 31)) > max_dev
    bad = np.r_[bad, False]
    ok_run = np.array([not bad[i:i + run].any() for i in range(len(beats))])
    first = int(np.argmax(ok_run))
    ok_back = np.array([not bad[max(0, j - run):j + 1].any() for j in range(len(beats))])
    last = int(len(beats) - 1 - np.argmax(ok_back[::-1]))
    return first, last


def extrapolate_edges(beats, first, last, n_fit=32):
    """Replace beats outside [first, last] with a linear continuation of the edge tempo."""
    out = beats.copy()
    i = np.arange(len(beats))
    p = np.polyfit(i[first:first + n_fit], beats[first:first + n_fit], 1)
    out[:first] = np.polyval(p, i[:first])
    p = np.polyfit(i[last - n_fit + 1:last + 1], beats[last - n_fit + 1:last + 1], 1)
    out[last + 1:] = np.polyval(p, i[last + 1:])
    return out, first, last


def _kick_segments(x, beats, first, last, sr=dsp.SR, pre=0.03, post=0.1):
    lo = dsp.sos_filter(x.mean(0), "bandpass", (30, 250), sr, 2)
    a, b = int(pre * sr), int(post * sr)
    segs = [lo[int(round(t * sr)) - a:int(round(t * sr)) + b] for t in beats[first:last + 1]
            if t * sr - a >= 0 and t * sr + b < len(lo)]
    return np.array(segs), a


def kick_coherence(x, beats, first, last):
    """How consistently the low band repeats at each beat: |mean|^2 / mean(|seg|^2). Higher = better grid."""
    segs, _ = _kick_segments(x, beats, first, last)
    return float(np.sum(segs.mean(0) ** 2) / np.mean(np.sum(segs ** 2, axis=1)))


def kick_onset_offset(x, beats, first, last, sr=dsp.SR):
    """Time of the averaged kick's onset (10% of peak envelope) relative to the beats, in seconds."""
    segs, a = _kick_segments(x, beats, first, last)
    env = ndimage.uniform_filter1d(np.abs(segs.mean(0)), int(0.001 * sr))
    return (int(np.argmax(env > 0.1 * env.max())) - a) / sr


def track(x, bpm_guess):
    env = onset_env(x)
    b0 = dp_beats(env, bpm_guess)
    b1 = refine_to_attack(x, b0)
    b2 = smooth_beats(b1, half=32)
    strength = beat_strength(env, b0)
    b3 = refine_by_local_average(x, b2)
    b3 = refine_by_local_average(x, b3, n_avg=13, iters=2)  # second, more local pass
    b3 = smooth_beats(b3, half=8, tol=0.003)
    first, last = reliable_span(b3)
    b4, first, last = extrapolate_edges(b3, first, last)
    # DAW-made tracks have a constant tempo: if a straight grid explains the kick better than the
    # drift-following one, use it, aligned so each beat sits on the kick onset.
    i = np.arange(len(b4))
    p = np.polyfit(i[first:last + 1], b4[first:last + 1], 1)
    const = np.polyval(p, i)
    c_track, c_const = kick_coherence(x, b4, first, last), kick_coherence(x, const, first, last)
    mode = "tracked"
    if c_const > 1.05 * c_track:
        mode = "constant"
        b4 = const + kick_onset_offset(x, const, first, last)
    return {"dp": b0, "refined": b1, "smoothed": b2, "beats": b4, "strength": strength,
            "reliable_first": int(first), "reliable_last": int(last), "grid_mode": mode,
            "coherence": {"tracked": round(c_track, 3), "constant": round(c_const, 3)}}
