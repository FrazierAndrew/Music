"""Drum, bass and FX synthesis from scratch (numpy only). All return float arrays at dsp.SR."""
import numpy as np
import dsp
import fx

SR = dsp.SR


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(seconds):
    return np.arange(int(seconds * SR)) / SR


def _decay(t, tau, start=0.0):
    return np.exp(-np.maximum(t - start, 0) / tau)


def _fade_out(y, seconds=0.005):
    n = min(len(y), int(seconds * SR))
    y[-n:] *= np.linspace(1, 0, n)
    return y


# ---------- drums ----------

def kick(f_end=49.0, f_start=230.0, pitch_tau=0.032, body_tau=0.11, length=0.42, click=0.5, drive=2.2, seed=0):
    """Punchy electronic kick tuned to f_end Hz (49 Hz = G1)."""
    t = _t(length)
    f = f_end + (f_start - f_end) * np.exp(-t / pitch_tau)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR)
    amp = np.minimum(t / 0.0007, 1) * (0.75 * _decay(t, body_tau, 0.012) + 0.25 * _decay(t, body_tau * 2.2, 0.012))
    y = body * amp
    rng = np.random.default_rng(seed)
    nclick = rng.standard_normal(len(t)) * _decay(t, 0.0018)
    nclick = dsp.sos_filter(nclick, "bandpass", (1500, 9000), SR, 2)
    y = y + click * nclick / (np.abs(nclick).max() + 1e-9) * 0.5
    y = np.tanh(drive * y) / np.tanh(drive)
    return _fade_out(y, 0.02)


def clap(decay=0.13, seed=1):
    t = _t(0.45)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(len(t))
    bp = dsp.sos_filter(noise, "bandpass", (850, 3200), SR, 2)
    env = np.zeros(len(t))
    for k, off in enumerate([0.0, 0.0085, 0.017, 0.0255]):
        tau = 0.0045 if k < 3 else decay
        env = np.maximum(env, np.where(t >= off, _decay(t, tau, off), 0) * (0.8 if k < 3 else 1.0))
    body = np.sin(2 * np.pi * 195 * t) * _decay(t, 0.035) * 0.35
    y = bp / np.abs(bp).max() * env + body * (t < 0.2)
    return _fade_out(y / np.abs(y).max())


def snare(decay=0.11, tone=190, seed=2):
    t = _t(0.35)
    rng = np.random.default_rng(seed)
    noise = dsp.sos_filter(rng.standard_normal(len(t)), "bandpass", (1200, 8000), SR, 2)
    noise = noise / np.abs(noise).max() * _decay(t, decay)
    f = tone * (1 + 0.25 * np.exp(-t / 0.01))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * _decay(t, 0.045)
    y = 0.75 * noise + 0.6 * body
    return _fade_out(np.tanh(1.5 * y) / np.tanh(1.5))


_METAL = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0])


def _metal_noise(length, seed, scale=1.0):
    t = _t(length)
    rng = np.random.default_rng(seed)
    sq = sum(np.sign(np.sin(2 * np.pi * f * scale * t + rng.uniform(0, 2 * np.pi))) for f in _METAL)
    return sq + 1.2 * rng.standard_normal(len(t)), t


def hat(decay=0.04, seed=3, bright=1.0):
    src, t = _metal_noise(decay * 7, seed)
    y = dsp.sos_filter(src, "highpass", 7000 * bright, SR, 4)
    y = y / np.abs(y).max() * np.minimum(t / 0.0005, 1) * _decay(t, decay)
    return _fade_out(y)


def open_hat(decay=0.2, seed=4):
    src, t = _metal_noise(decay * 4, seed)
    y = dsp.sos_filter(src, "highpass", 6500, SR, 4)
    y = y / np.abs(y).max() * np.minimum(t / 0.001, 1) * _decay(t, decay)
    return _fade_out(y, 0.03)


