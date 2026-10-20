"""Effects and dynamics: time-varying filters, reverb, delay, sidechain, blur, compression, limiting."""
import subprocess
import tempfile
import os
import numpy as np
from scipy import signal, ndimage
import dsp

SR = dsp.SR


def as_stereo(x):
    return np.stack([x, x]) if x.ndim == 1 else x


# ---------- filters ----------

def _biquad(kind, fc, q, sr):
    w = 2 * np.pi * np.clip(fc, 10, sr * 0.45) / sr
    cw, sw = np.cos(w), np.sin(w)
    alpha = sw / (2 * q)
    if kind == "lowpass":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    elif kind == "highpass":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    elif kind == "bandpass":
        b = [alpha, 0, -alpha]
    else:
        raise ValueError(kind)
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return np.array(b) / a[0], np.array(a) / a[0]


def tv_filter(x, kind, cutoff, q=0.707, stages=2, block=32, sr=SR):
    """Time-varying biquad filter. cutoff: array of length n (Hz) or scalar.

    stages=2 gives 24 dB/oct for low/high pass.
    """
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    n = x.shape[1]
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), (n,))
    y = x.copy()
    for _ in range(stages):
        zi = np.zeros((y.shape[0], 2))
        out = np.empty_like(y)
        for s in range(0, n, block):
            e = min(n, s + block)
            b, a = _biquad(kind, cutoff[s], q, sr)
            out[:, s:e], zi = signal.lfilter(b, a, y[:, s:e], axis=1, zi=zi)
        y = out
    return y


def sweep(n, start, end, shape="exp"):
    """Cutoff curve from start to end Hz over n samples."""
    u = np.linspace(0, 1, n)
    if shape == "exp":
        return start * (end / start) ** u
    return start + (end - start) * u


def eq_shelf(x, freq, gain_db, kind="low", sr=SR):
    """RBJ shelving filter (static)."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * freq / sr
    cw, sw = np.cos(w), np.sin(w)
    alpha = sw / 2 * np.sqrt(2)
    if kind == "low":
        b = [A * ((A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha), 2 * A * ((A - 1) - (A + 1) * cw),
             A * ((A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha)]
        a = [(A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha, -2 * ((A - 1) + (A + 1) * cw),
             (A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha]
    else:
        b = [A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha), -2 * A * ((A - 1) + (A + 1) * cw),
             A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha)]
        a = [(A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha, 2 * ((A - 1) - (A + 1) * cw),
             (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=-1)


def eq_peak(x, freq, gain_db, q=1.0, sr=SR):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * freq / sr
    alpha = np.sin(w) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w), 1 - alpha / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=-1)


# ---------- space ----------

def make_ir(rt60=2.5, predelay=0.02, hi_damp=0.5, width=1.0, seed=7, sr=SR):
    """Stereo reverb impulse response: decorrelated noise with faster decay above 3 kHz."""
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.1 * sr)
    t = np.arange(n) / sr
    noise = rng.standard_normal((2, n))
    if width < 1.0:
        m = noise.mean(0)
        noise = m + width * (noise - m)
    lo = dsp.sos_filter(noise, "lowpass", 3000, sr, 2) * np.exp(-6.91 * t / rt60)
    hi = dsp.sos_filter(noise, "highpass", 3000, sr, 2) * np.exp(-6.91 * t / (rt60 * hi_damp))
    ir = dsp.sos_filter(lo + hi, "highpass", 120, sr, 2)
    ir[:, :int(0.004 * sr)] *= np.linspace(0, 1, int(0.004 * sr))
    ir = np.pad(ir, ((0, 0), (int(predelay * sr), 0)))
    return ir / np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))


def reverb(x, ir):
    """Wet-only convolution reverb. Mono or stereo in, stereo out, same length."""
    x = as_stereo(x)
    return np.stack([signal.oaconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])


def pingpong(x, delay_s, feedback=0.45, taps=8, lp=5000, sr=SR):
    """Wet-only ping-pong delay, stereo out."""
    mono = x.mean(0) if x.ndim == 2 else x
    n = len(mono)
    d = int(round(delay_s * sr))
    out = np.zeros((2, n))
    sig = mono.astype(np.float64)
    for k in range(1, taps + 1):
        sig = dsp.sos_filter_causal(sig, "lowpass", lp, sr, 1) * feedback
        if k * d >= n:
            break
        out[(k - 1) % 2, k * d:] += sig[:n - k * d]
    return out


def widen(x, amount=1.3):
    """Mid/side width scaling."""
    m, s = (x[0] + x[1]) / 2, (x[0] - x[1]) / 2
    s = s * amount
    return np.stack([m + s, m - s])


def mono_below(x, freq=120, sr=SR):
    """Collapse the stereo image below freq to mono (keeps sub phase-coherent)."""
    lo = dsp.sos_filter(x, "lowpass", freq, sr, 4)
    hi = x - lo
    return hi + lo.mean(0, keepdims=True)


# ---------- time / spectral tricks ----------

def spectral_blur(x, seconds, n_fft=8192, hop=1024, sr=SR):
    """Smooth STFT magnitudes over time (removes pumping/transients, keeps chords)."""
    w = max(1, int(seconds * sr / hop))
    out = []
    for ch in as_stereo(x):
        Z = dsp.stft(ch, n_fft, hop)
        mag = ndimage.uniform_filter1d(np.abs(Z), w, axis=1)
        out.append(dsp.istft(mag * np.exp(1j * np.angle(Z)), n_fft, hop, len(ch)))
    return np.stack(out)


def rubberband(x, tempo=1.0, pitch=1.0, sr=SR):
    """Time-stretch / pitch-shift through ffmpeg's rubberband filter."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.wav"), os.path.join(d, "out.wav")
        dsp.save(src, as_stereo(x), sr, codec="pcm_f32le")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        f"rubberband=tempo={tempo}:pitch={pitch}:transients=smooth:window=long",
                        "-c:a", "pcm_f32le", dst], check=True)
        return dsp.load(dst, sr)


