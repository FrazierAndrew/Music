"""Spectral engine: work on magnitude spectra instead of waveforms.

- chord_spectrum: the long-term spectrum of one chord in your pad (median over every bar that plays it)
- freeze: resynthesize any sequence of magnitude spectra with fresh random phases (a stationary, endlessly
  sustained version of the sound, the method behind paulstretch), frame by frame with overlap-add
- morph_frames: frame magnitudes that follow a chord timeline and glide (log domain) into each change
- shift: transpose a spectrum by scaling its frequency axis (octaves only, to stay consonant)
- tilt: brightness motion; band_gate: rhythmic gating per frequency band in the time domain
- spectral_delay: per-bin delay with feedback, high partials echoing later than low ones (cascades)
"""
import numpy as np
from scipy import signal
import dsp

SR = dsp.SR


def stft(x, n_fft, hop):
    win = signal.windows.hann(n_fft, sym=False)
    xp = np.pad(np.asarray(x, dtype=np.float64), n_fft // 2)
    n_frames = 1 + (len(xp) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    return np.fft.rfft(xp[idx] * win, axis=1).T, win


def istft(Z, n_fft, hop, win, length):
    frames = np.fft.irfft(Z.T, n=n_fft, axis=1) * win
    n = n_fft + hop * (frames.shape[0] - 1)
    y, ws = np.zeros(n), np.zeros(n)
    for k, fr in enumerate(frames):
        y[k * hop:k * hop + n_fft] += fr
        ws[k * hop:k * hop + n_fft] += win ** 2
    y /= np.where(ws > 1e-9, ws, 1.0)
    out = y[n_fft // 2:n_fft // 2 + length]
    return np.pad(out, (0, max(0, length - len(out))))


def chord_spectrum(x, t_ranges, n_fft=16384):
    """Median magnitude spectrum (2, bins) of x over the given (t0, t1) second ranges."""
    hop = n_fft // 4
    win = signal.windows.hann(n_fft, sym=False)
    out = []
    for c in range(2):
        frames = []
        for t0, t1 in t_ranges:
            a, b = int(t0 * SR), int(t1 * SR)
            for s in range(a, b - n_fft, hop):
                frames.append(np.abs(np.fft.rfft(np.asarray(x[c, s:s + n_fft], dtype=np.float64) * win)))
        out.append(np.median(np.array(frames), axis=0))
    return np.array(out)


def morph_frames(chord_at_frame, spectra, morph_frames_n):
    """chord_at_frame: list of chord names per frame. Returns (frames, 2, bins) magnitudes that glide in
    the log domain over `morph_frames_n` frames before each chord change."""
    names = list(chord_at_frame)
    logs = {k: np.log(v + 1e-9) for k, v in spectra.items()}
    out = np.empty((len(names),) + next(iter(spectra.values())).shape, dtype=np.float32)
    for i, c in enumerate(names):
        nxt, dist = None, None
        for j in range(i + 1, min(len(names), i + morph_frames_n + 1)):
            if names[j] != c:
                nxt, dist = names[j], j - i
                break
        if nxt is None:
            out[i] = spectra[c]
        else:
            a = 1 - dist / (morph_frames_n + 1)
            out[i] = np.exp((1 - a) * logs[c] + a * logs[nxt])
    return out


def freeze(mags, n_out, n_fft=16384, hop=4096, seed=0):
    """Overlap-add resynthesis of per-frame magnitudes (frames, 2, bins) with random phases; independent
    phases per channel give a wide, still image. Output (2, n_out)."""
    rng = np.random.default_rng(seed)
    win = signal.windows.hann(n_fft, sym=False)
    out = np.zeros((2, n_out + n_fft))
    for i in range(min(len(mags), n_out // hop + 1)):
        a = i * hop
        for c in range(2):
            ph = rng.uniform(0, 2 * np.pi, mags.shape[2])
            fr = np.fft.irfft(mags[i, c] * np.exp(1j * ph), n_fft) * win
            out[c, a:a + n_fft] += fr
    norm = np.sum(win ** 2) / hop
    return out[:, n_fft // 2:n_fft // 2 + n_out] / norm


def shift(M, ratio):
    """Transpose a magnitude spectrum (..., bins) by `ratio` (2.0 = an octave up)."""
    bins = M.shape[-1]
    k = np.arange(bins)
    src = k / ratio
    return np.stack([np.interp(src, k, m, right=0.0) for m in M.reshape(-1, bins)]).reshape(M.shape)


def tilt(M, n_fft, slope_db_per_oct):
    """Brightness: multiply by (f / 1 kHz) ** slope, slope in dB per octave."""
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    g = (np.maximum(f, 20.0) / 1000.0) ** (slope_db_per_oct / 6.02)
    return M * g


def gate_env(n, hits, decay_s, floor=0.15, attack_s=0.006):
    """Envelope that jumps to 1 at each hit sample and decays toward `floor`."""
    env = np.full(n, floor)
    L = int((attack_s + decay_s * 5) * SR)
    t = np.arange(L) / SR
    shape = floor + (1 - floor) * np.minimum(t / attack_s, 1) * np.exp(-np.maximum(t - attack_s, 0) / decay_s)
    for h in hits:
        e = min(n, h + L)
        if h < n:
            env[h:e] = np.maximum(env[h:e], shape[:e - h])
    return env


def band_gate(x, bands, envs):
    """Split x into bands (sos band-pass) and multiply each by its envelope; envs[i] is (n,) or None (ungated)."""
    x = np.asarray(x, dtype=np.float64)
    out = np.zeros_like(x)
    for (lo, hi), env in zip(bands, envs):
        b = dsp.sos_filter(x, "bandpass", (lo, min(hi, 0.45 * SR)), SR, 2)
        out += b if env is None else b * env
    return out


def spectral_delay(x, max_delay_s, feedback=0.5, n_fft=2048, hop=512, power=0.7, damp=0.85):
    """Per-bin feedback delay: bin k echoes after max_delay_s * (k / K) ** power, so high partials trail
    behind low ones and notes dissolve into rising cascades. Wet only, stereo in and out."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x])
    out = []
    for c in range(2):
        X, win = stft(x[c], n_fft, hop)
        K, F = X.shape
        d = np.maximum(1, np.round(max_delay_s * SR / hop * (np.arange(K) / K) ** power)).astype(int)
        d = d + c * 2  # tiny L/R offset for width
        g = feedback * damp ** (np.arange(K) / K)
        Y = np.zeros_like(X)
        kk = np.arange(K)
        for t in range(F):
            src = t - d
            ok = src >= 0
            Y[:, t] = np.where(ok, g * Y[kk, np.maximum(src, 0)], 0.0) + X[:, t]
        out.append(istft(Y - X, n_fft, hop, win, x.shape[1]))
    return np.array(out)