def ride(decay=0.9, seed=5):
    t = _t(decay * 3)
    rng = np.random.default_rng(seed)
    partials = rng.uniform(2500, 9000, 14)
    tone = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * _decay(t, decay * rng.uniform(0.4, 1.0))
               for f in partials)
    bell = np.sin(2 * np.pi * 1180 * t) * _decay(t, 0.35) + 0.5 * np.sin(2 * np.pi * 2410 * t) * _decay(t, 0.25)
    noise = dsp.sos_filter(rng.standard_normal(len(t)), "highpass", 6000, SR, 2) * _decay(t, decay * 0.5)
    y = tone / np.abs(tone).max() * 0.6 + 0.25 * bell + 0.35 * noise / np.abs(noise).max()
    return _fade_out(dsp.sos_filter(y, "highpass", 900, SR, 2) * np.minimum(t / 0.0008, 1), 0.05)


def rim(freq=1650, seed=6):
    t = _t(0.12)
    rng = np.random.default_rng(seed)
    tone = np.sin(2 * np.pi * freq * t) * _decay(t, 0.012) + 0.6 * np.sin(2 * np.pi * freq * 0.53 * t) * _decay(t, 0.02)
    click = dsp.sos_filter(rng.standard_normal(len(t)), "highpass", 3000, SR, 2) * _decay(t, 0.003)
    y = tone + 0.4 * click / np.abs(click).max()
    return _fade_out(y / np.abs(y).max())


def tom(freq=110, decay=0.18):
    t = _t(decay * 3)
    f = freq * (1 + 0.6 * np.exp(-t / 0.03))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(t / 0.001, 1) * _decay(t, decay)
    return _fade_out(np.tanh(1.8 * y) / np.tanh(1.8))


def crash(length=3.0, seed=8):
    t = _t(length)
    out = []
    for c in range(2):
        src, _ = _metal_noise(length, seed + c, scale=3.1)
        y = dsp.sos_filter(src, "highpass", 3500, SR, 2)
        y = y / np.abs(y).max() * np.minimum(t / 0.002, 1) * (0.6 * _decay(t, 0.25) + 0.4 * _decay(t, length / 4))
        out.append(_fade_out(y, 0.2))
    return np.stack(out)


# ---------- tonal ----------

def saw(f, t, detune_cents=0.0, phase=0.0):
    ff = f * 2 ** (detune_cents / 1200)
    return 2 * ((ff * t + phase) % 1.0) - 1


_bass_cache = {}


def bass_note(midi, length, growl=0.0, pluck=0.6):
    """Rolling-bass note: sine sub + plucked filtered saw (+ optional detuned growl)."""
    key = (int(midi), round(length, 4), round(growl, 3), round(pluck, 3))
    if key in _bass_cache:
        return _bass_cache[key]
    f = midi_hz(midi)
    t = _t(length)
    amp = np.minimum(t / 0.0025, 1) * (0.72 + 0.28 * _decay(t, 0.05))
    sub = np.sin(2 * np.pi * f * t)
    s = saw(f, t) + 0.5 * saw(2 * f, t)
    cut = 180 + 2200 * pluck * np.exp(-t / 0.045)
    mid = fx.tv_filter(s, "lowpass", cut, q=0.9, stages=1, block=16)[0]
    y = sub + 0.32 * mid
    if growl > 0:
        r = saw(f, t, -14) + saw(f, t, 13, 0.33) + 0.7 * saw(2 * f, t, 7, 0.6)
        r = fx.tv_filter(r, "lowpass", 380 + 900 * growl, q=1.1, stages=2, block=64)[0]
        y = y + growl * 0.35 * np.tanh(2.5 * r)
    y = np.tanh(1.4 * y * amp) / np.tanh(1.4)
    y = _fade_out(y, 0.012)
    _bass_cache[key] = y
    return y


def sub_drone(midi, length, attack=0.4, release=0.8):
    f = midi_hz(midi)
    t = _t(length)
    y = np.sin(2 * np.pi * f * t) + 0.08 * np.sin(4 * np.pi * f * t)
    env = np.minimum(t / attack, 1) * np.minimum((length - t) / release, 1)
    return y * np.clip(env, 0, 1)


