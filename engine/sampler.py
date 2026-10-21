"""Sampler engine: capture one-shots from your stems, shape them (amp and filter envelopes), repitch them the
way a hardware sampler does (by playback speed), and play them from step patterns.
"""
import numpy as np
import dsp
import fx

SR = dsp.SR


def capture(layer, t0, dur, fade_in=0.003, fade_out=0.012):
    """Slice (2, n) audio from a stem starting at t0 seconds."""
    a = int(t0 * SR)
    x = np.array(layer[:, a:a + int(dur * SR)], dtype=np.float64)
    n = x.shape[1]
    fi, fo = int(fade_in * SR), int(fade_out * SR)
    x[:, :fi] *= np.linspace(0, 1, fi)
    x[:, n - fo:] *= np.linspace(1, 0, fo)
    return x


def normalize(x, peak=0.9):
    return x * (peak / (np.abs(x).max() + 1e-12))


def amp_env(x, attack=0.003, hold=0.03, decay=0.25, floor=0.0):
    n = x.shape[-1]
    t = np.arange(n) / SR
    env = np.where(t < attack, t / attack, np.where(t < attack + hold, 1.0,
                   floor + (1 - floor) * np.exp(-(t - attack - hold) / decay)))
    return x * env


def filter_env(x, f0, f1, time):
    """Low-pass that sweeps from f0 to f1 Hz over `time` seconds, then holds (the classic sampler pluck)."""
    n = x.shape[-1]
    k = min(n, int(time * SR))
    cut = np.full(n, float(f1))
    cut[:k] = np.geomspace(f0, f1, k)
    return fx.tv_filter(x, "lowpass", cut)


def repitch(x, semitones):
    """Change pitch by playback speed (length changes too), like an Akai or SP sampler."""
    r = 2 ** (semitones / 12)
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    n = int(x.shape[1] / r)
    idx = np.arange(n) * r
    return np.stack([np.interp(idx, np.arange(x.shape[1]), c) for c in x])


def reverse(x):
    return np.asarray(x)[..., ::-1].copy()