def tape_stop(x, sr=SR):
    """Slow a segment to a halt (pitch and speed fall together), same length out."""
    x = as_stereo(x)
    n = x.shape[1]
    speed = (1 - np.linspace(0, 1, n)) ** 1.6
    pos = np.cumsum(speed)
    pos = pos - pos[0]
    out = np.stack([np.interp(pos, np.arange(n), ch) for ch in x])
    return out * np.linspace(1, 0.6, n)


def stutter(x, start, slice_len, repeats, gate=0.9):
    """Repeat x[start:start+slice_len] `repeats` times with a short gate fade."""
    x = as_stereo(x)
    seg = x[:, start:start + slice_len].copy()
    g = int(slice_len * gate)
    env = np.ones(slice_len)
    f = min(64, g // 4)
    env[:f] = np.linspace(0, 1, f)
    env[g - f:g] = np.linspace(1, 0, f)
    env[g:] = 0
    return np.tile(seg * env, (1, repeats))


# ---------- dynamics ----------

def duck_curve(n, triggers, depth_db, attack=0.004, release=0.16, sr=SR):
    """Gain curve (linear) dipping by depth_db at each trigger sample, exponential recovery."""
    L = int(release * 5 * sr)
    t = np.arange(L) / sr
    shape = -depth_db * np.minimum(t / attack, 1.0) * np.exp(-np.maximum(t - attack, 0) / release)
    g = np.zeros(n)
    for s in triggers:
        s = int(s)
        if s >= n:
            continue
        e = min(n, s + L)
        g[s:e] = np.minimum(g[s:e], shape[:e - s])
    return dsp.undb(g)


def compress(x, threshold_db=-18, ratio=2.0, attack=0.01, release=0.15, knee_db=6, makeup_db=0.0, sr=SR):
    """Feed-forward RMS compressor (stereo-linked)."""
    x = as_stereo(x)
    p = ndimage.uniform_filter1d(np.mean(x ** 2, axis=0), int(0.005 * sr))
    lvl = 10 * np.log10(p + 1e-12)
    over = lvl - threshold_db
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    # attack/release smoothing of gain reduction (dB), decimated for speed
    dec = 48
    g = gr[::dec]
    a_att = np.exp(-dec / (attack * sr))
    a_rel = np.exp(-dec / (release * sr))
    out = np.empty_like(g)
    s = 0.0
    for i, v in enumerate(g):
        s = a_att * s + (1 - a_att) * v if v > s else a_rel * s + (1 - a_rel) * v
        out[i] = s
    gr_s = np.interp(np.arange(len(gr)), np.arange(len(out)) * dec, out)
    return x * dsp.undb(makeup_db - gr_s), gr_s


def soft_clip(x, threshold=0.8):
    a = np.abs(x)
    over = a > threshold
    y = x.copy()
    y[over] = np.sign(x[over]) * (threshold + (1 - threshold) * np.tanh((a[over] - threshold) / (1 - threshold)))
    return y


def limiter(x, ceiling_db=-1.0, lookahead=0.002, release=0.08, sr=SR):
    """Look-ahead brickwall limiter on 4x-oversampled peaks (true-peak aware)."""
    x = as_stereo(x).astype(np.float64)
    c = dsp.undb(ceiling_db)
    up = np.abs(signal.resample_poly(x, 4, 1, axis=1)).max(0)
    pk = up[:x.shape[1] * 4].reshape(-1, 4).max(1)
    pk = np.maximum(pk, np.abs(x).max(0))
    req = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    L = int(lookahead * sr)
    hold = ndimage.minimum_filter1d(req, 2 * L + 1)
    # release: gain may rise at most `rate` dB per sample
    rate = 20.0 / (release * sr)
    gdb = dsp.db(hold)
    k = np.arange(len(gdb))
    win = int(release * 4 * sr)
    # pad with a huge value: the default 'reflect' edge mode pulled ~-80 dB into the first window
    gdb = ndimage.minimum_filter1d(gdb - rate * k, win, origin=(win - 1) // 2, mode="constant", cval=1e9) + rate * k
    g = dsp.undb(np.minimum(gdb, 0))
    # moving average of a held minimum never exceeds the required gain at any sample
    g = ndimage.uniform_filter1d(g, 2 * L + 1)
    return x * g