def pluck(midi, length=0.5, bright=1.0, seed=0):
    """Glassy FM pluck for the arp layer."""
    f = midi_hz(midi)
    t = _t(length)
    idx = 2.2 * bright * _decay(t, 0.06)
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 2 * f * t)) * _decay(t, 0.16)
    y += 0.25 * np.sin(2 * np.pi * 2 * f * t) * _decay(t, 0.08)
    return _fade_out(y * np.minimum(t / 0.002, 1), 0.02)


def wave_bass(midi, length, decay_db=11.0, attack=0.035, h2_db=-15.0, h3_db=-22.0, release=0.3):
    """'Tidal wave' sub modelled on ddd2's last drop: near-sine, fast attack, recedes decay_db over the note."""
    f = midi_hz(midi)
    t = _t(length)
    y = np.sin(2 * np.pi * f * t) + dsp.undb(h2_db) * np.sin(4 * np.pi * f * t) + \
        dsp.undb(h3_db) * np.sin(6 * np.pi * f * t)
    env = dsp.undb(-decay_db * t / length) * np.minimum(t / attack, 1)
    env *= np.clip((length - t) / release, 0, 1)
    return np.tanh(1.2 * y * env) / np.tanh(1.2)


def reese(midi, length, cutoff=650, detune=14.0, lfo_hz=0.3, drive=2.0, seed=0):
    """Detuned-saw reese (stereo), low-passed with slow movement, sub removed (leave that to a sine)."""
    f = midi_hz(midi)
    t = _t(length)
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 1, 4)
    left = saw(f, t, -detune, ph[0]) + saw(f, t, detune * 0.6, ph[1])
    right = saw(f, t, detune, ph[2]) + saw(f, t, -detune * 0.6, ph[3])
    cut = cutoff * (1 + 0.45 * np.sin(2 * np.pi * lfo_hz * t + rng.uniform(0, 6.28)))
    y = fx.tv_filter(np.stack([left, right]), "lowpass", cut, q=1.1, stages=2, block=64)
    y = np.tanh(drive * y / 2) / np.tanh(drive)
    y = dsp.sos_filter(y, "highpass", 90, SR, 2)
    env = np.minimum(t / 0.012, 1) * np.clip((length - t) / 0.03, 0, 1)
    return y * env


# ---------- transitions ----------

def riser(length, f0=350, f1=9000, seed=9):
    n = int(length * SR)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((2, n))
    y = fx.tv_filter(noise, "bandpass", fx.sweep(n, f0, f1), q=1.4, stages=1, block=64)
    y = y / (np.abs(y).max() + 1e-9)
    amp = np.linspace(0, 1, n) ** 2.2
    t = np.arange(n) / SR
    fsweep = 140 * (1500 / 140) ** (t / length) ** 1.5
    tone = np.sin(2 * np.pi * np.cumsum(fsweep) / SR) * 0.25
    return (y + tone) * amp


def downlifter(length, seed=10):
    n = int(length * SR)
    rng = np.random.default_rng(seed)
    y = fx.tv_filter(rng.standard_normal((2, n)), "bandpass", fx.sweep(n, 8000, 250), q=1.0, stages=1, block=64)
    y = y / (np.abs(y).max() + 1e-9)
    return y * np.linspace(1, 0, n) ** 2


def impact(length=2.5):
    t = _t(length)
    f = 32 + 40 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(t / 0.002, 1) * _decay(t, 0.55)
    boom = np.tanh(2.0 * boom) / np.tanh(2.0)
    return _fade_out(boom, 0.3)


def reverse_swell(x, ir):
    """Reverse reverb: reverb the (short) input, reverse it so it swells into the hit."""
    wet = fx.reverb(np.pad(fx.as_stereo(x), ((0, 0), (0, ir.shape[1]))), ir)
    return wet[:, ::-1]
