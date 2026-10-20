"""Harmonic/percussive separation (median-filter HPSS, Fitzgerald 2010) on stereo audio.

Usage: python3 separate.py input.wav out_prefix
Writes out_prefix_harm.npy and out_prefix_perc.npy (float32, shape (2, n)).
perc = input - harm, so the two layers always sum back to the original.
"""
import sys
import numpy as np
from scipy import ndimage
import dsp


def hpss(x, n_fft=4096, hop=1024, kt=31, kf=31, power=2.0):
    Z = [dsp.stft(ch, n_fft, hop) for ch in x]
    mag = (np.abs(Z[0]) + np.abs(Z[1])) / 2
    H = np.empty_like(mag)
    P = np.empty_like(mag)
    step, pad = 2000, kt
    for s in range(0, mag.shape[1], step):  # chunked along time to bound memory
        a, e = max(0, s - pad), min(mag.shape[1], s + step + pad)
        H[:, s:s + step] = ndimage.median_filter(mag[:, a:e], size=(1, kt))[:, s - a:s - a + step]
        P[:, s:s + step] = ndimage.median_filter(mag[:, a:e], size=(kf, 1))[:, s - a:s - a + step]
    mh = H ** power / (H ** power + P ** power + 1e-12)
    harm = np.stack([dsp.istft(z * mh, n_fft, hop, x.shape[1]) for z in Z]).astype(np.float32)
    return harm, (x - harm).astype(np.float32)


if __name__ == "__main__":
    x = dsp.load(sys.argv[1])
    harm, perc = hpss(x)
    np.save(sys.argv[2] + "_harm.npy", harm)
    np.save(sys.argv[2] + "_perc.npy", perc)
    print("harm rms dB", dsp.db(np.sqrt(np.mean(harm ** 2))), "perc rms dB", dsp.db(np.sqrt(np.mean(perc ** 2))))
