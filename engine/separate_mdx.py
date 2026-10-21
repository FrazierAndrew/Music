"""Neural 4-stem separation with the KUIELab MDX-Net models (ONNX, run by onnxruntime on CPU).

Usage: python3 engine/separate_mdx.py src/<t>.wav work/<t>
Writes work/<t>_{drums,bass,other,vocals}.npy (float32, (2, n), 48 kHz) and work/<t>_resid.npy
(input minus the four stems, for diagnostics).
Models: models/kuielab_b_<stem>.onnx from the UVR model repository (GitHub release all_public_uvr_models).
Each model maps the mixture spectrogram (STFT at 44.1 kHz, hop 1024, n_fft = 2048 x scale) to the stem's.
Much cleaner than HPSS: it separates by instrument, so the original kick leaves the pads.
"""
import os
import sys
import time
import numpy as np
from scipy import signal
import onnxruntime as ort
import dsp

MODEL_DIR = os.environ.get("REMIX_MODELS", "models")
HOP, DIM_F, SR_MODEL = 1024, 2048, 44100
N_FFT = {"vocals": 6144, "drums": 4096, "bass": 16384, "other": 8192}  # dim_f x (3, 2, 8, 4)


def _stft(x, n_fft, win):
    """torch.stft(center=True, reflect pad, periodic Hann, no normalization), shape (bins, frames)."""
    xp = np.pad(x, n_fft // 2, mode="reflect")
    n_frames = 1 + (len(xp) - n_fft) // HOP
    idx = np.arange(n_fft)[None, :] + HOP * np.arange(n_frames)[:, None]
    return np.fft.rfft(xp[idx] * win, axis=1).T


def _istft(Z, n_fft, win, length):
    frames = np.fft.irfft(Z.T, n=n_fft, axis=1) * win
    n = n_fft + HOP * (frames.shape[0] - 1)
    y, wsum = np.zeros(n), np.zeros(n)
    w2 = win ** 2
    for k, fr in enumerate(frames):
        y[k * HOP:k * HOP + n_fft] += fr
        wsum[k * HOP:k * HOP + n_fft] += w2
    y /= np.where(wsum > 1e-10, wsum, 1.0)
    return y[n_fft // 2:n_fft // 2 + length]


def demix(mix, stem):
    """mix: (2, n) float at 44.1 kHz -> estimated stem (2, n)."""
    sess = ort.InferenceSession(f"{MODEL_DIR}/kuielab_b_{stem}.onnx", providers=["CPUExecutionProvider"])
    dim_t = sess.get_inputs()[0].shape[3]
    n_fft = N_FFT[stem]
    win = signal.windows.hann(n_fft, sym=False)
    chunk = HOP * (dim_t - 1)
    trim = n_fft // 2
    gen = chunk - 2 * trim
    n = mix.shape[1]
    pad = gen - n % gen
    mp = np.concatenate([np.zeros((2, trim)), mix, np.zeros((2, pad + trim))], 1)
    out = []
    for i in range(0, n + pad, gen):
        w = mp[:, i:i + chunk]
        L, R = _stft(w[0], n_fft, win), _stft(w[1], n_fft, win)
        X = np.stack([L.real, L.imag, R.real, R.imag])[:, :DIM_F, :dim_t]
        Y = sess.run(None, {sess.get_inputs()[0].name: X[None].astype(np.float32)})[0][0]
        full = np.zeros((4, n_fft // 2 + 1, dim_t))
        full[:, :DIM_F] = Y
        yl = _istft(full[0] + 1j * full[1], n_fft, win, chunk)
        yr = _istft(full[2] + 1j * full[3], n_fft, win, chunk)
        out.append(np.stack([yl, yr])[:, trim:chunk - trim])
    return np.concatenate(out, 1)[:, :n]


def main(src, prefix):
    mix = dsp.load(src, sr=SR_MODEL).astype(np.float64)
    full = dsp.load(src)  # 48 kHz original, for the residual
    total = np.zeros_like(full, dtype=np.float64)
    for stem in ("drums", "bass", "other", "vocals"):
        t0 = time.time()
        y = demix(mix, stem)
        y48 = signal.resample_poly(y, 160, 147, axis=1)[:, :full.shape[1]]
        if y48.shape[1] < full.shape[1]:
            y48 = np.pad(y48, ((0, 0), (0, full.shape[1] - y48.shape[1])))
        np.save(f"{prefix}_{stem}.npy", y48.astype(np.float32))
        total += y48
        print(f"{stem}: {time.time() - t0:.0f}s, rms {dsp.db(np.sqrt(np.mean(y48 ** 2))):.1f} dB")
    resid = full - total
    np.save(f"{prefix}_resid.npy", resid.astype(np.float32))
    print(f"residual rms {dsp.db(np.sqrt(np.mean(resid ** 2))):.1f} dB vs mix {dsp.db(np.sqrt(np.mean(full ** 2))):.1f} dB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
