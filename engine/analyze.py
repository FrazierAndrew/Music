"""Analyze a track: loudness, drift-following beat grid, downbeats, key, per-bar harmony and energy.

Usage: python3 analyze.py input.wav out_dir [harmonic_layer.npy]
Writes out_dir/analysis.json and out_dir/analysis.png. If the harmonic layer from separate.py is
given, bass notes are also measured on it (more reliable: the kick and pumping sidebands bias them).
"""
import sys
import json
import numpy as np
from scipy import signal, ndimage
import dsp
import beats as beatlib

AN_SR = 24000


def tempo_guess(x):
    env = beatlib.onset_env(x)
    e = env - env.mean()
    n = len(e)
    ac = np.fft.irfft(np.abs(np.fft.rfft(e, 2 * n)) ** 2)[:n]
    lags = np.arange(1, n)
    bpm = 60 * beatlib.FPS / lags
    prior = np.exp(-0.5 * ((np.log2(bpm) - np.log2(125)) / 1.0) ** 2)
    score = np.where((bpm >= 70) & (bpm <= 190), ac[1:] * prior, -np.inf)
    return float(bpm[np.argmax(score)])


def bass_notes(x, beat_times, sr=dsp.SR):
    """Dominant pitch (MIDI, float) below 200 Hz for each beat."""
    lo = dsp.sos_filter(x.mean(0), "lowpass", 200, sr, order=6)
    rate = 2000
    y = signal.resample_poly(lo, 1, sr // rate)
    out = []
    for a, b in zip(beat_times[:-1], beat_times[1:]):
        seg = y[int(a * rate):int(b * rate)]
        if len(seg) < 64:
            out.append(np.nan)
            continue
        n = 8192
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
        f = np.fft.rfftfreq(n, 1 / rate)
        sel = (f >= 28) & (f <= 200)
        k = np.argmax(spec * sel)
        if 0 < k < len(spec) - 1:  # parabolic interpolation
            a1, a2, a3 = np.log(spec[k - 1:k + 2] + 1e-12)
            k = k + 0.5 * (a1 - a3) / (a1 - 2 * a2 + a3)
        out.append(69 + 12 * np.log2(k * rate / n / 440))
    return np.array(out + [out[-1]])


def note_name(m):
    m = int(round(m))
    return f"{dsp.NOTE_NAMES[m % 12]}{m // 12 - 1}"


def main(path, out_dir, harm_path=None):
    x = dsp.load(path)
    dur = x.shape[1] / dsp.SR
    print(f"duration {dur:.2f}s  LUFS {dsp.lufs(x):.2f}  peak {dsp.db(np.abs(x).max()):.2f} dBFS")

    bpm0 = tempo_guess(x)
    tr = beatlib.track(x, bpm0)
    bt = tr["beats"]
    bt = bt[(bt >= 0) & (bt < dur)]
    period = float(np.median(np.diff(bt)))
    print(f"tempo guess {bpm0:.2f}; tracked {len(bt)} beats, median {60 / period:.3f} BPM; "
          f"reliable beats {tr['reliable_first']}-{tr['reliable_last']}; grid {tr['grid_mode']} "
          f"(kick coherence {tr['coherence']})")

    # chroma per beat
    mono = signal.resample_poly(x.mean(0), 1, 2).astype(np.float32)
    n_fft_c, hop_c = 8192, 1200
    Sc = dsp.stft_mag(mono, n_fft_c, hop_c)
    C = dsp.chroma(Sc, AN_SR, n_fft_c, fmin=100, fmax=4000)
    fps_c = AN_SR / hop_c
    key_rank = dsp.estimate_key(C.sum(1))
    print("key:", [(n, round(float(s), 3)) for s, n in key_rank[:4]])
    edges = np.r_[bt, bt[-1] + period]
    bchroma = np.array([C[:, int(a * fps_c):max(int(b * fps_c), int(a * fps_c) + 1)].mean(1)
                        for a, b in zip(edges[:-1], edges[1:])])
    bchroma /= np.linalg.norm(bchroma, axis=1, keepdims=True) + 1e-12
    bass = bass_notes(x, edges)[:len(bt)]

    # downbeat phase: where chords and bass notes change
    cnov = np.r_[0, 1 - np.sum(bchroma[1:] * bchroma[:-1], axis=1)]
    bchg = np.r_[0, (np.abs(np.diff(np.round(bass))) >= 1).astype(float)]
    phase_score = [float(cnov[p::4].mean() / cnov.mean() + bchg[p::4].mean() / (bchg.mean() + 1e-9))
                   for p in range(4)]
    down = int(np.argmax(phase_score))
    print("downbeat phase scores:", [round(s, 2) for s in phase_score], "-> phase", down)

    # per-bar features
    bands = {"sub": (20, 60), "low": (60, 150), "lowmid": (150, 500), "mid": (500, 2500),
             "high": (2500, 7000), "air": (7000, 16000)}
    bars = []
    for bi, k in enumerate(range(down, len(bt) - 4, 4)):
        t0, t1 = bt[k], bt[k + 4]
        seg = x[:, int(t0 * dsp.SR):int(t1 * dsp.SR)]
        spec = np.abs(np.fft.rfft(seg.mean(0) * np.hanning(seg.shape[1]))) ** 2
        f = np.fft.rfftfreq(seg.shape[1], 1 / dsp.SR)
        row = {"bar": bi, "beat": int(k), "t": round(float(t0), 3), "len": round(float(t1 - t0), 4),
               "rms": round(float(dsp.db(np.sqrt(np.mean(seg ** 2)))), 1)}
        for name, (lo, hi) in bands.items():
            row[name] = round(float(10 * np.log10(spec[(f >= lo) & (f < hi)].sum() + 1e-12)), 1)
        mid, side = seg.mean(0), (seg[0] - seg[1]) / 2
        row["width"] = round(float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-12)), 2)
        row["bass"] = [round(float(v), 2) for v in bass[k:k + 4]]
        ch = bchroma[k:k + 4].mean(0)
        row["chroma"] = [round(float(v), 3) for v in ch]
        row["top"] = [dsp.NOTE_NAMES[i] for i in np.argsort(ch)[::-1][:4]]
        bars.append(row)

    # section boundaries: novelty over bar features
    feats = np.array([[r[k] for k in bands] + [r["rms"], r["width"] * 10] for r in bars])
    feats = (feats - feats.mean(0)) / (feats.std(0) + 1e-9)
    feats = np.hstack([feats, np.array([r["chroma"] for r in bars]) * 4])
    D = np.linalg.norm(feats[:, None] - feats[None], axis=2)
    L = 8
    kern = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((L, L)))
    novelty = np.zeros(len(bars))
    for i in range(L, len(bars) - L):
        novelty[i] = -np.sum(D[i - L:i + L, i - L:i + L] * kern)
    pk, _ = signal.find_peaks(novelty, distance=8, prominence=novelty.max() * 0.15)
    print("section boundaries (bar: time):", [(int(p), round(bars[p]["t"], 1)) for p in pk])

    # harmony runs: collapse consecutive bars with the same bass notes
    print("\nbars        time     bass (per beat)            top chroma   rms  sub  width")
    runs, cur = [], None
    for r in bars:
        sig = tuple(note_name(v) for v in r["bass"])
        if cur and cur["sig"] == sig:
            cur["end"] = r["bar"]
        else:
            cur = {"sig": sig, "start": r["bar"], "end": r["bar"]}
            runs.append(cur)
    for run in runs:
        r = bars[run["start"]]
        print(f"{run['start']:3d}-{run['end']:3d}  {r['t']:7.1f}  {' '.join(run['sig']):26s} "
              f"{' '.join(r['top']):12s} {r['rms']:5.1f} {r['sub']:5.1f} {r['width']:4.2f}")

    out = {"file": path, "duration": dur, "lufs": dsp.lufs(x), "bpm": 60 / period,
           "beats": bt.tolist(), "downbeat_phase": down, "reliable_beats": [tr["reliable_first"], tr["reliable_last"]],
           "key_rank": [(n, float(s)) for s, n in key_rank[:6]], "bars": bars,
           "sections": [int(p) for p in pk], "beat_bass_midi": [float(v) for v in bass]}
    if harm_path:
        hb = bass_notes(np.load(harm_path), edges)[:len(bt)]
        out["beat_bass_harm_midi"] = [float(v) for v in hb]
    with open(f"{out_dir}/analysis.json", "w") as fh:
        json.dump(out, fh)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(18, 10), sharex=True)
    tb = np.array([r["t"] for r in bars])
    for name in bands:
        ax[0].plot(tb, [r[name] for r in bars], label=name)
    ax[0].legend(ncol=6, loc="lower left")
    ax[0].set_ylabel("band dB")
    ax[1].imshow(np.array([r["chroma"] for r in bars]).T, aspect="auto", origin="lower",
                 extent=[tb[0], tb[-1], -0.5, 11.5], cmap="viridis")
    ax[1].set_yticks(range(12), dsp.NOTE_NAMES)
    ax[2].plot(bt, bass, ".", ms=2)
    ax[2].set_yticks(range(24, 52), [note_name(m) for m in range(24, 52)], fontsize=6)
    ax[2].set_ylim(26, 50)
    for p in pk:
        for a in ax:
            a.axvline(bars[p]["t"], color="red", lw=0.8)
    plt.tight_layout()
    plt.savefig(f"{out_dir}/analysis.png", dpi=65)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
