"""Objective checks on a rendered remix (I can't listen, so these stand in for ears where they can).

Usage: python3 verify.py remix.wav version
Checks: loudness arc per section, kick/bed grid alignment, bass-vs-chord agreement,
clicks at edit points, true peak of WAV and MP3, spectral balance vs the original.
"""
import sys
import numpy as np
from scipy import signal, ndimage
import dsp
import beats as beatlib
import remix as R

SP = R.SP


def short_term(x, win=3.0, hop=0.5):
    out = []
    for t in np.arange(0, x.shape[1] / dsp.SR - win, hop):
        seg = x[:, int(t * dsp.SR):int((t + win) * dsp.SR)]
        out.append((t + win / 2, dsp.lufs(seg) if np.abs(seg).max() > 1e-4 else -70))
    return np.array(out)


def main(path, version):
    y = dsp.load(path)
    print(f"length {y.shape[1] / dsp.SR:.1f}s  LUFS {dsp.lufs(y):.2f}  TP {dsp.true_peak_db(y):.2f} dBTP  "
          f"DC {np.abs(y.mean(1)).max():.5f}  clipped samples {(np.abs(y) >= 0.999).sum()}")
    mp3 = dsp.load(path.replace(".wav", ".mp3"))
    print(f"mp3 decode: TP {dsp.true_peak_db(mp3):.2f} dBTP, LUFS {dsp.lufs(mp3):.2f}")

    # loudness per section
    print("\nsection        bars      LUFS   LRA-ish(p90-p10)")
    st = short_term(y)
    for name, r0, nb, _ in R.SECTIONS:
        t0, t1 = R.pos(r0) / dsp.SR, R.pos(r0 + nb) / dsp.SR
        v = st[(st[:, 0] >= t0) & (st[:, 0] < t1), 1]
        print(f"{name:12s} {r0:3d}-{r0 + nb:3d}  {dsp.lufs(y[:, R.span(r0, r0 + nb)]):6.1f}   "
              f"{np.percentile(v, 90) - np.percentile(v, 10):4.1f}")

    # grid alignment: averaged transient onset of the bed stem (original material) vs grid beats
    bed = np.load(f"{SP}/stem_bed.npy")
    env, rate = beatlib.hf_envelope(bed)
    print("\nbed transient offset vs grid (ms) per section:")
    for name, r0, nb, _ in R.SECTIONS:
        segs = []
        w = int(0.06 * rate)
        for b in range(r0 * 4, (r0 + nb) * 4):
            a = int(round((b * R.SPB / dsp.SR - 0.03) * rate))
            if a >= 0 and a + w <= len(env):
                segs.append(env[a:a + w])
        off = beatlib.attack_time(np.mean(segs, 0), rate, 0.03) * 1000
        contrast = np.mean(segs, 0).max() / (np.median(np.mean(segs, 0)) + 1e-12)
        note = "" if contrast >= 1.45 else "  unreliable: blurred/filtered bed has no clear transients"
        print(f"  {name:10s} {off:+6.1f} ms  (peak/median {contrast:.1f}){note}")

    # bass vs chord: is the bass pitch class strong in the bed's chroma for each bar?
    # pitch is measured inside a single note (a train of retriggered notes has a comb spectrum)
    bass = np.load(f"{SP}/stem_bass.npy").mean(0)
    mono_bed = signal.resample_poly(bed.mean(0), 1, 2)
    Sc = dsp.stft_mag(mono_bed, 8192, 1200)
    C = dsp.chroma(Sc, 24000, 8192, fmin=100, fmax=4000)
    fps = 24000 / 1200
    agree, total, bad = 0, 0, []
    for r in sorted(R.BASS_BARS):
        a, b = R.pos(r) / dsp.SR, R.pos(r + 1) / dsp.SR
        n0 = R.pos(r, 0.25) + int(0.005 * dsp.SR)
        seg = bass[n0:n0 + int(0.08 * dsp.SR)]
        if np.abs(seg).max() < 1e-3:
            continue
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 18))
        f = np.fft.rfftfreq(1 << 18, 1 / dsp.SR)
        f0 = f[np.argmax(spec * (f > 28) * (f < 120))]
        pc = int(round(69 + 12 * np.log2(f0 / 440))) % 12
        ch = C[:, int(a * fps):int(b * fps)].mean(1)
        top3 = list(np.argsort(ch)[::-1][:3])
        # clash = a strong chord tone a semitone above the bass (b9) or a tritone away
        clash = any((t - pc) % 12 in (1, 6) for t in top3)
        total += 1
        if not clash:
            agree += 1
        else:
            bad.append((r, dsp.NOTE_NAMES[pc], [dsp.NOTE_NAMES[i] for i in top3]))
    print(f"\nbass vs bed chords: {agree}/{total} bars without b9/tritone clashes; clashes: {bad[:12]}")

    # clicks: in the bed stem (where every bar is a splice), compare >8 kHz energy in the 3 ms
    # around each bar boundary's crossfade with the surrounding 40 ms
    hi = dsp.sos_filter(bed.mean(0), "highpass", 8000, dsp.SR, 4)
    ratios = []
    for r in range(1, R.END):
        p = R.pos(r) - int(0.003 * dsp.SR)
        core = np.sqrt(np.mean(hi[p - 72:p + 72] ** 2) + 1e-12)
        ctx = np.sqrt(np.mean(np.r_[hi[p - 2000:p - 200], hi[p + 200:p + 2000]] ** 2) + 1e-12)
        ratios.append((dsp.db(core) - dsp.db(ctx), r))
    ratios.sort(reverse=True)
    print(f"\nsplice clicks (bed, >8 kHz, splice vs context dB): worst {[(round(v, 1), r) for v, r in ratios[:5]]}")

    # spectral balance: octave bands relative to each track's own 250-2000 Hz level
    x = dsp.load(R.SRC)

    def band_levels(z):
        f, p = signal.welch(z.mean(0), dsp.SR, nperseg=16384)
        ref = p[(f >= 250) & (f < 2000)].mean()
        return {lo_: 10 * np.log10(p[(f >= lo_) & (f < 2 * lo_)].mean() / ref) for lo_ in
                (25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800)}
    bo, br = band_levels(x), band_levels(y)
    print("\noctave bands vs own 250-2000 Hz (dB):  band  original  remix")
    for k in bo:
        print(f"   {k:6d} Hz  {bo[k]:+6.1f}  {br[k]:+6.1f}")
    f, ps = signal.welch(x.mean(0), dsp.SR, nperseg=8192)
    _, pr = signal.welch(y.mean(0), dsp.SR, nperseg=8192)
    ps, pr = 10 * np.log10(ps + 1e-20), 10 * np.log10(pr + 1e-20)
    k = np.argmin(np.abs(f - 1000))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(18, 11))
    st0 = short_term(x)
    ax[0].plot(st[:, 0], st[:, 1], label="remix short-term LUFS")
    ax[0].plot(st0[:, 0] * (st[-1, 0] / st0[-1, 0]), st0[:, 1], alpha=0.5, label="original (time-scaled)")
    for name, r0, nb, _ in R.SECTIONS:
        ax[0].axvline(R.pos(r0) / dsp.SR, color="gray", lw=0.6)
        ax[0].text(R.pos(r0) / dsp.SR + 1, -6.5, name, fontsize=8)
    ax[0].set_ylim(-30, -5)
    ax[0].legend(loc="lower center")
    fz, tz, Z = signal.stft(y.mean(0)[::2], dsp.SR / 2, nperseg=2048, noverlap=1024)
    Zdb = 20 * np.log10(np.abs(Z) + 1e-9)
    ax[1].pcolormesh(tz, fz, Zdb, vmin=Zdb.max() - 90, vmax=Zdb.max(), cmap="magma", shading="auto")
    ax[1].set_yscale("symlog", linthresh=200)
    ax[1].set_ylim(30, 12000)
    ax[2].semilogx(f, ps - ps[k], label="original")
    ax[2].semilogx(f, pr - pr[k], label="remix")
    ax[2].set_xlim(20, 20000)
    ax[2].set_ylim(-60, 30)
    ax[2].legend()
    plt.tight_layout()
    plt.savefig(f"out/verify_{version}.png", dpi=60)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
