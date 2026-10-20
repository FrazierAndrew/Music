"""Shared DSP helpers. Only numpy, scipy and ffmpeg (no pip packages needed)."""
import subprocess
import numpy as np
from scipy import signal

SR = 48000


# ---------- I/O ----------

def load(path, sr=SR):
    """Decode any audio file to float32 stereo, shape (2, n)."""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-acodec", "pcm_f32le",
           "-ac", "2", "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T.copy()


def save(path, x, sr=SR, codec="pcm_s24le", extra=()):
    """Write (2, n) float audio. codec examples: pcm_s24le, libmp3lame."""
    x = np.ascontiguousarray(np.asarray(x, dtype=np.float32).T)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2",
           "-i", "-", "-c:a", codec, *extra, path]
    subprocess.run(cmd, input=x.tobytes(), check=True)


# ---------- spectral analysis ----------

def stft_mag(y, n_fft, hop):
    """Magnitude STFT of a mono signal, shape (n_fft//2+1, frames). Centered frames."""
    win = signal.get_window("hann", n_fft).astype(np.float32)
    yp = np.pad(y.astype(np.float32), n_fft // 2)
    n_frames = 1 + (len(yp) - n_fft) // hop
    out = np.empty((n_fft // 2 + 1, n_frames), dtype=np.float32)
    offs = np.arange(n_fft)
    for s in range(0, n_frames, 2048):
        e = min(n_frames, s + 2048)
        idx = (np.arange(s, e) * hop)[:, None] + offs[None, :]
        out[:, s:e] = np.abs(np.fft.rfft(yp[idx] * win, axis=1)).T
    return out


def mel_filterbank(sr, n_fft, n_mels=128, fmin=30.0, fmax=None):
    fmax = fmax or sr / 2
    hz2mel = lambda f: 2595 * np.log10(1 + f / 700)
    mel2hz = lambda m: 700 * (10 ** (m / 2595) - 1)
    hz = mel2hz(np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    fb = np.zeros((n_mels, len(freqs)), np.float32)
    for i in range(n_mels):
        lo, c, hi = hz[i], hz[i + 1], hz[i + 2]
        fb[i] = np.maximum(0, np.minimum((freqs - lo) / (c - lo), (hi - freqs) / (hi - c)))
    return fb, hz[1:-1]


def onset_envelope(mel_power, band=None):
    """Spectral flux on log-mel power. band = slice of mel rows to use."""
    m = mel_power if band is None else mel_power[band]
    logm = 10 * np.log10(np.maximum(m, 1e-10))
    logm = np.maximum(logm, logm.max() - 80)
    flux = np.maximum(0, np.diff(logm, axis=1)).mean(0)
    return np.concatenate([[0.0], flux]).astype(np.float32)


def chroma(mag, sr, n_fft, fmin=65.0, fmax=4000.0):
    """12 x frames pitch-class energy from a magnitude STFT."""
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    sel = (freqs >= fmin) & (freqs <= fmax)
    pc = np.round(69 + 12 * np.log2(freqs[sel] / 440.0)).astype(int) % 12
    proj = np.zeros((12, sel.sum()), np.float32)
    proj[pc, np.arange(sel.sum())] = 1.0
    return proj @ (mag[sel] ** 2)


KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def estimate_key(chroma_vec):
    """Return list of (score, name) for all 24 keys, best first."""
    v = chroma_vec / (chroma_vec.sum() + 1e-12)
    res = []
    for k in range(12):
        for prof, mode in ((KRUMHANSL_MAJOR, "major"), (KRUMHANSL_MINOR, "minor")):
            res.append((np.corrcoef(v, np.roll(prof, k))[0, 1], f"{NOTE_NAMES[k]} {mode}"))
    return sorted(res, reverse=True)


def stft(y, n_fft=4096, hop=1024):
    """Complex STFT of a mono signal, shape (bins, frames). Centered, zero padded."""
    win = signal.get_window("hann", n_fft).astype(np.float32)
    yp = np.pad(y.astype(np.float32), n_fft // 2)
    n_frames = 1 + (len(yp) - n_fft) // hop
    out = np.empty((n_fft // 2 + 1, n_frames), dtype=np.complex64)
    offs = np.arange(n_fft)
    for s in range(0, n_frames, 2048):
        e = min(n_frames, s + 2048)
        idx = (np.arange(s, e) * hop)[:, None] + offs[None, :]
        out[:, s:e] = np.fft.rfft(yp[idx] * win, axis=1).T
    return out


def istft(Z, n_fft=4096, hop=1024, length=None):
    """Inverse of stft() by weighted overlap-add."""
    win = signal.get_window("hann", n_fft).astype(np.float32)
    n_frames = Z.shape[1]
    total = n_fft + hop * (n_frames - 1)
    y = np.zeros(total, np.float32)
    wsum = np.zeros(total, np.float32)
    for s in range(0, n_frames, 2048):
        e = min(n_frames, s + 2048)
        frames = np.fft.irfft(Z[:, s:e].T, n_fft, axis=1).astype(np.float32) * win
        for j, f in enumerate(frames):
            a = (s + j) * hop
            y[a:a + n_fft] += f
            wsum[a:a + n_fft] += win ** 2
    y = y / np.maximum(wsum, 1e-6)
    y = y[n_fft // 2:]
    return y[:length] if length else y


# ---------- filters / dynamics ----------

def sos_filter(x, kind, freq, sr=SR, order=4):
    """Zero-phase Butterworth (kind: lowpass/highpass/bandpass). Works on (..., n)."""
    sos = signal.butter(order, freq, btype=kind, fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=-1)


def sos_filter_causal(x, kind, freq, sr=SR, order=2):
    sos = signal.butter(order, freq, btype=kind, fs=sr, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def undb(d):
    return 10 ** (d / 20)


def lufs(x, sr=SR):
    """Integrated loudness (ITU-R BS.1770-4, gated) of (2, n) audio."""
    # K-weighting: high-shelf + high-pass (coefficients derived for arbitrary sr)
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / sr)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / sr)
    a0 = 1 + K / Q + K * K
    b2 = [1, -2, 1]
    a2 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    y = signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=-1), axis=-1)
    blk, step = int(0.4 * sr), int(0.1 * sr)
    n = 1 + (y.shape[-1] - blk) // step
    if n < 1:
        return -70.0
    p = np.square(y).astype(np.float64)
    cs = np.concatenate([np.zeros((p.shape[0], 1)), np.cumsum(p, axis=-1)], axis=-1)
    starts = np.arange(n) * step
    ms = (cs[:, starts + blk] - cs[:, starts]) / blk
    z = ms.sum(0)
    l = -0.691 + 10 * np.log10(np.maximum(z, 1e-20))
    z = z[l > -70]
    if len(z) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    l = -0.691 + 10 * np.log10(z)
    return float(-0.691 + 10 * np.log10(z[l > rel].mean()))


def true_peak_db(x, sr=SR):
    """4x oversampled peak (BS.1770 style) in dBFS."""
    up = signal.resample_poly(x, 4, 1, axis=-1)
    return float(db(np.max(np.abs(up))))
